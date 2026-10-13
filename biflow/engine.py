"""Moteur de déploiement : exécute les étapes du notebook, sans les modifier, dans un espace de noms partagé.

- la cellule LLM (GPU) est remplacée par OllamaLLM (CPU, sans clé d'API) ;
- la progression (pourcentage, étape en cours) est écrite dans <job>/progress.json ;
- les résultats de chaque agent sont publiés dans <job>/results/ dès que l'agent a terminé ;
- le résultat final est écrit dans <job>/result.json ;
- si une étape 4 ou 5 s'arrête (mode manuel sans décision, qualité bloquante), le moteur ne plante pas :
  il charge seulement les définitions restantes, et c'est l'orchestrateur (étape 6) qui donne le statut final.
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
              4: "Qualité et nettoyage", 5: "ETL : modèle en étoile", 6: "Orchestrateur LangGraph"}
STEP_WEIGHTS = {1: 5, 2: 10, 3: 30, 4: 25, 5: 15, 6: 15}       # part approximative du temps total (le LLM domine)

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


def _exec_definitions_only(source: str, ns: dict, name: str) -> None:
    """Mode dégradé : chaque instruction est tentée séparément ; celles qui échouent sont ignorées."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Expr):
            continue                                 # affichages / démonstrations
        try:
            exec(compile(ast.Module(body=[node], type_ignores=[]), name, "exec"), ns)
        except Exception:
            pass


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
        "review": {k: review.get(k) for k in ("mode", "reviewer", "approved", "escalated", "rejected", "added")},
        "llm": {"model": getattr(llm, "model_id", None), "calls": getattr(llm, "calls", None),
                "cache_hits": getattr(llm, "cache_hits", None)},
    }


def _publish_partial(ns: dict, job_dir: Path, llm, completed_step: int) -> None:
    """Résultats disponibles à la fin d'une étape : l'interface les affiche sans attendre la fin du traitement."""
    try:
        partial = _export(ns, job_dir, llm)
        partial["completed_step"] = completed_step
        (job_dir / "results" / "partial.json").write_text(json.dumps(partial, ensure_ascii=False, indent=1, default=str),
                                                          encoding="utf-8")
    except Exception as exc:                          # un affichage partiel ne doit jamais casser le traitement
        print(f"(résultats partiels non publiés : {exc})")


def run_pipeline(data_dir: str | Path, job_dir: str | Path, autonomy: str = "risk_based",
                 human_decision: dict | None = None, llm=None) -> dict:
    """Lance la Data Preparation Agent sur un dataset. Renvoie (et écrit dans <job>/result.json) le résultat."""
    data_dir, job_dir = Path(data_dir).resolve(), Path(job_dir).resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = STEPS_DIR / "manifest.json"
    if not manifest_path.exists() or NOTEBOOK.stat().st_mtime > manifest_path.stat().st_mtime:
        extract()                                     # notebook modifié (ou étapes absentes) : ré-extraction automatique
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cells = [m for m in manifest if not m["skip"]]
    progress = Progress(job_dir, cells)

    os.environ["BIFLOW_DATA_DIR"] = str(data_dir)     # lu par la cellule 1.1
    os.environ["BIFLOW_AUTONOMY"] = autonomy
    os.environ.setdefault("BIFLOW_CACHE_DIR", str(Path("biflow_cache").resolve()))   # cache partagé entre les runs
    if human_decision:                                # lu par la cellule 1.5 (./biflow_overrides.json)
        (job_dir / "biflow_overrides.json").write_text(json.dumps({"cleaning": human_decision}, ensure_ascii=False),
                                                       encoding="utf-8")
    cwd = os.getcwd()
    os.chdir(job_dir)                                 # ./biflow_runs et ./biflow_overrides.json sont propres à ce job
    llm = llm or OllamaLLM()
    module = types.ModuleType("biflow_pipeline")     # un vrai module : nécessaire aux dataclasses du notebook
    sys.modules["biflow_pipeline"] = module
    ns = module.__dict__
    ns.update({"display": _display, "_BIFLOW_LLM": llm})
    if hasattr(llm, "bind"):                          # LLM de test : accès à l'état du pipeline
        llm.bind(ns)
    degraded, result = False, None
    try:
        if hasattr(llm, "check"):
            llm.check()                               # échoue tout de suite si Ollama n'est pas prêt
        for i, cell in enumerate(cells):
            if i and cell["step"] != cells[i - 1]["step"]:    # une étape vient de se terminer
                done_step = cells[i - 1]["step"]
                if not degraded:
                    _publish_partial(ns, job_dir, llm, done_step)
                progress.update(completed_step=done_step)
            progress.at_cell(i, cell)
            print(f"\n### [{i + 1}/{len(cells)}] {cell['title']}", flush=True)
            source = LLM_CELL if cell["kind"] == "llm" else (STEPS_DIR / cell["file"]).read_text(encoding="utf-8")
            if cell["step"] == 6 and degraded:        # l'orchestrateur reprend la main avec le LLM réactivé
                degraded, llm.disabled = False, False
            if degraded:
                _exec_definitions_only(source, ns, cell["file"])
                continue
            try:
                _exec_cell(source, ns, cell["file"])
            except LLMUnavailable:
                raise
            except Exception as exc:
                if cell["step"] in (4, 5):            # arrêt « métier » : l'orchestrateur donnera le statut exact
                    print(f"!! Arrêt à {cell['title']} : {type(exc).__name__} : {exc}\n"
                          "!! Chargement des définitions restantes ; l'orchestrateur décide du statut final.", flush=True)
                    degraded, llm.disabled = True, True
                    _exec_definitions_only(source, ns, cell["file"])
                else:
                    raise
        result = _export(ns, job_dir, llm)
    except Exception as exc:
        traceback.print_exc()
        result = {"status": "failed", "error": f"{type(exc).__name__} : {exc}",
                  "llm": {"model": getattr(llm, "model_id", None), "calls": getattr(llm, "calls", 0)}}
    finally:
        os.chdir(cwd)
    result["autonomy"] = autonomy
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