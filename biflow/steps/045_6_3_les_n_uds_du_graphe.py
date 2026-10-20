@graph_node("preflight")
def node_preflight(state: DataPrepState) -> dict:
    checks = checkpoint_raw_integrity()
    if not checks["contenu_inchangé"].all():
        return {"status": "failed", "error": "les données brutes ont été modifiées"}
    return {"status": "running", "summary": {"tables": len(RAW.names), "rows": int(sum(len(RAW._tables[t]) for t in RAW.names))}}


@graph_node("profiler_agent")
def node_profiler(state: DataPrepState) -> dict:
    global SCREENING, REQUIRED, AGENT_RUN, FINDINGS, INTERPRETATIONS, PROFILING_REPORT
    TOOL_RESULTS.clear()
    SCREENING = screening()
    REQUIRED = ({("analyze_missingness", t) for t, s in SCREENING["tables"].items() if s["columns_with_missing"]}
                | {("detect_anomalies", t) for t, s in SCREENING["tables"].items() if s["numeric_measures"]})
    AGENT_RUN = run_profiler_agent()
    FINDINGS = build_findings()
    INTERPRETATIONS, _ = interpret_findings(FINDINGS)
    PROFILING_REPORT = FINDINGS.merge(INTERPRETATIONS.drop(columns="attempt"), on="id", how="left")
    metrics = {"investigations": len(REQUIRED), "by_agent": len(AGENT_RUN["done"]), "fallback": len(AGENT_RUN["fallback"]),
               "findings": len(PROFILING_REPORT), "interpreted_by_llm": int((PROFILING_REPORT["source"] == "LLM").sum())}
    return {"status": "running", "profiler": metrics, "summary": metrics}


@graph_node("quality_agent")
def node_quality(state: DataPrepState) -> dict:
    global SILVER, TYPE_REPORT, TYPE_FAILURES, RULES, ISSUES_BEFORE, RULES_BEFORE, SCORES_BEFORE
    global CANDIDATES, AUTO_FLAGGED, Q_RUN, CLEANING_PLAN, OTHER_TREATMENTS, PLAN_SHA256
    SILVER, reports, failures = {}, [], []
    for t in DATA_CONTRACT:                                   # repart toujours des données brutes
        SILVER[t], rep, fail = convert_types(t)
        reports += rep
        failures.append(fail)
    TYPE_REPORT, TYPE_FAILURES = pd.DataFrame(reports), pd.concat(failures, ignore_index=True)
    RULES = build_rules()
    ISSUES_BEFORE, RULES_BEFORE = run_rules(SILVER, RULES)
    SCORES_BEFORE = dq_scores(SILVER, RULES_BEFORE, ISSUES_BEFORE)
    CANDIDATES = build_candidates()
    AUTO_FLAGGED = RULES_BEFORE[(RULES_BEFORE["violations"] > 0)
                                & ~RULES_BEFORE["rule"].isin({c["rule"] for c in CANDIDATES})][["rule", "table", "severity", "violations"]]
    Q_RUN = run_quality_agent()
    proposed = [c for c in CANDIDATES if c["status"] == "proposé"]
    CLEANING_PLAN = pd.DataFrame([{"id": f"C{i:02d}", "correction": c["correction"], "table": c["table"], "colonne": c["column"],
                                   "candidat": c["id"], "règle": c["rule"], "findings": c["profiler_findings"],
                                   "effet_simulé": c["simulation"]["rules_changed"], "justification": c["agent_reason"],
                                   "décidé_par": c["decided_by"]} for i, c in enumerate(proposed, 1)],
                                 columns=["id", "correction", "table", "colonne", "candidat", "règle", "findings",
                                          "effet_simulé", "justification", "décidé_par"])
    OTHER_TREATMENTS = pd.DataFrame([{"élément": c["id"], "table": c["table"], "traitement": "écarté par l'agent : reste signalé",
                                      "justification": c["agent_reason"]} for c in CANDIDATES if c["status"] == "écarté"],
                                    columns=["élément", "table", "traitement", "justification"])
    PLAN_SHA256 = sha256_text(canonical_json({"plan": CLEANING_PLAN.to_dict(orient="records")}))
    metrics = {"rules_violated": int((RULES_BEFORE["violations"] > 0).sum()), "candidates": len(CANDIDATES),
               "decided_by_agent": Q_RUN["decided_by_agent"], "proposed": CLEANING_PLAN["id"].tolist(),
               "dismissed": [c["id"] for c in CANDIDATES if c["status"] == "écarté"], "plan_sha256": PLAN_SHA256}
    return {"status": "running", "quality": metrics, "summary": metrics}


@graph_node("risk_review")
def node_risk_review(state: DataPrepState) -> dict:
    """Validation automatique selon le risque (aucune attente humaine)."""
    global APPROVED, REVIEW
    REVIEW = review_plan()
    APPROVED = REVIEW["approved"]
    return {"status": "running", "summary": {"mode": REVIEW["mode"], "approved": APPROVED, "set_aside": REVIEW["set_aside"]}}


@graph_node("apply_corrections")
def node_apply(state: DataPrepState) -> dict:
    global CHANGE_LOG, ROW_LOG, EXECUTION, CHANGES, ROW_CHANGES, ISSUES_AFTER, RULES_AFTER, SCORES_AFTER, STATUS
    CHANGE_LOG, ROW_LOG = [], []
    EXECUTION = pd.DataFrame([apply_correction(p.id, p.correction, p.table, p.colonne)
                              for p in plan_in_order() if p.id in APPROVED],
                             columns=["id", "correction", "table", "column", "rows_before", "rows_after", "effect"])
    CHANGES = pd.concat(CHANGE_LOG, ignore_index=True) if CHANGE_LOG else pd.DataFrame()
    ROW_CHANGES = pd.concat(ROW_LOG, ignore_index=True) if ROW_LOG else pd.DataFrame()
    ISSUES_AFTER, RULES_AFTER = run_rules(SILVER, RULES)
    SCORES_AFTER = dq_scores(SILVER, RULES_AFTER, ISSUES_AFTER)
    flags = ISSUES_AFTER.groupby(["table", "_source_row_id"])["rule"].agg(lambda r: "|".join(sorted(set(r))))
    for t in SILVER:
        table_flags = flags.xs(t, level="table") if t in flags.index.get_level_values("table") else pd.Series(dtype="string")
        SILVER[t]["_dq_flags"] = SILVER[t]["_source_row_id"].map(table_flags).astype("string")
    mark_estimated_values()                              # lignes dont une valeur a été estimée (4.1 bis)
    blocking_left = int(RULES_AFTER.query("severity == 'blocking'")["violations"].sum())
    STATUS = "blocked" if blocking_left else ("ready_with_warnings" if RULES_AFTER["violations"].sum() else "ready")
    metrics = {"corrections_applied": len(EXECUTION), "cells_changed": len(CHANGES), "rows_changed": len(ROW_CHANGES),
               "quality_status": STATUS, "blocking_left": blocking_left,
               "scores": {d: [float(SCORES_BEFORE[d]), float(SCORES_AFTER[d])] for d in SCORES_BEFORE.index}}
    update = {"quality": {**state["quality"], **metrics}, "summary": metrics}
    update["status"] = "blocked" if STATUS == "blocked" else "running"
    if STATUS == "blocked":
        update["error"] = f"{blocking_left} violation(s) bloquante(s) : ETL interdit"
    return update


@graph_node("etl_agent")
def node_etl(state: DataPrepState) -> dict:
    global STAGING, DERIVED, WH, ETL_TEMPLATES, ETL_STATUS, ETL_RESULTS, ETL_RUN
    out_dir = RUN_DIR / "data_preparation_output"
    out_dir.mkdir(exist_ok=True)
    WH = Warehouse(out_dir / f"biflow_star.{'duckdb' if SQL_ENGINE == 'duckdb' else 'sqlite'}")
    STAGING, DERIVED = build_staging()                       # staging générique + indicateurs de temps
    for name, df in STAGING.items():
        WH.load(name, df)
    ETL_TEMPLATES = design_star_schema()                     # modèle en étoile conçu à partir des données nettoyées
    ETL_STATUS = {name: "à construire" for name in ETL_TEMPLATES}
    ETL_RESULTS = {}
    ETL_RUN = run_etl_agent()
    ok = all(s == "testée" for s in ETL_STATUS.values())
    metrics = {"tables_built": sum(s == "testée" for s in ETL_STATUS.values()), "tables_expected": len(ETL_TEMPLATES),
               "built_by_agent": ETL_RUN["built_by_agent"], "failed": [n for n, s in ETL_STATUS.items() if s == "échec"]}
    update = {"etl": metrics, "summary": metrics, "status": "running" if ok else "failed"}
    if not ok:
        update["error"] = f"tests ETL en échec : {metrics['failed'] or 'construction incomplète'}"
    return update


@graph_node("finalize")
def node_finalize(state: DataPrepState) -> dict:
    out_dir = RUN_DIR / "data_preparation_output"
    star = {name: WH.query(f"SELECT * FROM {name}") for name in ETL_TEMPLATES}
    for name, df in star.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)
    PROFILING_REPORT.to_csv(out_dir / "profiling_report.csv", index=False)
    RULES_AFTER.to_csv(out_dir / "quality_rules_after.csv", index=False)
    CHANGES.to_csv(out_dir / "quality_cell_changes.csv", index=False)
    ROW_CHANGES.to_csv(out_dir / "quality_row_changes.csv", index=False)
    raw_ok = bool(checkpoint_raw_integrity()["contenu_inchangé"].all())
    chain_ok, chain_msg = AUDIT.verify()
    outputs = {"directory": str(out_dir), "warehouse": str(WH.path), "tables": {n: len(d) for n, d in star.items()},
               "raw_unchanged": raw_ok, "audit_chain": chain_msg}
    (out_dir / "data_preparation_manifest.json").write_text(canonical_json(
        {"run_id": RUN_ID, "profiler": state["profiler"], "quality": state["quality"], "etl": state["etl"], "outputs": outputs}),
        encoding="utf-8")
    ok = raw_ok and chain_ok
    return {"status": "success" if ok else "failed", "outputs": outputs, "summary": outputs,
            "error": None if ok else "contrôle final en échec"}


@graph_node("report")
def node_report(state: DataPrepState) -> dict:
    """Nœud d'arrêt : explique pourquoi le pipeline s'est interrompu."""
    reasons = {"blocked": "qualité bloquante : l'ETL n'a pas été lancé",
               "failed": "erreur pendant l'exécution"}
    return {"summary": {"status": state.get("status"), "reason": reasons.get(state.get("status")), "error": state.get("error")}}


print("7 nœuds définis : preflight, profiler_agent, quality_agent, risk_review, apply_corrections, etl_agent, finalize (+ report)")
