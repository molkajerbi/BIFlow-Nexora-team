"""BIFlow user accounts: local SQLite database, hashed passwords (PBKDF2), cookie sessions, optional Google sign-in.

Accounts stay on this computer, like the data. Google sign-in is optional: it is enabled only when a Google OAuth
client ID is set in the .env file (BIFLOW_GOOGLE_CLIENT_ID). Google only confirms who the user is; no data is sent.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "biflow_accounts.sqlite3"
COOKIE = "biflow_session"
SESSION_DAYS = 14
ITERATIONS = 200_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
_lock = threading.Lock()


class AuthError(Exception):
    """Error shown as is to the user."""


def load_env() -> None:
    """Reads the .env file at the project root (KEY=value lines) without overwriting variables already set."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()


@contextmanager
def _db():
    """Connection to the accounts database (created on first use), committed then closed at the end of the block."""
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, organization TEXT,
                password_hash TEXT NOT NULL, salt TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires TEXT NOT NULL);
        """)
        columns = {r["name"] for r in con.execute("PRAGMA table_info(users)")}
        if "google_sub" not in columns:                  # older databases: add the Google columns
            con.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
            con.execute("ALTER TABLE users ADD COLUMN picture TEXT")
        yield con
        con.commit()
    finally:
        con.close()


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS).hex()


def _public(row) -> dict:
    keys = row.keys()
    return {"id": row["id"], "email": row["email"], "name": row["name"], "organization": row["organization"] or "",
            "created": row["created"], "has_password": bool(row["password_hash"]),
            "google": bool(row["google_sub"]) if "google_sub" in keys else False,
            "picture": (row["picture"] or "") if "picture" in keys else ""}


def _check_password(password: str) -> None:
    if len(password or "") < 8:
        raise AuthError("The password must be at least 8 characters long.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_user(name: str, email: str, password: str, organization: str = "") -> dict:
    name, email = (name or "").strip(), (email or "").strip().lower()
    if len(name) < 2:
        raise AuthError("Please enter your full name.")
    if not EMAIL_RE.match(email):
        raise AuthError("Invalid email address.")
    _check_password(password)
    salt = secrets.token_hex(16)
    with _lock, _db() as con:
        if con.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise AuthError("An account already exists with this email address. Please sign in.")
        con.execute("INSERT INTO users (id, email, name, organization, password_hash, salt, created) VALUES (?,?,?,?,?,?,?)",
                    (secrets.token_hex(8), email, name, (organization or "").strip(), _hash(password, salt), salt, _now()))
        row = con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return _public(row)


def authenticate(email: str, password: str) -> dict:
    with _db() as con:
        row = con.execute("SELECT * FROM users WHERE email = ?", ((email or "").strip().lower(),)).fetchone()
    if row is not None and not row["password_hash"]:
        raise AuthError('This account uses Google sign-in. Click "Continue with Google".')
    if row is None or not hmac.compare_digest(row["password_hash"], _hash(password or "", row["salt"])):
        raise AuthError("Incorrect email or password.")
    return _public(row)


# ================================================================ Google sign-in
def google_client_id() -> str:
    return os.environ.get("BIFLOW_GOOGLE_CLIENT_ID", "").strip()


def _verify_google(credential: str) -> dict:
    """Checks the Google ID token with Google (signature, expiry, audience) and returns its claims."""
    client_id = google_client_id()
    if not client_id:
        raise AuthError("Google sign-in is not configured: add BIFLOW_GOOGLE_CLIENT_ID to the .env file, then restart the API.")
    if not credential or len(credential) > 4096:
        raise AuthError("Google sign-in failed: invalid answer from Google.")
    url = f"{GOOGLE_TOKENINFO}?{urllib.parse.urlencode({'id_token': credential})}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            claims = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError:
        raise AuthError("Google sign-in failed: Google rejected the sign-in. Please try again.")
    except (urllib.error.URLError, OSError, ValueError):
        raise AuthError("Google could not be reached: check this computer's Internet connection, then try again.")
    if claims.get("aud") != client_id:
        raise AuthError("Google sign-in failed: this sign-in was issued for another application.")
    if claims.get("iss") not in GOOGLE_ISSUERS or int(claims.get("exp", 0)) < time.time():
        raise AuthError("Google sign-in failed: the sign-in has expired. Please try again.")
    if str(claims.get("email_verified")).lower() != "true" or not claims.get("email"):
        raise AuthError("Google sign-in failed: this Google account has no verified email address.")
    return claims


def google_user(credential: str) -> dict:
    """Signs in with Google: finds the account (by Google ID, then by email) or creates it."""
    claims = _verify_google(credential)
    sub, email = str(claims["sub"]), str(claims["email"]).strip().lower()
    name = (claims.get("name") or email.split("@")[0]).strip()
    picture = claims.get("picture") or ""
    with _lock, _db() as con:
        row = con.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone() or \
            con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:                                  # first visit: the Google account becomes a BIFlow account
            con.execute("INSERT INTO users (id, email, name, organization, password_hash, salt, created, google_sub, picture) "
                        "VALUES (?,?,?,?,?,?,?,?,?)", (secrets.token_hex(8), email, name, "", "", "", _now(), sub, picture))
        else:                                            # existing account with the same email: linked to Google
            con.execute("UPDATE users SET google_sub = ?, picture = ? WHERE id = ?", (sub, picture, row["id"]))
        row = con.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone()
    return _public(row)


# ================================================================ sessions
def new_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    with _lock, _db() as con:
        con.execute("INSERT INTO sessions VALUES (?, ?, ?)", (token, user_id, expires))
    return token


def end_session(token: str | None) -> None:
    if token:
        with _lock, _db() as con:
            con.execute("DELETE FROM sessions WHERE token = ?", (token,))


def user_from_token(token: str | None) -> dict | None:
    if not token:
        return None
    with _db() as con:
        row = con.execute("SELECT u.*, s.expires FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
                          (token,)).fetchone()
    if row is None or row["expires"] < datetime.now(timezone.utc).isoformat():
        return None
    return _public(row)


# ================================================================ profile
def update_user(user_id: str, name: str, organization: str) -> dict:
    name = (name or "").strip()
    if len(name) < 2:
        raise AuthError("Please enter your full name.")
    with _lock, _db() as con:
        con.execute("UPDATE users SET name = ?, organization = ? WHERE id = ?", (name, (organization or "").strip(), user_id))
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public(row)


def change_password(user_id: str, current: str, new: str) -> None:
    """Changes the password. A Google account without a password can set one (no current password needed)."""
    with _db() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise AuthError("Account not found.")
    if row["password_hash"] and not hmac.compare_digest(row["password_hash"], _hash(current or "", row["salt"])):
        raise AuthError("Current password is incorrect.")
    _check_password(new)
    salt = secrets.token_hex(16)
    with _lock, _db() as con:
        con.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (_hash(new, salt), salt, user_id))
