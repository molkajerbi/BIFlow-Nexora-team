"""Moteur de déploiement : exécute les étapes du notebook, sans les modifier, dans un espace de noms partagé.

- la cellule LLM (GPU) est remplacée par OllamaLLM (CPU, sans clé d'API) ;
- la progression (pourcentage, étape en cours) est écrite dans <job>/progress.json ;
- les résultats de chaque agent sont publiés dans <job>/results/ dès que l'agent a terminé ;
- le résultat final est écrit dans <job>/result.json ;
- tout est automatique : aucune validation humaine n'est attendue ;
- les étapes 1 à 5 sont exécutées une seule fois ; l'étape 6 du notebook (orchestrateur LangGraph, qui rejoue
  toute la chaîne pour le futur BI Orchestrator) n'est pas relancée : le moteur livre directement le modèle en
  étoile et les données nettoyées produits par l'étape 5 (voir _deliver) ;
- si une étape 4 ou 5 s'arrête (qualité bloquante), le moteur ne plante pas : il livre le statut « bloqué » ou « échec ».
"""
from __future__ import annotations

import ast
import gc
import json
import os
import shutil
import sys
import time
import traceback
import types
from datetime import datetime, timezone
from pathlib import Path

from .extract import NOTEBOOK, extract
from .llm import LLMUnavailable, OllamaLLM

STEPS_DIR = Path(__file__).resolve().parent / "steps"
STEP_NAMES = {1: "Contrat et ingestion", 2: "Outils du Profiler", 3: "Agents LLM (Domaine + Profiler)",
              4: "Qualité et nettoyage", 5: "ETL : modèle en étoile"}
STEP_WEIGHTS = {1: 5, 2: 10, 3: 40, 4: 30, 5: 15}              # part approximative du temps total (le LLM domine)

LLM_CELL = """
LLM = _BIFLOW_LLM
LLM_MODEL_ID = getattr(LLM, "model_id", "test")
_t0 = time.perf_counter()
_answer = LLM.chat([{"role": "user", "content": "En une phrase : pourquoi une valeur manquante n'est-elle pas toujours une erreur ?"}], 60)
AUDIT.log("orchestrator", "llm_loaded", {
    "model": LLM_MODEL_ID, "backend": "ollama (CPU, local)", "url": getattr(LLM, "url", None),
    "num_ctx": getattr(LLM, "num_ctx", None), "decoding": "temperature=0, seed=42",
    "seconds": round(time.perf_counter() - _t0, 1)})
print(f"{LLM_MODEL_ID} via Ollama ({getattr(LLM, 'url', '-')}) : {_answer}")
"""


class Progress:
    def __init__(self, job_dir: Path, cells: list[dict]):
        self.path = job_dir / "progress.json"
        per_step = {s: sum(c["step"] == s for c in cells) for s in STEP_WEIGHTS}
        self.weights = [STEP_WEIGHTS.get(c["step"], 5) / max(per_step.get(c["step"], 1), 1) for c in cells]
        self.state = {"status": "running", "percent": 0, "step_num": 1, "completed_step": 0, "done": 0,
                      "total": len(cells), "step": None, "cell": None,
                      "started_at": datetime.now(timezone.utc).isoformat(), "elapsed_s": 0, "error": None}
        self._t0 = time.perf_counter()
        self.write()

    def at_cell(self, i: int, cell: dict) -> None:
        """i : nombre de cellules déjà terminées."""
        pct = 100 * sum(self.weights[:i]) / sum(self.weights)
        self.update(done=i, percent=round(min(pct, 99)), step_num=cell["step"],
                    step=f"{cell['step']}. {STEP_NAMES.get(cell['step'], '')}", cell=cell["title"])

    def update(self, **kw) -> None:
        self.state.update(kw, elapsed_s=round(time.perf_counter() - self._t0))
        self.write()

    def write(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)                       # écriture atomique : l'interface ne lit jamais un fichier à moitié écrit


def _display(obj) -> None:
    """Remplace display() de Jupyter : affichage texte dans le journal."""
    try:
        print(obj.head(30).to_string() if hasattr(obj, "head") else obj)
    except Exception:
        print(obj)


def _exec_cell(source: str, ns: dict, name: str) -> None:
    """Exécute une cellule comme Jupyter (la dernière expression est affichée)."""
    tree = ast.parse(source)
    last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
    exec(compile(tree, name, "exec"), ns)
    if last is not None:
        value = eval(compile(ast.Expression(last.value), name, "eval"), ns)
        if value is not None:
            _display(value)


def _export(ns: dict, job_dir: Path, llm) -> dict:
    """Résultats lisibles par l'interface (JSON + CSV), à partir des variables du pipeline.
    Appelé à la fin de chaque étape (résultats partiels) puis à la fin du traitement."""
    import pandas as pd
    res_dir = job_dir / "results"
    res_dir.mkdir(exist_ok=True)

    def save(name: str, df) -> None:
        if isinstance(df, pd.DataFrame) and len(df.columns):
            df.to_csv(res_dir / f"{name}.csv", index=not isinstance(df.index, pd.RangeIndex))

    final = ns.get("DATA_PREP_RESULT") or {}
    contract = ns.get("DATA_CONTRACT", {})
    stats = ns.get("INFERRED", {}).get("stats", {})
    save("contract_tables", pd.DataFrame([{
        "table": t, "rôle": ns.get("TABLE_ROLES", {}).get(t), "lignes": stats.get(t, {}).get("rows"),
        "colonnes": len(s["columns"]), "grain": ", ".join(s["grain"] or []), "description": s.get("description")}
        for t, s in contract.items()]))
    save("contract_columns", pd.DataFrame([{"table": t, "colonne": c, "type": sem}
                                           for t, s in contract.items() for c, sem in s["columns"].items()]))
    save("relationships", pd.DataFrame(ns.get("RELATIONSHIPS", [])))
    for var, name in [("PROFILING_REPORT", "profiling_report"), ("HEALTH", "health_map"), ("RULES_BEFORE", "rules_before"),
                      ("RULES_AFTER", "rules_after"), ("CLEANING_PLAN", "cleaning_plan"), ("EXECUTION", "corrections_applied"),
                      ("OTHER_TREATMENTS", "dismissed"), ("DERIVED", "derived_indicators")]:
        save(name, ns.get(var))
    if isinstance(ns.get("CHANGES"), pd.DataFrame) and len(ns["CHANGES"]):
        changes = ns["CHANGES"]                       # quelques exemples par correction (avant -> après)
        save("cell_changes_sample", changes.groupby("correction", group_keys=False).head(20))
    if "SCORES_BEFORE" in ns:
        save("quality_scores", pd.DataFrame({"avant": ns["SCORES_BEFORE"], "après": ns.get("SCORES_AFTER")}))
    if ns.get("ETL_RESULTS"):
        save("etl_tests", pd.DataFrame([{"table": n, "type": ns["ETL_TEMPLATES"][n]["type"], "lignes": r["rows"],
                                         "colonnes": r["columns"], **r["tests"], "OK": r["passed"], "construite_par": r["decided_by"]}
                                        for n, r in ns["ETL_RESULTS"].items()]))
        star = {n: {"type": t["type"], "grain": t.get("grain"), "rows": ns["ETL_RESULTS"].get(n, {}).get("rows"),
                    "links": {c: list(v) for c, v in (t.get("fks") or {}).items()},
                    "measures": list((t.get("sums") or {}).keys()), "description": t.get("description")}
                for n, t in ns["ETL_TEMPLATES"].items()}
        (res_dir / "star_schema.json").write_text(json.dumps(star, ensure_ascii=False, indent=1, default=str),
                                                  encoding="utf-8")
    candidates = [{"id": c["id"], "correction": c["correction"], "table": c["table"], "colonne": c["column"],
                   "règle": c["rule"], "violations": c["violations"], "statut": c["status"], "justification": c.get("agent_reason"),
                   "décidé_par": c.get("decided_by")}
                  for c in ns.get("CANDIDATES", [])]
    save("candidates", pd.DataFrame(candidates))

    run_dir = ns.get("RUN_DIR")
    out_dir = Path(final.get("outputs", {}).get("directory", "")) if final.get("outputs") else None
    review = ns.get("REVIEW") or {}
    raw = ns.get("RAW")
    return {
        "status": final.get("status", "failed"), "error": final.get("error"),
        "domain": ns.get("DOMAIN"), "run_id": ns.get("RUN_ID"), "run_dir": str(Path(run_dir).resolve()) if run_dir else None,
        "output_dir": str(out_dir.resolve()) if out_dir else None, "history": final.get("history", []),
        "profiler": final.get("profiler"), "quality": final.get("quality"), "etl": final.get("etl"),
        "outputs": final.get("outputs"), "confidence_pct": ns.get("INFERRED", {}).get("confidence"),
        "points_to_check": ns.get("INFERRED", {}).get("checks"),
        "input": {"tables": len(contract), "rows": int(sum(s.get("rows", 0) for s in stats.values())),
                  "files": len(raw.manifest) if raw is not None else len(contract)},
        "quality_status": ns.get("STATUS"),
        "review": {k: review.get(k) for k in ("mode", "reviewer", "approved", "set_aside")},
        "llm": {"model": getattr(llm, "model_id", None), "calls": getattr(llm, "calls", None),
                "cache_hits": getattr(llm, "cache_hits", None)},
    }


def _deliver(ns: dict, error: str | None) -> dict:
    """Livraison, sans rien recalculer : le modèle en étoile (base + CSV, déjà produits par l'étape 5) et les données
    nettoyées, après un contrôle rapide (données brutes inchangées, journal d'audit intact)."""
    import pandas as pd
    status = ns.get("STATUS")
    run_dir = Path(ns["RUN_DIR"]) if ns.get("RUN_DIR") else None
    etl_ok = bool(ns.get("ETL_STATUS")) and all(s == "testée" for s in ns["ETL_STATUS"].values())
    if status == "blocked":
        final = {"status": "blocked", "error": "qualité bloquante : le modèle en étoile n'a pas été construit"}
    elif error or not etl_ok or run_dir is None:
        final = {"status": "failed", "error": error or "construction du modèle en étoile incomplète"}
    else:
        final = {"status": "success", "error": None}
    q_run, agent_run, etl_run = ns.get("Q_RUN") or {}, ns.get("AGENT_RUN") or {}, ns.get("ETL_RUN") or {}
    report = ns.get("PROFILING_REPORT")
    final["profiler"] = {"investigations": len(ns.get("REQUIRED") or []), "by_agent": len(agent_run.get("done", [])),
                         "findings": 0 if report is None else len(report),
                         "interpreted_by_llm": 0 if report is None else int((report["source"] == "LLM").sum())}
    final["quality"] = {"candidates": len(ns.get("CANDIDATES") or []), "decided_by_agent": q_run.get("decided_by_agent"),
                        "corrections_applied": len(ns["EXECUTION"]) if "EXECUTION" in ns else 0,
                        "cells_changed": len(ns["CHANGES"]) if "CHANGES" in ns else 0,
                        "rows_changed": len(ns["ROW_CHANGES"]) if "ROW_CHANGES" in ns else 0, "quality_status": status}
    final["etl"] = {"tables_built": sum(s == "testée" for s in (ns.get("ETL_STATUS") or {}).values()),
                    "tables_expected": len(ns.get("ETL_TEMPLATES") or {}), "built_by_agent": etl_run.get("built_by_agent")}
    if final["status"] != "success":
        return final
    clean_dir = run_dir / "donnees_nettoyees"                  # données nettoyées, une table par fichier
    clean_dir.mkdir(exist_ok=True)
    for name, df in ns["SILVER"].items():
        df.to_csv(clean_dir / f"{name}.csv", index=False)
    warehouse = run_dir / "warehouse"                         # modèle en étoile : base + CSV (étape 5)
    raw_ok = bool(ns["checkpoint_raw_integrity"]()["contenu_inchangé"].all())
    chain_ok, chain_msg = ns["AUDIT"].verify()
    outputs = {"directory": str(warehouse), "warehouse": str(ns["WH"].path), "cleaned_data": str(clean_dir),
               "tables": {n: len(d) for n, d in (ns.get("STAR") or {}).items()},
               "raw_unchanged": raw_ok, "audit_chain": chain_msg}
    ns["AUDIT"].log("orchestrator", "data_preparation_delivered", outputs)
    (warehouse / "data_preparation_manifest.json").write_text(json.dumps(
        {"run_id": ns.get("RUN_ID"), "profiler": final["profiler"], "quality": final["quality"], "etl": final["etl"],
         "outputs": outputs}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    final["outputs"] = outputs
    if not (raw_ok and chain_ok):
        final.update(status="failed", error="contrôle final en échec (données brutes ou journal d'audit modifiés)")
    return final


def _publish_partial(ns: dict, job_dir: Path, llm, completed_step: int) -> None:
    """Résultats disponibles à la fin d'une étape : l'interface les affiche sans attendre la fin du traitement."""
    try:
        partial = _export(ns, job_dir, llm)
        partial["completed_step"] = completed_step
        (job_dir / "results" / "partial.json").write_text(json.dumps(partial, ensure_ascii=False, indent=1, default=str),
                                                          encoding="utf-8")
    except Exception as exc:                          # un affichage partiel ne doit jamais casser le traitement
        print(f"(résultats partiels non publiés : {exc})")


def run_pipeline(data_dir: str | Path, job_dir: str | Path, llm=None) -> dict:
    """Lance la Data Preparation Agent (100 % automatique) sur un dataset.
    Renvoie (et écrit dans <job>/result.json) le résultat."""
    data_dir, job_dir = Path(data_dir).resolve(), Path(job_dir).resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = STEPS_DIR / "manifest.json"
    if not manifest_path.exists() or NOTEBOOK.stat().st_mtime > manifest_path.stat().st_mtime:
        extract()                                     # notebook modifié (ou étapes absentes) : ré-extraction automatique
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cells = [m for m in manifest if not m["skip"] and m["step"] in STEP_NAMES]   # étapes 1 à 5 (pas l'étape 6)
    progress = Progress(job_dir, cells)

    os.environ["BIFLOW_DATA_DIR"] = str(data_dir)     # lu par la cellule 1.1
    os.environ.setdefault("BIFLOW_CACHE_DIR", str(Path("biflow_cache").resolve()))   # cache partagé entre les runs
    cwd = os.getcwd()
    os.chdir(job_dir)                                 # ./biflow_runs est propre à ce job
    llm = llm or OllamaLLM()
    module = types.ModuleType("biflow_pipeline")     # un vrai module : nécessaire aux dataclasses du notebook
    sys.modules["biflow_pipeline"] = module
    ns = module.__dict__
    ns.update({"display": _display, "_BIFLOW_LLM": llm})
    if hasattr(llm, "bind"):                          # LLM de test : accès à l'état du pipeline
        llm.bind(ns)
    stop_error, result = None, None
    try:
        if hasattr(llm, "check"):
            llm.check()                               # échoue tout de suite si Ollama n'est pas prêt
        for i, cell in enumerate(cells):
            if i and cell["step"] != cells[i - 1]["step"]:    # une étape vient de se terminer
                done_step = cells[i - 1]["step"]
                _publish_partial(ns, job_dir, llm, done_step)
                progress.update(completed_step=done_step)
            progress.at_cell(i, cell)
            print(f"\n### [{i + 1}/{len(cells)}] {cell['title']}", flush=True)
            source = LLM_CELL if cell["kind"] == "llm" else (STEPS_DIR / cell["file"]).read_text(encoding="utf-8")
            try:
                _exec_cell(source, ns, cell["file"])
            except LLMUnavailable:
                raise
            except Exception as exc:
                if cell["step"] not in (4, 5):
                    raise
                stop_error = f"{cell['title']} : {type(exc).__name__} : {exc}"     # arrêt « métier » (qualité bloquante…)
                print(f"!! Arrêt à {stop_error}", flush=True)
                break
        progress.update(completed_step=5 if stop_error is None else progress.state["completed_step"],
                        step="Livraison", cell="Livraison du modèle en étoile et des données nettoyées", percent=99)
        print("\n### Livraison : modèle en étoile et données nettoyées", flush=True)
        ns["DATA_PREP_RESULT"] = _deliver(ns, stop_error)
        result = _export(ns, job_dir, llm)
    except Exception as exc:
        traceback.print_exc()
        result = {"status": "failed", "error": f"{type(exc).__name__} : {exc}",
                  "llm": {"model": getattr(llm, "model_id", None), "calls": getattr(llm, "calls", 0)}}
    finally:
        os.chdir(cwd)
    result["data_dir"] = str(data_dir)
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    for obj in gc.get_objects():                      # ferme les entrepôts (sous Windows, un fichier ouvert est verrouillé)
        if type(obj).__name__ == "Warehouse":
            try:
                obj.con.close()
            except Exception:
                pass
    if result.get("output_dir"):                      # zip de tous les livrables, prêt à télécharger
        try:
            shutil.make_archive(str(job_dir / "biflow_outputs"), "zip", result["run_dir"])
        except OSError as exc:
            print(f"Zip des livrables impossible : {exc}")
    (job_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    progress.update(status=result["status"], done=len(cells), percent=100, error=result.get("error"),
                    completed_step=6 if result["status"] == "success" else progress.state["completed_step"])
    return result