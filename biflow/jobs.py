"""Gestion des analyses lancées depuis l'interface web : un dossier par analyse dans jobs/."""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = ROOT / "jobs"
DATA_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xls", ".parquet", ".json"}


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _safe_extract(data: bytes, target: Path) -> None:
    """Décompresse un zip en ignorant les fichiers système et en refusant les chemins qui sortent du dossier."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.infolist():
            name = member.filename
            if member.is_dir() or name.startswith("__MACOSX") or Path(name).name.startswith("."):
                continue
            dest = (target / name).resolve()
            if target.resolve() not in dest.parents:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(member))


def create_job(files: list[tuple[str, bytes]] | None, name: str, model: str, input_from: str | None = None,
               owner: str | None = None) -> str:
    """Crée le dossier du traitement et y dépose les données (fichiers envoyés, ou copie d'un traitement précédent)."""
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir = JOBS_DIR / job_id
    while job_dir.exists():
        job_id += "b"
        job_dir = JOBS_DIR / job_id
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True)
    if input_from:
        shutil.copytree(JOBS_DIR / input_from / "input", input_dir, dirs_exist_ok=True)
    for filename, data in files or []:
        if filename.lower().endswith(".zip"):
            _safe_extract(data, input_dir)
        elif Path(filename).suffix.lower() in DATA_EXTENSIONS:
            (input_dir / Path(filename).name).write_bytes(data)
    if not any(p.suffix.lower() in DATA_EXTENSIONS for p in input_dir.rglob("*") if p.is_file()):
        shutil.rmtree(job_dir)
        raise ValueError("Aucun fichier de données reconnu (CSV, TSV, TXT, Excel, Parquet, JSON, ou un zip qui en contient).")
    meta = {"id": job_id, "name": name or job_id, "model": model, "owner": owner,
            "created": datetime.now().isoformat(timespec="seconds"), "from_job": input_from}
    (job_dir / "job.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return job_id


def launch(job_id: str) -> None:
    """Lance le pipeline dans un processus séparé : l'interface reste réactive pendant les longs calculs."""
    job_dir = JOBS_DIR / job_id
    meta = _read_json(job_dir / "job.json")
    cmd = [sys.executable, "-m", "biflow", "run", str(job_dir / "input"), "--job-dir", str(job_dir),
           "--model", meta.get("model", "qwen2.5:7b")]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"}
    log = open(job_dir / "run.log", "w", encoding="utf-8")
    common = dict(cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env)
    if os.name == "nt":
        # Processus indépendant et INVISIBLE : aucune fenêtre noire ne s'ouvre (ni pour lui, ni pour les
        # sous-processus de calcul), et l'analyse continue même si l'interface est arrêtée (Ctrl+C) ou relancée.
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            proc = subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **common)
        except OSError:                                   # certains terminaux interdisent de sortir de leur « job »
            proc = subprocess.Popen(cmd, creationflags=flags, **common)
    else:
        proc = subprocess.Popen(cmd, start_new_session=True, **common)
    (job_dir / "pid").write_text(str(proc.pid), encoding="utf-8")


def status(job_id: str) -> str:
    """running · success · blocked · failed · interrupted"""
    job_dir = JOBS_DIR / job_id
    result = _read_json(job_dir / "result.json")
    if result:
        return result.get("status", "failed")
    try:
        pid = int((job_dir / "pid").read_text())
        if psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE:
            return "running"
    except (OSError, ValueError, psutil.Error):
        pass
    return "interrupted"


def stop(job_id: str) -> None:
    try:
        psutil.Process(int((JOBS_DIR / job_id / "pid").read_text())).kill()
    except (OSError, ValueError, psutil.Error):
        pass


def delete(job_id: str) -> bool:
    """Supprime une analyse et tous ses fichiers (arrête d'abord le traitement s'il tourne encore)."""
    import stat
    import time
    job_dir = JOBS_DIR / job_id
    if not job_dir.is_dir() or job_dir.resolve().parent != JOBS_DIR.resolve():
        return False                                      # sécurité : on ne supprime que dans jobs/
    if status(job_id) == "running":
        stop(job_id)
        time.sleep(1)                                     # laisse Windows libérer les fichiers du processus

    def force(func, path, _exc):                          # fichiers en lecture seule (Windows)
        os.chmod(path, stat.S_IWRITE)
        func(path)

    for _ in range(3):
        try:
            shutil.rmtree(job_dir, onerror=force)
            return True
        except OSError:
            time.sleep(1)
    return not job_dir.exists()


def list_jobs(owner: str | None = None) -> list[dict]:
    """Analyses, des plus récentes aux plus anciennes. owner : seulement celles de cet utilisateur
    (les analyses lancées avant la création des comptes, sans propriétaire, restent visibles par tous)."""
    jobs = []
    for d in sorted(JOBS_DIR.glob("*"), reverse=True):
        meta = _read_json(d / "job.json")
        if meta and (owner is None or meta.get("owner") in (None, owner)):
            jobs.append({**meta, "status": status(meta["id"])})
    return jobs


def meta(job_id: str) -> dict:
    return _read_json(JOBS_DIR / job_id / "job.json") or {}


def progress(job_id: str) -> dict:
    return _read_json(JOBS_DIR / job_id / "progress.json") or {}


def result(job_id: str) -> dict | None:
    return _read_json(JOBS_DIR / job_id / "result.json")


def log_tail(job_id: str, lines: int = 30) -> str:
    try:
        text = (JOBS_DIR / job_id / "run.log").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-lines:])


def table(job_id: str, name: str):
    """Un tableau de résultats (results/<name>.csv), ou None."""
    import pandas as pd
    path = JOBS_DIR / job_id / "results" / f"{name}.csv"
    return pd.read_csv(path) if path.exists() else None


def star_schema(job_id: str) -> dict | None:
    """Description du modèle en étoile. Pour les analyses lancées avec une ancienne version du moteur,
    elle est reconstruite à partir du manifeste de l'entrepôt (tables, colonnes, identifiants)."""
    star = _read_json(JOBS_DIR / job_id / "results" / "star_schema.json")
    if star:
        return star
    res = result(job_id) or _read_json(JOBS_DIR / job_id / "results" / "partial.json") or {}
    run_dir = res.get("run_dir")
    manifest = _read_json(Path(run_dir) / "warehouse" / "etl_manifest.json") if run_dir else None
    if not manifest or not manifest.get("tables"):
        return None
    tables = manifest["tables"]
    star = {n: {"type": "fait" if n.startswith("fact_") else "dimension", "grain": t.get("grain"),
                "rows": t.get("rows"), "links": {}, "measures": []} for n, t in tables.items()}
    keys = {n: s["grain"][0] for n, s in star.items() if s["grain"] and len(s["grain"]) == 1}
    for n, t in tables.items():
        if star[n]["type"] != "fait":
            continue
        cols = set(t.get("columns", []))
        for target, key in keys.items():
            if target == n or key not in cols:
                continue
            if star[n]["grain"] == [key] and (star[target]["type"] != "fait" or
                                             (star[n]["rows"] or 0) > (star[target]["rows"] or 0)):
                continue                                  # sa propre clé : lien seulement vers le fait « en-tête »
            star[n]["links"][key] = [target, key]
        if "dim_date" in star:
            for c in cols:
                if c.endswith("_date_key"):
                    star[n]["links"][c] = ["dim_date", "date_key"]
    return star


def bi(job_id: str) -> dict:
    """Résumé de la partie 2 (secteur, KPI, analyse, dashboard)."""
    return _read_json(JOBS_DIR / job_id / "results" / "bi.json") or {}


def xai(job_id: str) -> dict:
    """Rapport de l'agent XAI (registre des décisions, questions d'exemple)."""
    return _read_json(JOBS_DIR / job_id / "results" / "xai.json") or {}


def insights(job_id: str) -> list[dict]:
    try:
        return json.loads((JOBS_DIR / job_id / "results" / "insights.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def dashboard_html(job_id: str) -> str | None:
    """Le tableau de bord produit par le Dashboard Generator Agent (fichier HTML autonome)."""
    path = bi(job_id).get("dashboard") or ((result(job_id) or {}).get("bi") or {}).get("dashboard")
    try:
        return Path(path).read_text(encoding="utf-8") if path else None
    except OSError:
        return None


def ollama_models(url: str) -> list[str] | None:
    """Modèles installés dans Ollama, ou None si Ollama ne répond pas."""
    try:
        return sorted(m["name"] for m in requests.get(f"{url}/api/tags", timeout=3).json().get("models", []))
    except (requests.RequestException, ValueError):
        return None
