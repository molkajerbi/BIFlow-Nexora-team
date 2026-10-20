"""BIFlow notifications: when an analysis finishes or stops, the user is told.

- in the app: bell at the top right (list + unread count) and a message that pops up on screen;
- on the computer: Windows notification from the browser (if the user allowed it);
- by email: ONLY if a sending server is configured in the .env file (otherwise nothing is sent).

A "watcher" (an API thread) checks the state of the analyses every 5 seconds. The pipeline itself is not changed:
the watcher reads the same files as the interface (result.json, progress.json, pid).
No data from the analysed files is sent: only a summary (number of KPIs, title of the main insight).
"""
from __future__ import annotations

import html
import json
import os
import smtplib
import ssl
import threading
import time
from datetime import datetime, timezone
from email.message import EmailMessage

from biflow import jobs

from . import auth

TERMINAL = {"success", "failed", "blocked", "interrupted"}
MARK = "notified.json"                         # in the analysis folder: last state already notified
BASELINE = jobs.JOBS_DIR / ".notifications_baseline"
EVERY_S = 5
_started = False

auth.load_env()


# ================================================================ configuration (.env)
def mail_config() -> dict | None:
    """Email sending server (Gmail, Outlook…), or None if it is not configured."""
    host, user, password = (os.environ.get(k, "").strip() for k in
                            ("BIFLOW_SMTP_HOST", "BIFLOW_SMTP_USER", "BIFLOW_SMTP_PASSWORD"))
    if not (host and user and password):
        return None
    return {"host": host, "port": int(os.environ.get("BIFLOW_SMTP_PORT", "587") or 587), "user": user,
            "password": password.replace(" ", ""), "sender": os.environ.get("BIFLOW_MAIL_FROM", "").strip() or user,
            "app_url": os.environ.get("BIFLOW_APP_URL", "http://localhost:3000").rstrip("/")}


# ================================================================ notifications database
def _init() -> None:
    with auth._lock, auth._db() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, job_id TEXT, kind TEXT NOT NULL,
                title TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL, read INTEGER NOT NULL DEFAULT 0,
                emailed INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS notification_prefs (user_id TEXT PRIMARY KEY, email INTEGER NOT NULL DEFAULT 1);
        """)


def _row(r) -> dict:
    return {"id": r["id"], "job_id": r["job_id"], "kind": r["kind"], "title": r["title"], "body": r["body"],
            "created": r["created"], "read": bool(r["read"]), "emailed": bool(r["emailed"])}


def list_for(user_id: str, limit: int = 30) -> dict:
    with auth._db() as con:
        rows = con.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                           (user_id, limit)).fetchall()
        unread = con.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read = 0", (user_id,)).fetchone()[0]
    return {"items": [_row(r) for r in rows], "unread": unread}


def mark_read(user_id: str, ids: list[int] | None = None) -> None:
    with auth._lock, auth._db() as con:
        if ids:
            con.executemany("UPDATE notifications SET read = 1 WHERE user_id = ? AND id = ?", [(user_id, i) for i in ids])
        else:
            con.execute("UPDATE notifications SET read = 1 WHERE user_id = ?", (user_id,))


def email_enabled(user_id: str) -> bool:
    with auth._db() as con:
        row = con.execute("SELECT email FROM notification_prefs WHERE user_id = ?", (user_id,)).fetchone()
    return True if row is None else bool(row["email"])


def set_email(user_id: str, enabled: bool) -> None:
    with auth._lock, auth._db() as con:
        con.execute("INSERT INTO notification_prefs (user_id, email) VALUES (?, ?) "
                    "ON CONFLICT(user_id) DO UPDATE SET email = excluded.email", (user_id, int(bool(enabled))))


def prefs(user_id: str) -> dict:
    return {"email_configured": mail_config() is not None, "email_enabled": email_enabled(user_id)}


def _user(user_id: str) -> dict | None:
    with auth._db() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return auth._public(row) if row else None


# ================================================================ message content
def _short(text, limit: int = 220) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _n(value, one: str, many: str) -> str:
    k = int(value or 0)
    return f"{k} {one if k == 1 else many}"


def message(job_id: str, meta: dict, status: str) -> dict:
    """Title, text and details of a notification, built from the analysis results."""
    res = jobs.result(job_id) or {}
    bi, prep = res.get("bi") or {}, res.get("quality") or {}
    name = meta.get("name") or job_id
    details = []
    if status == "success":
        sectors = ", ".join(bi.get("sectors") or []) or "generic"
        insights = jobs.insights(job_id)
        details = [("KPIs computed and verified", bi.get("kpis")), ("Insights published", bi.get("insights")),
                   ("Business sector", sectors), ("Corrections applied", prep.get("corrections_applied"))]
        top = f' Main insight: "{insights[0]["titre"]}".' if insights else ""
        return {"kind": "success", "title": f"Analysis finished: {name}",
                "body": f"{_n(bi.get('kpis'), 'KPI', 'KPIs')} computed, {_n(bi.get('insights'), 'insight', 'insights')} "
                        f"published, dashboard ready.{top}", "details": details, "action": "View the results"}
    if status == "blocked":
        return {"kind": "blocked", "title": f"Analysis stopped for safety: {name}",
                "body": "A critical problem in the data prevents building a reliable model. The Cleaning tab shows "
                        "which one, and the assistant can explain why.", "details": details, "action": "View the details"}
    if status == "failed" and bi.get("error") and res.get("output_dir"):
        return {"kind": "failed", "title": f"BI analysis interrupted: {name}",
                "body": "Your data is ready (cleaned, with its star schema), but the KPI or analysis step stopped: "
                        f"{_short(bi['error'], 160)}. You can run it again: the steps already done will be fast.",
                "details": details, "action": "Run the analysis again"}
    if status == "failed" and "ollama" in str(res.get("error") or bi.get("error") or "").lower():
        return {"kind": "failed", "title": f"Analysis stopped: {name}",
                "body": "The local AI engine (Ollama) was not responding. Open the Ollama app, then run the analysis "
                        "again: the steps already done will be fast.", "details": details,
                "action": "Run the analysis again"}
    if status == "failed":
        return {"kind": "failed", "title": f"Analysis stopped: {name}",
                "body": f"The analysis stopped before the end: {_short(res.get('error'), 160) or 'unknown reason'}. "
                        "Check that Ollama is open, then run it again.", "details": details,
                "action": "View and run again"}
    return {"kind": "interrupted", "title": f"Analysis interrupted: {name}",
            "body": "The processing stopped abruptly (computer asleep, window closed…). Run it again: the steps already "
                    "done will be fast.", "details": details, "action": "Run the analysis again"}


# ================================================================ email
COLORS = {"success": "#0f9f8f", "blocked": "#c0362c", "failed": "#c0362c", "interrupted": "#b26b00"}
LABELS = {"success": "Analysis finished", "blocked": "Safety stop", "failed": "Analysis stopped",
          "interrupted": "Analysis interrupted"}


def _email_html(user: dict, msg: dict, link: str) -> str:
    e = html.escape
    color = COLORS.get(msg["kind"], "#2f6bf6")
    rows = "".join(f'<tr><td style="padding:6px 0;color:#5b6478;font-size:14px">{e(k)}</td>'
                   f'<td style="padding:6px 0;text-align:right;font-weight:700;color:#101a2c;font-size:14px">{e(str(v))}</td></tr>'
                   for k, v in msg["details"] if v not in (None, ""))
    table = f'<table width="100%" style="border-collapse:collapse;margin:18px 0 6px;border-top:1px solid #e4e8ef">{rows}</table>' \
        if rows else ""
    return f"""<!doctype html><html><body style="margin:0;background:#f4f6fa;font-family:Segoe UI,Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6fa;padding:28px 12px"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #e4e8ef">
<tr><td style="height:6px;background:linear-gradient(90deg,#14b8a6,#2f6bf6,#7c5cf6)"></td></tr>
<tr><td style="padding:26px 30px 8px"><span style="font-size:20px;font-weight:800;color:#101a2c">BI<span style="color:#2f6bf6">Flow</span></span>
<span style="float:right;font-size:12px;font-weight:700;color:{color};background:#f4f6fa;border-radius:99px;padding:5px 12px">{e(LABELS.get(msg['kind'], ''))}</span></td></tr>
<tr><td style="padding:10px 30px 0"><h1 style="margin:0 0 10px;font-size:21px;line-height:1.3;color:#101a2c">{e(msg['title'])}</h1>
<p style="margin:0;color:#3b4558;font-size:15px;line-height:1.6">Hello {e(user['name'].split()[0])},<br>{e(msg['body'])}</p>{table}</td></tr>
<tr><td style="padding:20px 30px 28px"><a href="{e(link)}" style="display:inline-block;background:#2f6bf6;background:linear-gradient(90deg,#14b8a6,#2f6bf6,#7c5cf6);color:#ffffff;text-decoration:none;font-weight:700;font-size:15px;padding:12px 22px;border-radius:12px">{e(msg['action'])}</a></td></tr>
<tr><td style="padding:16px 30px;background:#f8fafc;color:#8a94a8;font-size:12px;line-height:1.5">Automatic message from BIFlow (Nexora team · ESPRIT). Your data stays on your computer: this email only contains a summary. You can turn these emails off in "My profile".</td></tr>
</table></td></tr></table></body></html>"""


def send_email(user: dict, msg: dict, job_id: str | None) -> bool:
    """Sends the email (SMTP server from the .env file). A failure is only printed in the API terminal."""
    cfg = mail_config()
    if not cfg:
        return False
    link = f"{cfg['app_url']}/app/analyses/{job_id}" if job_id else f"{cfg['app_url']}/app"
    mail = EmailMessage()
    mail["Subject"], mail["From"], mail["To"] = msg["title"], f"BIFlow <{cfg['sender']}>", user["email"]
    mail.set_content(f"Hello {user['name']},\n\n{msg['body']}\n\n{msg['action']}: {link}\n\n— BIFlow")
    mail.add_alternative(_email_html(user, msg, link), subtype="html")
    try:
        context = ssl.create_default_context()
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=20) as s:
                s.login(cfg["user"], cfg["password"])
                s.send_message(mail)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as s:
                s.starttls(context=context)
                s.login(cfg["user"], cfg["password"])
                s.send_message(mail)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        print(f"[BIFlow] email not sent to {user['email']}: {exc}", flush=True)
        return False


def send_test(user: dict) -> bool:
    msg = {"kind": "success", "title": "BIFlow notifications test",
           "body": "If you are reading this, BIFlow emails work: you will be told at the end of each analysis, or if "
                   "it stops.", "details": [], "action": "Open BIFlow"}
    return send_email(user, msg, None)


# ================================================================ watcher
def _stamp(job_id: str, status: str) -> str | None:
    """Identity of the final state: changes with each new run (relaunch). None: state not certain yet."""
    job_dir = jobs.JOBS_DIR / job_id
    if status == "interrupted":
        pid = job_dir / "pid"
        if not pid.exists():
            return None                                  # analysis being created: not launched yet
        last = max((p.stat().st_mtime for p in (pid, job_dir / "progress.json") if p.exists()), default=0)
        if time.time() - last < 20:
            return None                                  # just launched: give the process time to start
        return f"interrupted|{pid.read_text(encoding='utf-8').strip()}"
    res = jobs.result(job_id) or {}
    return f"{status}|{res.get('finished_at')}"


def notify(job_id: str, meta: dict, status: str) -> None:
    owner = meta.get("owner")
    user = _user(owner) if owner else None
    if user is None:
        return
    msg = message(job_id, meta, status)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with auth._lock, auth._db() as con:
        cur = con.execute("INSERT INTO notifications (user_id, job_id, kind, title, body, created) VALUES (?,?,?,?,?,?)",
                          (owner, job_id, msg["kind"], msg["title"], msg["body"], now))
        nid = cur.lastrowid
    if mail_config() and email_enabled(owner):
        def run():
            if send_email(user, msg, job_id):
                with auth._lock, auth._db() as con:
                    con.execute("UPDATE notifications SET emailed = 1 WHERE id = ?", (nid,))
        threading.Thread(target=run, daemon=True).start()


def check_once(silent: bool = False) -> int:
    """One round of the watcher: notifies each analysis that reached a final state not notified yet."""
    sent = 0
    for meta in jobs.list_jobs():
        job_id = meta["id"]
        status = meta.get("status") or jobs.status(job_id)
        if status not in TERMINAL:
            continue
        stamp = _stamp(job_id, status)
        mark = jobs.JOBS_DIR / job_id / MARK
        try:
            done = json.loads(mark.read_text(encoding="utf-8")).get("stamp") if mark.exists() else None
        except (OSError, json.JSONDecodeError):
            done = None
        if stamp is None or stamp == done:
            continue
        try:
            mark.write_text(json.dumps({"stamp": stamp, "status": status}), encoding="utf-8")
        except OSError:
            continue                                     # folder being deleted
        if not silent:
            notify(job_id, meta, status)
            sent += 1
    return sent


def _loop() -> None:
    if not BASELINE.exists():                            # first start: analyses already finished are not notified
        check_once(silent=True)
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    while True:
        try:
            check_once()
        except Exception as exc:                         # the watcher must never stop
            print(f"[BIFlow] notifications: {type(exc).__name__}: {exc}", flush=True)
        time.sleep(EVERY_S)


def start() -> None:
    """Starts the watcher only once (called when the API starts)."""
    global _started
    if _started:
        return
    _started = True
    _init()
    threading.Thread(target=_loop, name="biflow-notifications", daemon=True).start()
    cfg = mail_config()
    print(f"[BIFlow] notifications on · emails: {'via ' + cfg['host'] if cfg else 'not configured (.env file)'} · "
          f"Google sign-in: {'on' if auth.google_client_id() else 'not configured (.env file)'}", flush=True)
