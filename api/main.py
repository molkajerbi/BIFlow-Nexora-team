"""BIFlow API (FastAPI): accounts, analyses, results of each agent, dashboard and XAI assistant.

The pipeline itself does not change: each analysis is launched by biflow.jobs (a separate process that runs the
notebook cells with biflow.engine). This API only launches, follows and serves the results.

Start (from the project root):   uvicorn api.main:app --port 8000
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import threading
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from biflow import jobs

from . import auth, notify

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
ORIGINS = [o.strip() for o in os.environ.get("BIFLOW_WEB_ORIGINS",
                                             "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,120}$")
TECH_COLUMNS = {"_source_row_id", "_dq_flags", "is_unknown_member"}

app = FastAPI(title="BIFlow API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])
notify.start()                                    # watcher: tells the user when an analysis finishes or stops


# ================================================================ helpers
class SignupBody(BaseModel):
    name: str
    email: str
    password: str
    organization: str = ""


class SigninBody(BaseModel):
    email: str
    password: str


class GoogleBody(BaseModel):
    credential: str


class ProfileBody(BaseModel):
    name: str
    organization: str = ""


class PasswordBody(BaseModel):
    current: str
    new: str


class ReadBody(BaseModel):
    ids: list[int] | None = None


class NotifyPrefsBody(BaseModel):
    email: bool


class ChatBody(BaseModel):
    question: str
    use_llm: bool = True


def clean(value):
    """Valid JSON values (NaN and infinities become null)."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def frame_records(df: pd.DataFrame, limit: int | None = None) -> dict:
    if limit:
        df = df.head(limit)
    df = df.rename(columns={c: "index" for c in df.columns if str(c).startswith("Unnamed")})
    df = df.astype(object).where(pd.notna(df), None)
    return {"columns": [str(c) for c in df.columns], "rows": clean(df.to_dict(orient="records"))}


def current_user(request: Request) -> dict:
    user = auth.user_from_token(request.cookies.get(auth.COOKIE))
    if user is None:
        raise HTTPException(401, "Session expired: please sign in again.")
    return user


def with_session(user: dict) -> JSONResponse:
    response = JSONResponse({"user": user})
    response.set_cookie(auth.COOKIE, auth.new_session(user["id"]), httponly=True, samesite="lax",
                        max_age=auth.SESSION_DAYS * 86400, path="/")
    return response


def own_job(job_id: str, user: dict) -> dict:
    """Metadata of one of the user's analyses (404 otherwise: the existence of other users' analyses is not revealed)."""
    meta = jobs.meta(job_id) if NAME_RE.match(job_id or "") else {}
    if not meta or meta.get("owner") not in (None, user["id"]):
        raise HTTPException(404, "Analysis not found.")
    return meta


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_result(job_id: str) -> tuple[dict, int, str]:
    """(available results, last finished step, status)."""
    status = jobs.status(job_id)
    res = jobs.result(job_id)
    prog = jobs.progress(job_id)
    partial = read_json(jobs.JOBS_DIR / job_id / "results" / "partial.json") or {}
    if res is None:
        res = partial
    elif res.get("status") != "success" and partial:
        res = {**partial, **{k: v for k, v in res.items() if v is not None}}   # stopped: keep what was ready
    completed = 13 if status == "success" else int(prog.get("completed_step") or res.get("completed_step") or 0)
    return res, completed, status


def summary(meta: dict) -> dict:
    """One analysis row in the lists."""
    res, completed, status = load_result(meta["id"])
    prog = jobs.progress(meta["id"]) if status == "running" else {}
    bi, xai = res.get("bi") or {}, res.get("xai") or {}
    return {"id": meta["id"], "name": meta.get("name"), "created": meta.get("created"), "model": meta.get("model"),
            "status": status, "completed": completed, "percent": prog.get("percent"), "domain": res.get("domain"),
            "tables": (res.get("input") or {}).get("tables"), "rows": (res.get("input") or {}).get("rows"),
            "kpis": bi.get("kpis"), "insights": bi.get("insights"), "sectors": bi.get("sectors"),
            "decisions": xai.get("decisions"), "chat_ready": bool(xai.get("ready")) and status != "running"}


# ================================================================ health
@app.get("/api/health")
def health():
    models = jobs.ollama_models(OLLAMA_URL)
    default = "qwen2.5:7b" if models and "qwen2.5:7b" in models else (models[0] if models else "qwen2.5:7b")
    return {"api": True, "ollama": models is not None, "models": models or [], "default_model": default,
            "mail": notify.mail_config() is not None, "google": bool(auth.google_client_id())}


# ================================================================ accounts
@app.post("/api/auth/signup")
def signup(body: SignupBody):
    try:
        user = auth.create_user(body.name, body.email, body.password, body.organization)
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc))
    return with_session(user)


@app.post("/api/auth/signin")
def signin(body: SigninBody):
    try:
        user = auth.authenticate(body.email, body.password)
    except auth.AuthError as exc:
        raise HTTPException(401, str(exc))
    return with_session(user)


@app.get("/api/auth/config")
def auth_config():
    """What the sign-in page needs: the Google client ID (public, not a secret), or an empty string."""
    return {"google_client_id": auth.google_client_id()}


@app.post("/api/auth/google")
def signin_google(body: GoogleBody):
    try:
        user = auth.google_user(body.credential)
    except auth.AuthError as exc:
        raise HTTPException(401, str(exc))
    return with_session(user)


@app.post("/api/auth/signout")
def signout(request: Request):
    auth.end_session(request.cookies.get(auth.COOKIE))
    response = JSONResponse({"ok": True})
    response.delete_cookie(auth.COOKIE, path="/")
    return response


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return {"user": user}


@app.put("/api/me")
def update_me(body: ProfileBody, user: dict = Depends(current_user)):
    try:
        return {"user": auth.update_user(user["id"], body.name, body.organization)}
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc))


@app.put("/api/me/password")
def update_password(body: PasswordBody, user: dict = Depends(current_user)):
    try:
        auth.change_password(user["id"], body.current, body.new)
    except auth.AuthError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


# ================================================================ notifications
@app.get("/api/notifications")
def notifications(user: dict = Depends(current_user)):
    return {**notify.list_for(user["id"]), **notify.prefs(user["id"])}


@app.post("/api/notifications/read")
def notifications_read(body: ReadBody, user: dict = Depends(current_user)):
    notify.mark_read(user["id"], body.ids)
    return {"ok": True}


@app.put("/api/me/notifications")
def notifications_prefs(body: NotifyPrefsBody, user: dict = Depends(current_user)):
    notify.set_email(user["id"], body.email)
    return notify.prefs(user["id"])


@app.post("/api/me/notifications/test")
def notifications_test(user: dict = Depends(current_user)):
    if notify.mail_config() is None:
        raise HTTPException(400, "No email server is configured: fill in the .env file, then restart the API.")
    if not notify.send_test(user):
        raise HTTPException(502, "The email could not be sent: check the address and the app password in the .env "
                                 "file (the details are printed in the API terminal).")
    return {"ok": True}


# ================================================================ analyses
@app.get("/api/stats")
def stats(user: dict = Depends(current_user)):
    rows = [summary(m) for m in jobs.list_jobs(user["id"])]
    done = [r for r in rows if r["status"] == "success"]
    return {"analyses": len(rows), "finished": len(done), "running": sum(r["status"] == "running" for r in rows),
            "kpis": sum(r["kpis"] or 0 for r in done), "insights": sum(r["insights"] or 0 for r in done),
            "decisions": sum(r["decisions"] or 0 for r in done), "recent": rows[:5]}


@app.get("/api/jobs")
def list_analyses(user: dict = Depends(current_user)):
    return {"jobs": [summary(m) for m in jobs.list_jobs(user["id"])]}


@app.post("/api/jobs")
async def create_analysis(request: Request, user: dict = Depends(current_user)):
    form = await request.form(max_files=2000)
    files = [(f.filename, await f.read()) for f in form.getlist("files") if getattr(f, "filename", None)]
    if not files:
        raise HTTPException(400, "Add at least one data file.")
    name = str(form.get("name") or "").strip() or (Path(files[0][0]).stem if len(files) == 1 else
                                                    f"Analysis of {len(files)} files")
    model = str(form.get("model") or "qwen2.5:7b")
    try:
        job_id = jobs.create_job(files, name, model, owner=user["id"])
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    jobs.launch(job_id)
    return {"id": job_id}


@app.get("/api/jobs/{job_id}")
def analysis(job_id: str, user: dict = Depends(current_user)):
    meta = own_job(job_id, user)
    res, completed, status = load_result(job_id)
    prog = jobs.progress(job_id)
    out_dir = res.get("output_dir")
    warehouse = next(iter(Path(out_dir).glob("biflow_star.*")), None) if out_dir and Path(out_dir).exists() else None
    downloads = {"zip": (jobs.JOBS_DIR / job_id / "biflow_outputs.zip").exists(),
                 "warehouse": warehouse.name if warehouse else None,
                 "warehouse_mb": round(warehouse.stat().st_size / 1e6, 1) if warehouse else None,
                 "dashboard": bool((res.get("bi") or {}).get("dashboard"))}
    return clean({"meta": meta, "status": status, "completed": completed, "result": res,
                  "progress": {k: prog.get(k) for k in ("percent", "step", "cell", "elapsed_s", "completed_step")},
                  "downloads": downloads})


@app.get("/api/jobs/{job_id}/table/{name}")
def analysis_table(job_id: str, name: str, limit: int = 2000, user: dict = Depends(current_user)):
    own_job(job_id, user)
    if not NAME_RE.match(name):
        raise HTTPException(404, "Table not found.")
    path = jobs.JOBS_DIR / job_id / "results" / f"{name}.csv"
    if not path.exists():
        return {"columns": [], "rows": [], "missing": True}
    return frame_records(pd.read_csv(path), limit)


@app.get("/api/jobs/{job_id}/star")
def analysis_star(job_id: str, user: dict = Depends(current_user)):
    own_job(job_id, user)
    return clean(jobs.star_schema(job_id) or {})


@app.get("/api/jobs/{job_id}/insights")
def analysis_insights(job_id: str, user: dict = Depends(current_user)):
    own_job(job_id, user)
    return {"insights": clean(jobs.insights(job_id))}


@app.get("/api/jobs/{job_id}/preview/{table}")
def warehouse_preview(job_id: str, table: str, user: dict = Depends(current_user)):
    """The first 200 rows of a star schema table."""
    own_job(job_id, user)
    res, _, _ = load_result(job_id)
    folder = Path(res["run_dir"]) / "warehouse" if res.get("run_dir") else None
    path = folder / f"{table}.csv" if folder and NAME_RE.match(table) else None
    if not path or not path.exists():
        raise HTTPException(404, "Table not found.")
    df = pd.read_csv(path, nrows=200)
    return frame_records(df.drop(columns=[c for c in df.columns if c in TECH_COLUMNS]))


@app.get("/api/jobs/{job_id}/dashboard", response_class=HTMLResponse)
def analysis_dashboard(job_id: str, user: dict = Depends(current_user)):
    own_job(job_id, user)
    html = jobs.dashboard_html(job_id)
    if not html:
        raise HTTPException(404, "Dashboard not found.")
    return HTMLResponse(html)


@app.get("/api/jobs/{job_id}/download/{kind}")
def download(job_id: str, kind: str, user: dict = Depends(current_user)):
    meta = own_job(job_id, user)
    stem = re.sub(r"[^0-9A-Za-z_-]+", "_", meta.get("name") or job_id).strip("_") or job_id
    if kind == "zip":
        path = jobs.JOBS_DIR / job_id / "biflow_outputs.zip"
        name = f"biflow_{stem}.zip"
    elif kind == "warehouse":
        res, _, _ = load_result(job_id)
        out = res.get("output_dir")
        path = next(iter(Path(out).glob("biflow_star.*")), None) if out and Path(out).exists() else None
        name = path.name if path else ""
    elif kind == "dashboard":
        bi = (load_result(job_id)[0].get("bi") or {})
        path = Path(bi["dashboard"]) if bi.get("dashboard") else None
        name = f"dashboard_{stem}.html"
    else:
        raise HTTPException(404, "Unknown download.")
    if not path or not Path(path).exists():
        raise HTTPException(404, "File not found.")
    return FileResponse(path, filename=name)


@app.post("/api/jobs/{job_id}/relaunch")
def relaunch(job_id: str, user: dict = Depends(current_user)):
    own_job(job_id, user)
    if jobs.status(job_id) == "running":
        raise HTTPException(409, "The analysis is already running.")
    job_dir = jobs.JOBS_DIR / job_id
    for old in ("result.json", "decision.json", "progress.json"):
        (job_dir / old).unlink(missing_ok=True)
    for folder in ("results", "chat"):                # results and conversation of the previous run
        shutil.rmtree(job_dir / folder, ignore_errors=True)
    forget_chat(job_id)
    jobs.launch(job_id)
    return {"ok": True}


@app.post("/api/jobs/{job_id}/stop")
def stop(job_id: str, user: dict = Depends(current_user)):
    own_job(job_id, user)
    jobs.stop(job_id)
    return {"ok": True}


@app.delete("/api/jobs/{job_id}")
def delete(job_id: str, user: dict = Depends(current_user)):
    own_job(job_id, user)
    forget_chat(job_id)
    if not jobs.delete(job_id):
        raise HTTPException(409, "Deletion incomplete: close the open files (Excel, File Explorer), then try again.")
    return {"ok": True}


# ================================================================ XAI assistant
_CHATS: dict[str, tuple[str, object]] = {}
_CHAT_LOCK = threading.Lock()


def forget_chat(job_id: str) -> None:
    with _CHAT_LOCK:
        _CHATS.pop(job_id, None)


def chat_session(job_id: str):
    """XAI agent of the analysis, rebuilt once (notebook code + ledger exported by the run)."""
    from biflow.llm import OllamaLLM
    from biflow.xai_chat import XAISession
    res = jobs.result(job_id) or {}
    if jobs.status(job_id) == "running" or not (res.get("xai") or {}).get("ready"):
        raise HTTPException(409, "The assistant will be available as soon as the analysis is finished.")
    stamp = str(res.get("finished_at"))
    with _CHAT_LOCK:
        cached = _CHATS.get(job_id)
        if cached and cached[0] == stamp:
            return cached[1]
        llm = OllamaLLM(model_id=jobs.meta(job_id).get("model"), url=OLLAMA_URL, cache_dir=jobs.ROOT / "biflow_cache")
        try:
            session = XAISession(jobs.JOBS_DIR / job_id, llm=llm)
        except RuntimeError as exc:                  # analyse faite avec l'ancien notebook, ou XAI absent
            raise HTTPException(409, f"The assistant is not available for this analysis: {exc}.")
        _CHATS[job_id] = (stamp, session)
        return session


@app.get("/api/chat/jobs")
def chat_jobs(user: dict = Depends(current_user)):
    return {"jobs": [s for s in (summary(m) for m in jobs.list_jobs(user["id"])) if s["chat_ready"]]}


@app.get("/api/jobs/{job_id}/chat")
def chat_history(job_id: str, user: dict = Depends(current_user)):
    own_job(job_id, user)
    session = chat_session(job_id)
    xai = (jobs.result(job_id) or {}).get("xai") or {}
    return clean({"history": session.history, "suggestions": [q for q in xai.get("demo_questions") or [] if q][:6],
                  "decisions": xai.get("decisions"), "rules": xai.get("rules")})


@app.post("/api/jobs/{job_id}/chat")
def chat_ask(job_id: str, body: ChatBody, user: dict = Depends(current_user)):
    own_job(job_id, user)
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(400, "Ask a question.")
    session = chat_session(job_id)
    return clean({"turn": session.ask(question[:1000], use_llm=body.use_llm)})


@app.delete("/api/jobs/{job_id}/chat")
def chat_clear(job_id: str, user: dict = Depends(current_user)):
    own_job(job_id, user)
    chat_session(job_id).clear()
    return {"ok": True}
