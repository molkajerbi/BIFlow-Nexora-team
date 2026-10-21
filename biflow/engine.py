"""Moteur de déploiement : exécute les étapes du notebook, sans les modifier, dans un espace de noms partagé.

Le moteur joue le rôle du BI Orchestrator global du notebook (étape 13) :
  partie 1  Data Preparation Agent  (étapes 1 à 5, puis livraison du modèle en étoile et des données nettoyées)
  partie 2  BI & Insight Agent      (étapes 7 à 10 : base de connaissances, KPI, analyse, dashboard)
  partie 3  XAI Agent               (étape 12 : registre des décisions et explications ; toujours construit)

- la cellule LLM (GPU) est remplacée par OllamaLLM (CPU, sans clé d'API) ;
- chaque cellule n'est exécutée qu'une seule fois : les cellules qui « refont tout » (relances 6.6, 11.4, 13.3…)
  sont ignorées, les cellules qui définissent les orchestrateurs (6.1 à 6.5, 11.1 à 11.3) sont gardées ;
- après chaque étape de la partie 2, son point de contrôle (ok7 … ok10) est relu, comme le fait run_bi_insight() :
  s'il est faux, la partie 2 s'arrête proprement avec la raison ;
- l'explicabilité est toujours construite, même après un arrêt : le chat peut alors expliquer pourquoi ;
- la progression est écrite dans <job>/progress.json et les résultats de chaque agent dans <job>/results/
  dès que l'agent a terminé ; le résultat final est écrit dans <job>/result.json.
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
STEP_NAMES = {1: "Contract and ingestion", 2: "Profiler tools", 3: "LLM agents (Domain + Profiler)",
              4: "Quality and cleaning", 5: "ETL: star schema", 6: "Data preparation delivery",
              7: "KPI knowledge base", 8: "KPI agent", 9: "Analyst agent", 10: "Dashboard agent",
              11: "BI orchestration", 12: "Explainability (XAI)"}
# Titres des sections du notebook, en anglais (affichés « Right now: … » pendant l'analyse)
SECTION_TITLES = {
    "1.1": "Configuration", "1.2": "Tamper-proof audit log", "1.4": "Automatic data contract inference",
    "1.5": "Active contract and confidence score", "1.6": "Traceable ingestion (bronze zone)",
    "1.7": "Preview and step 1 checkpoint", "1.8": "Step 1 audit log", "2.1": "Automatic traceability and validators",
    "2.2": "Tool 1: column profile", "2.3": "Tool 2: uniqueness and duplicates", "2.4": "Tool 3: relationships between tables",
    "2.5": "Tool 4: missing values explained", "2.6": "Tool 5: anomaly detection", "2.7": "Dataset health map",
    "2.8": "Quality findings", "2.9": "Step 2 checkpoint", "3.1": "Local LLM", "3.2": "Traced LLM call and JSON extraction",
    "3.3": "Domain & Contract Agent: understanding the business", "3.4": "Profiler Agent · phase 1: deterministic screening",
    "3.5": "Profiler Agent · phase 2: LLM-driven investigation", "3.6": "Investigation findings",
    "3.7": "Profiler Agent · phase 3: business interpretation", "3.8": "Profiling report and checkpoint",
    "4.1": "Typing (silver zone)", "4.1 bis": "Missing, impossible and extreme values: the policy",
    "4.2": "Quality rules engine (DAMA)", "4.3": "Quality score per dimension (before cleaning)",
    "4.4": "Candidate fixes and sandbox", "4.5": "Quality agent: test, observe, decide", "4.6": "Risk-based automatic validation",
    "4.7": "Controlled application of the fixes", "4.8": "Re-validation and Data Quality Report", "4.9": "Step 4 checkpoint",
    "5.1": "Pre-check and SQL warehouse", "5.2": "Staging and time indicators", "5.3": "Automatic star schema design and tests",
    "5.4": "ETL Agent: planning and building", "5.5": "Test results and the double-counting trap",
    "5.6": "Export and step 5 checkpoint", "6.1": "Graph engine", "6.2": "Shared state and node wrapper", "6.3": "Graph nodes",
    "6.4": "Building the graph", "6.5": "Single entry point", "7.1": "Bridge: what part 1 hands over to part 2",
    "7.2": "Semantic inventory: what can be computed", "7.3": "KPI knowledge base", "7.4": "Knowledge base validation",
    "7.5": "Semantic search engine (RAG)", "7.6": "Feasibility of each KPI on this dataset",
    "7.7": "Business sector: search proposes, LLM decides, code checks", "7.8": "Reference KPIs handed to the KPI agent",
    "7.9": "Step 7 checkpoint", "8.1": "Compiler: from the closed language to SQL (and pandas)",
    "8.2": "KPI binding: automatic when obvious, LLM when in doubt", "8.3": "Computing and testing each KPI",
    "8.4": "KPIs proposed by the agent", "8.5": "KPI catalog", "8.6": "Step 8 checkpoint", "9.1": "Reliable monthly series",
    "9.2": "Statistical rules: detecting what changes", "9.3": "Breakdown by segment", "9.4": "LLM-driven investigation",
    "9.5": "Writing verified insights", "9.6": "Analysis report and checkpoint", "10.1": "Dashboard candidates",
    "10.2": "Layout: the LLM chooses, the supervisor applies best practices", "10.3": "Template: styles and rendering engine",
    "10.4": "Dashboard generation", "10.5": "Checks and checkpoint", "11.1": "Step registry", "11.2": "Orchestration graph",
    "11.3": "Single entry point", "12.1": "Decision ledger", "12.2": "System rules: how each agent decides",
    "12.3": "Explanation search engine", "12.4": "Answer: rules explain, LLM rephrases, code checks",
    "12.5": "The chat", "12.6": "Evaluation and checkpoint",
}


def _title(cell: dict) -> str:
    """Titre anglais d'une cellule (« 8.3 Computing and testing each KPI »), sinon le titre du notebook."""
    import re
    m = re.match(r"(\d+\.\d+(?: bis)?)", cell["title"])
    return f"{m.group(1)} {SECTION_TITLES[m.group(1)]}" if m and m.group(1) in SECTION_TITLES else cell["title"]
STEP_WEIGHTS = {1: 3, 2: 6, 3: 26, 4: 20, 5: 8, 6: 1, 7: 8, 8: 12, 9: 9, 10: 4, 11: 1, 12: 2}   # part du temps (le LLM domine)
PREP_STEPS, BI_STEPS, XAI_STEPS = {1, 2, 3, 4, 5}, {7, 8, 9, 10, 11}, {12}
BI_CHECKPOINTS = {7: ("ok7", "checks7"), 8: ("ok8", "checks8"), 9: ("ok9", "checks9"), 10: ("ok10", "checks10")}
TESTED = {"testée", "tested"}

# Le notebook anglais a traduit les clés de ses tableaux. L'interface (et les analyses déjà faites avec l'ancien notebook
# français) lit les noms d'origine : les résultats exportés sont donc renommés vers ces noms, un tableau à la fois.
RENAME = {
    "profiling_report": {"column": "colonne", "finding": "constat"},
    "health_map": {"rows": "lignes", "columns": "colonnes", "missing_cells_%": "cellules_manquantes_%",
                   "columns_with_missing": "colonnes_avec_manquants", "invalid_values": "valeurs_non_conformes",
                   "unique_grain": "grain_unique", "exact_duplicates": "doublons_exacts", "IF_anomalies": "anomalies_IF",
                   "IQR_extremes": "extrêmes_IQR"},
    "cleaning_plan": {"column": "colonne", "decided_by": "décidé_par", "candidate": "candidat", "findings": "constats",
                      "simulated_effect": "effet_simulé"},
    "derived_indicators": {"column": "colonne", "calculation": "calcul"},
    "dismissed": {"item": "élément", "treatment": "traitement"},
    "decisions": {"step": "étape", "subject": "sujet", "object": "objet", "decision": "décision", "why": "pourquoi",
                  "decided_by": "décidé_par"},
}
INSIGHT_KEYS = {"title": "titre", "text": "texte", "recommendation": "recommandation", "facts": "faits"}


def _get(d: dict, *keys):
    """Valeur de la première clé présente (clé anglaise du nouveau notebook, ou clé française de l'ancien)."""
    return next((d[k] for k in keys if k in d), None)


def _col(df, *names):
    """Première colonne présente : le notebook anglais et l'ancien notebook français n'ont pas les mêmes noms."""
    return next((n for n in names if n in df), names[0])


BI_NODES = {7: "bridge_agent", 8: "kpi_agent", 9: "analyst_agent", 10: "dashboard_agent"}

LLM_CELL = """
LLM = _BIFLOW_LLM
LLM_MODEL_ID = getattr(LLM, "model_id", "test")
_t0 = time.perf_counter()
_answer = LLM.chat([{"role": "user", "content": "In one sentence: why is a missing value not always an error?"}], 60)
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
        self.weights = [STEP_WEIGHTS.get(c["step"], 1) / max(per_step.get(c["step"], 1), 1) for c in cells]
        self.state = {"status": "running", "percent": 0, "step_num": 1, "completed_step": 0, "done": 0,
                      "total": len(cells), "step": None, "cell": None,
                      "started_at": datetime.now(timezone.utc).isoformat(), "elapsed_s": 0, "error": None}
        self._t0 = time.perf_counter()
        self.write()

    def at_cell(self, i: int, cell: dict) -> None:
        """i : nombre de cellules déjà terminées."""
        pct = 100 * sum(self.weights[:i]) / sum(self.weights)
        self.update(done=i, percent=round(min(pct, 99)), step_num=cell["step"],
                    step=f"{cell['step']}. {STEP_NAMES.get(cell['step'], '')}", cell=_title(cell))

    def update(self, **kw) -> None:
        self.state.update(kw, elapsed_s=round(time.perf_counter() - self._t0))
        self.write()

    def write(self) -> None:
        """Écriture atomique (l'interface ne lit jamais un fichier à moitié écrit). Sous Windows, le remplacement est
        refusé pendant que l'interface lit le fichier (toutes les 3 s) : on réessaie, puis on écrit directement.
        Un problème d'affichage de la progression ne doit JAMAIS arrêter l'analyse."""
        text = json.dumps(self.state, ensure_ascii=False, indent=1)
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(text, encoding="utf-8")
            for _ in range(20):
                try:
                    tmp.replace(self.path)
                    return
                except PermissionError:              # fichier ouvert en lecture par l'interface
                    time.sleep(0.1)
            self.path.write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"(progress not saved: {exc})", flush=True)


def _display(*objs, **_kw) -> None:
    """Remplace display() de Jupyter : affichage texte dans le journal."""
    for obj in objs:
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


def _records(obj) -> list:
    """Liste de dictionnaires sérialisables (DataFrame, liste ou dictionnaire)."""
    import pandas as pd
    if isinstance(obj, pd.DataFrame):
        return json.loads(obj.to_json(orient="records", force_ascii=False, default_handler=str))
    return obj or []


def _export_bi(ns: dict, res_dir: Path, save) -> dict | None:
    """Résultats de la partie 2 (KPI, analyse, dashboard) lisibles par l'interface."""
    import pandas as pd
    if "BI_INPUT" not in ns:
        return None
    info = {"domain": ns["BI_INPUT"].get("domain"), "sectors": ns.get("BI_SECTORS"), "mode": ns.get("BI_MODE"),
            "sector_reason": ns.get("sector_reason"), "sector_source": ns.get("sector_source"),
            "reference_date": ns.get("REF_DATE"), "search_mode": getattr(ns.get("SEARCH"), "mode", None),
            "facts_tables": ns.get("BI_FACTS")}
    if isinstance(ns.get("SECTOR_EVIDENCE"), pd.DataFrame):
        save("bi_sector_evidence", ns["SECTOR_EVIDENCE"])
    if isinstance(ns.get("KPI_CATALOG"), pd.DataFrame):
        cat = ns["KPI_CATALOG"].copy()
        fmt = ns.get("fmt_value")
        cat["valeur"] = [fmt(v, u) if fmt else v for v, u in zip(cat["value"], cat["unit"])]
        keep = ["id", "name", "valeur", "value", "unit", "direction", "status", "binding", "sector", "definition",
                "formula", "fact", "columns", "reliability", "periods", "sql"]
        save("kpi_catalog", cat[[c for c in keep if c in cat]])
        reasons = {k: (b.get("reason") or "") for k, b in (ns.get("BINDINGS") or {}).items()}
        info.update(kpis=len(cat), validated=int(cat["status"].str.startswith(("validé", "validated")).sum()),
                    to_confirm=int(cat["status"].isin(["à confirmer", "to confirm"]).sum()),
                    proposed=len(ns.get("PROPOSALS") or {}), dropped=ns.get("DROPPED") or {},
                    failed={k: str(v) for k, v in (ns.get("FAILED") or {}).items()}, binding_reasons=reasons)
    if ns.get("KPI_SERIES"):
        pd.concat(ns["KPI_SERIES"].values(), ignore_index=True)[["id", "period", "v"]].to_csv(res_dir / "kpi_series.csv",
                                                                                             index=False)
    if "FACTS" in ns:
        facts = [{"id": f.get("id"), "kpi": f.get("kpi"), "label": f.get("label"), "type": f.get("type"),
                  "texte": _get(f, "text", "texte"), "priority": f.get("priority"), "valence": f.get("valence"),
                  "sens": f.get("sens", f.get("direction"))} for f in ns["FACTS"].values()]
        save("analysis_facts", pd.DataFrame(facts))
        not_signal = {"valeur", "value", "segment", "contribution"}
        info.update(series=len(ns.get("SERIES") or {}),
                    signals=sum(1 for f in ns["FACTS"].values() if f["type"] not in not_signal),
                    segments=sum(1 for f in ns["FACTS"].values() if f["type"] in {"segment", "contribution"}),
                    investigations=[{"fait": _get(i, "fact", "fait"), "axe": list(_get(i, "axis", "axe"))[-1],
                                     "pourquoi": _get(i, "why", "pourquoi"), "source": i.get("source"),
                                     "résultat": _get(i, "result", "résultat")}
                                    for i in ns.get("INVESTIGATIONS") or []],
                    reliable_periods={f: [p[0], p[-1]] if p else [] for f, p in (ns.get("RELIABLE") or {}).items()})
    if "INSIGHTS" in ns and "ANALYSIS" in ns:
        insights = [{INSIGHT_KEYS.get(k, k): v for k, v in i.items()} for i in ns["INSIGHTS"]]
        (res_dir / "insights.json").write_text(json.dumps(insights, ensure_ascii=False, indent=1, default=str),
                                               encoding="utf-8")
        info.update(insights=len(ns["INSIGHTS"]), insights_llm=sum(i.get("source") == "LLM" for i in ns["INSIGHTS"]))
    if ns.get("DASHBOARD_PATH") and Path(ns["DASHBOARD_PATH"]).exists() and "checks10" in ns:
        info.update(dashboard=str(Path(ns["DASHBOARD_PATH"]).resolve()), layout_source=ns.get("layout_source"),
                    dashboard_title=_get(ns.get("LAYOUT") or {}, "title", "titre"))
    (res_dir / "bi.json").write_text(json.dumps(info, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return info


def _export_xai(ns: dict, res_dir: Path, save) -> dict | None:
    """Registre des décisions et rapport de l'agent XAI (le chat de l'interface les relit)."""
    import pandas as pd
    if not isinstance(ns.get("DECISIONS"), pd.DataFrame) or "XAI_REPORT" not in ns:
        return None
    d = ns["DECISIONS"]
    save("decisions", d[[c for c in ("id", "step", "étape", "agent", "subject", "sujet", "object", "objet", "decision",
                                     "décision", "why", "pourquoi", "decided_by", "décidé_par") if c in d]])
    info = {**ns["XAI_REPORT"], "ready": True, "demo_questions": ns.get("DEMO_QUESTIONS") or [],
            "checkpoint": bool(ns.get("ok12")), "xai_dir": str(Path(ns["XAI_DIR"]).resolve())}
    (res_dir / "xai.json").write_text(json.dumps(info, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return info


def _export(ns: dict, job_dir: Path, llm, run_info: dict | None = None) -> dict:
    """Résultats lisibles par l'interface (JSON + CSV), à partir des variables du pipeline.
    Appelé à la fin de chaque étape (résultats partiels) puis à la fin du traitement."""
    import pandas as pd
    res_dir = job_dir / "results"
    res_dir.mkdir(exist_ok=True)

    def save(name: str, df) -> None:
        if isinstance(df, pd.DataFrame) and len(df.columns):
            df = df.rename(columns=RENAME.get(name, {}))
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
        star = {n: {"type": "fait" if t["type"] in ("fait", "fact") else t["type"], "grain": t.get("grain"), "rows": ns["ETL_RESULTS"].get(n, {}).get("rows"),
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

    run_info = run_info or {}
    bi = _export_bi(ns, res_dir, save)
    xai = _export_xai(ns, res_dir, save)
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
        "bi": {**(bi or {}), **(run_info.get("bi") or {})} if (bi or run_info.get("bi")) else None,
        "xai": {**(xai or {}), **(run_info.get("xai") or {})} if (xai or run_info.get("xai")) else None,
        "parts": run_info.get("parts", []),
        "llm": {"model": getattr(llm, "model_id", None), "calls": getattr(llm, "calls", None),
                "cache_hits": getattr(llm, "cache_hits", None)},
    }


def _deliver(ns: dict, error: str | None) -> dict:
    """Livraison de la partie 1, sans rien recalculer : le modèle en étoile (base + CSV, déjà produits par l'étape 5) et
    les données nettoyées, après un contrôle rapide (données brutes inchangées, journal d'audit intact)."""
    status = ns.get("STATUS")
    run_dir = Path(ns["RUN_DIR"]) if ns.get("RUN_DIR") else None
    etl_ok = bool(ns.get("ETL_STATUS")) and all(s in TESTED for s in ns["ETL_STATUS"].values())
    if status == "blocked":
        final = {"status": "blocked", "error": "blocking data quality: the star schema was not built"}
    elif error or not etl_ok or run_dir is None:
        final = {"status": "failed", "error": error or "star schema build incomplete"}
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
    final["etl"] = {"tables_built": sum(s in TESTED for s in (ns.get("ETL_STATUS") or {}).values()),
                    "tables_expected": len(ns.get("ETL_TEMPLATES") or {}), "built_by_agent": etl_run.get("built_by_agent")}
    if final["status"] != "success":
        return final
    clean_dir = run_dir / "cleaned_data"                      # données nettoyées, une table par fichier
    clean_dir.mkdir(exist_ok=True)
    for name, df in ns["SILVER"].items():
        df.to_csv(clean_dir / f"{name}.csv", index=False)
    warehouse = run_dir / "warehouse"                         # modèle en étoile : base + CSV (étape 5)
    integrity = ns["checkpoint_raw_integrity"]()
    raw_ok = bool(integrity[_col(integrity, "content_unchanged", "contenu_inchangé")].all())
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
        final.update(status="failed", error="final check failed (raw data or audit log modified)")
    return final


def _publish_partial(ns: dict, job_dir: Path, llm, completed_step: int, run_info: dict) -> None:
    """Résultats disponibles à la fin d'une étape : l'interface les affiche sans attendre la fin du traitement."""
    try:
        partial = _export(ns, job_dir, llm, run_info)
        partial["completed_step"] = completed_step
        (job_dir / "results" / "partial.json").write_text(json.dumps(partial, ensure_ascii=False, indent=1, default=str),
                                                          encoding="utf-8")
    except Exception as exc:                          # un affichage partiel ne doit jamais casser le traitement
        print(f"(partial results not published: {exc})")


def _failed_checks(ns: dict, step: int) -> str:
    ok_name, checks_name = BI_CHECKPOINTS[step]
    failed = [k for k, v in (ns.get(checks_name) or {}).items() if not v]
    return f"step {step} checkpoint failed: {', '.join(failed) or '?'}"


def _embeddings_usable() -> bool:
    """Teste le modèle d'embeddings (étape 7.5) dans un processus à part, AVANT de le charger dans le pipeline.
    Sous Windows, une bibliothèque torch mal installée peut faire planter Python d'un coup (sans message) au lieu de
    lever une erreur : le test protège le pipeline, qui passe alors en recherche lexicale (repli prévu par le notebook).
    Le premier test télécharge le modèle (Internet nécessaire une seule fois)."""
    import subprocess
    name = os.environ.get("BIFLOW_EMBED_MODEL", "intfloat/multilingual-e5-small")
    code = ("from sentence_transformers import SentenceTransformer; "
            f"SentenceTransformer({name!r}, device='cpu').encode(['test']); print('ok')")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=1800,
                           creationflags=flags, env={**os.environ, "PYTHONUTF8": "1"})
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"Embeddings: test failed ({exc}): lexical search", flush=True)
        return False
    if r.returncode == 0 and "ok" in r.stdout:
        print("Embeddings: multilingual model available", flush=True)
        return True
    last = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [f"exit code {r.returncode}"]
    print(f"Embeddings unavailable ({last[0][:200]}): lexical search", flush=True)
    return False


def run_pipeline(data_dir: str | Path, job_dir: str | Path, llm=None) -> dict:
    """Lance BIFlow de A à Z (100 % automatique) sur un dataset.
    Renvoie (et écrit dans <job>/result.json) le résultat."""
    data_dir, job_dir = Path(data_dir).resolve(), Path(job_dir).resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = STEPS_DIR / "manifest.json"
    if not manifest_path.exists() or NOTEBOOK.stat().st_mtime > manifest_path.stat().st_mtime:
        extract()                                     # notebook modifié (ou étapes absentes) : ré-extraction automatique
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cells = [m for m in manifest if not m["skip"] and m["step"] in STEP_NAMES]
    progress = Progress(job_dir, cells)

    os.environ["BIFLOW_DATA_DIR"] = str(data_dir)     # lu par la cellule 1.1
    os.environ.setdefault("BIFLOW_CACHE_DIR", str(Path("biflow_cache").resolve()))   # cache partagé entre les runs
    cwd = os.getcwd()
    os.chdir(job_dir)                                 # ./biflow_runs est propre à ce job
    llm = llm or OllamaLLM()
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")      # Windows : deux copies d'OpenMP (torch + numpy) ne plantent plus
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if not _embeddings_usable():                      # bibliothèques absentes ou instables : on ne les charge jamais
        sys.modules["sentence_transformers"] = None   # → ImportError propre : le notebook passe en recherche lexicale
    module = types.ModuleType("biflow_pipeline")     # un vrai module : nécessaire aux dataclasses du notebook
    sys.modules["biflow_pipeline"] = module
    ns = module.__dict__
    ns.update({"display": _display, "_BIFLOW_LLM": llm})
    if hasattr(llm, "bind"):                          # LLM de test : accès à l'état du pipeline
        llm.bind(ns)

    run_info = {"parts": [], "bi": None, "xai": None}
    prep_error = bi_error = xai_error = None
    delivered = bi_started = xai_started = False
    t_part = time.perf_counter()

    def close_part(name: str, status: str, error: str | None) -> None:
        nonlocal t_part
        run_info["parts"].append({"node": name, "status": status, "error": error,
                                  "seconds": round(time.perf_counter() - t_part, 1)})
        t_part = time.perf_counter()

    def deliver() -> None:
        nonlocal delivered
        delivered = True
        progress.update(step="Delivery", cell="Delivering the star schema and the cleaned data")
        print("\n### Delivery: star schema and cleaned data", flush=True)
        ns["DATA_PREP_RESULT"] = _deliver(ns, prep_error)
        r = ns["DATA_PREP_RESULT"]
        ns["AUDIT"].log("orchestrator", "data_preparation_finished", {"status": r["status"], "error": r.get("error")},
                        level="INFO" if r["status"] == "success" else "WARNING")
        close_part("data_preparation", r["status"], r.get("error"))

    def finish_bi() -> None:
        """Le moteur joue le rôle de run_bi_insight() : même rapport, même trace dans l'audit."""
        status = "failed" if bi_error else "success"
        history = [{"node": BI_NODES[s], "status": "running", "seconds": None, "summary": None}
                   for s in sorted(BI_NODES) if ns.get(BI_CHECKPOINTS[s][0])]
        ns["BI_RESULT"] = {"status": status, "error": bi_error, "history": history, "stages": {}, "outputs": {}}
        ns["AUDIT"].log("orchestrator", "bi_insight_finished", {"status": status, "error": bi_error},
                        level="INFO" if status == "success" else "WARNING")
        close_part("bi_insight", status, bi_error)
        run_info["bi"] = {"status": status, "error": bi_error}

    def start_xai() -> None:
        nonlocal xai_started
        xai_started = True
        prep = (ns.get("DATA_PREP_RESULT") or {}).get("status", "failed")
        status = prep if prep != "success" else ("failed" if bi_error else "success")
        error = (ns.get("DATA_PREP_RESULT") or {}).get("error") if prep != "success" else bi_error
        ns["BIFLOW_RESULT"] = {"status": status, "error": error, "history": [
            {"node": p["node"], "status": p["status"], "seconds": p["seconds"], "summary": None} for p in run_info["parts"]]}
        ns["AUDIT"].log("orchestrator", "biflow_finished", {"status": status, "error": error},
                        level="INFO" if status == "success" else "WARNING")

    result, ran, failed_steps = None, set(), set()
    try:
        if hasattr(llm, "check"):
            llm.check()                               # échoue tout de suite si Ollama n'est pas prêt
        for i, cell in enumerate(cells):
            step = cell["step"]
            if i and step != cells[i - 1]["step"]:    # une étape vient de se terminer
                done_step = cells[i - 1]["step"]
                if done_step in BI_CHECKPOINTS and bi_started and not bi_error and not ns.get(BI_CHECKPOINTS[done_step][0]):
                    bi_error = _failed_checks(ns, done_step)          # comme run_bi_insight() : arrêt propre de la partie 2
                    failed_steps.add(done_step)
                    print(f"!! Part 2 stopped: {bi_error}", flush=True)
                if done_step in ran and done_step not in failed_steps:   # seule une étape exécutée sans erreur compte
                    _publish_partial(ns, job_dir, llm, done_step, run_info)
                    progress.update(completed_step=done_step)
            if step not in PREP_STEPS and not delivered:
                deliver()
                if ns["DATA_PREP_RESULT"]["status"] == "success":
                    _publish_partial(ns, job_dir, llm, 6, run_info)
                    progress.update(completed_step=6)
            prep_ok = (ns.get("DATA_PREP_RESULT") or {}).get("status") == "success"
            if step in PREP_STEPS and prep_error:
                continue                              # arrêt « métier » de la partie 1 : on va directement à la livraison
            if step in BI_STEPS:
                if not prep_ok or bi_error:
                    continue                          # partie 2 seulement après une préparation réussie
                bi_started = True
            if step in XAI_STEPS:
                if bi_started and run_info["bi"] is None:
                    finish_bi()
                if not xai_started:
                    start_xai()
                if xai_error:
                    continue
            ran.add(step)
            progress.at_cell(i, cell)
            print(f"\n### [{i + 1}/{len(cells)}] {_title(cell)}", flush=True)
            source = LLM_CELL if cell["kind"] == "llm" else (STEPS_DIR / cell["file"]).read_text(encoding="utf-8")
            try:
                _exec_cell(source, ns, cell["file"])
            except LLMUnavailable as exc:
                failed_steps.add(step)
                if step in PREP_STEPS:
                    raise
                if step in BI_STEPS:
                    bi_error = f"{_title(cell)}: {exc}"
                else:
                    xai_error = f"{_title(cell)}: {exc}"
                print(f"!! {exc}", flush=True)
            except Exception as exc:
                where = f"{_title(cell)}: {type(exc).__name__}: {exc}"
                failed_steps.add(step)
                if step in (4, 5):
                    prep_error = where                # arrêt « métier » (qualité bloquante…)
                elif step in BI_STEPS:
                    bi_error = where
                elif step in XAI_STEPS:
                    xai_error = where
                else:
                    raise
                traceback.print_exc()
                print(f"!! Stopped at {where}", flush=True)
        if not delivered:
            deliver()
        if bi_started and run_info["bi"] is None:
            finish_bi()
        last = cells[-1]["step"] if cells else 12
        if last in BI_CHECKPOINTS and bi_started and not bi_error and not ns.get(BI_CHECKPOINTS[last][0]):
            bi_error = _failed_checks(ns, last)
        run_info["xai"] = {"status": "failed" if xai_error or not xai_started else "success", "error": xai_error}
        if xai_started:
            close_part("explainability", run_info["xai"]["status"], xai_error)
        result = _export(ns, job_dir, llm, run_info)
        if result["status"] == "success" and bi_error:
            result.update(status="failed", error=f"BI analysis interrupted: {bi_error}")
    except Exception as exc:
        traceback.print_exc()
        result = {"status": "failed", "error": f"{type(exc).__name__}: {exc}",
                  "llm": {"model": getattr(llm, "model_id", None), "calls": getattr(llm, "calls", 0)}}
    finally:
        os.chdir(cwd)
    result["data_dir"] = str(data_dir)
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    for obj in gc.get_objects():                      # ferme les entrepôts (sous Windows, un fichier ouvert est verrouillé)
        if type(obj).__name__ in ("Warehouse", "BIWarehouse", "BIWorkspace"):
            try:
                obj.con.close()
            except Exception:
                pass
    if result.get("output_dir"):                      # zip de tous les livrables, prêt à télécharger
        try:
            shutil.make_archive(str(job_dir / "biflow_outputs"), "zip", result["run_dir"])
        except OSError as exc:
            print(f"Could not zip the deliverables: {exc}")
    (job_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    progress.update(status=result["status"], done=len(cells), percent=100, error=result.get("error"),
                    completed_step=13 if result["status"] == "success" else progress.state["completed_step"])
    return result
