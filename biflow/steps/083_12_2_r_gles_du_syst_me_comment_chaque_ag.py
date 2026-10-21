METHOD_CARDS = [   # (étape, titre, fonctions qui décident, seuils, mots-clés)
    (1, "Reading the files and data contract", ["sniff", "infer_type", "infer_relationships", "infer_roles", "validate_contract"],
     [], ["column type", "format", "grain", "identifier", "fact table", "dimension", "link", "relationship"]),
    (2, "Profiler tools: quality measurements", ["cramers_v", "screening"], [],
     ["missing values", "anomalies", "duplicates", "isolation forest", "iqr", "cramer"]),
    (3, "Domain and interpretation of the findings by the LLM", ["understand_domain", "validate_decision", "is_grounded"],
     ["BLOCKING_ALLOWED"], ["domain", "business", "interpretation", "severity", "finding"]),
    (4, "Quality rules and score", ["run_rules", "learned_business_rules", "learned_cross_table_rules", "dq_scores"], [],
     ["quality rule", "quality score", "quality dimension", "dama"]),
    (4, "Missing, impossible and extreme values", ["missing_method", "protected_columns", "category_fill", "fences",
                                                   "outlier_policy"], ["MAX_IMPUTE_PCT", "MAX_OUTLIER_PCT", "OUTLIER_K"],
     ["missing values", "imputation", "median", "fill", "extreme value", "cap", "impossible value"]),
    (4, "Corrections: test, decide, validate, apply", ["simulate_correction", "run_quality_agent", "allowed_decisions",
                                                       "assess_risk", "review_plan", "plan_in_order", "apply_correction"],
     ["MAX_ROWS_REMOVED_PCT"], ["correction", "sandbox", "risk", "cleaning", "duplicates"]),
    (5, "Star schema and time indicators", ["derive_time_indicators", "design_star_schema", "extracted_dimensions",
                                            "test_table"], [], ["star schema", "etl", "delay", "lateness", "calendar"]),
    (6, "Preparation orchestration", ["graph_node", "run_data_preparation"], [], ["orchestrator", "langgraph", "node"]),
    (7, "Business sector and reference KPIs (RAG)", ["sector_supported"], ["MIN_SECTOR_KPIS", "MIN_SECTOR_COVERAGE",
                                                                           "MIN_SECTOR_COLUMNS"],
     ["sector", "rag", "semantic search", "knowledge base", "embeddings"]),
    (8, "Binding, calculation and tests of the KPIs", ["auto_params", "validate_binding", "run_sql", "check_bounds", "name_mismatch"], [],
     ["kpi", "binding", "formula", "sql", "double calculation", "bounds"]),
    (9, "Statistical signals, segments and insights", ["analyse_series", "mann_kendall", "theil_sen", "robust_z", "dimensions",
                                                       "twin_axis", "check_insight", "repair_citations"], ["WINDOW"],
     ["trend", "anomaly", "level shift", "recent change", "year over year", "signal", "segment", "insight", "mann kendall"]),
    (10, "Dashboard layout", ["validate_layout"], ["MAX_TILES", "MAX_CHARTS", "MAX_SEGMENTS"],
     ["dashboard", "layout", "tile", "chart"]),
    (11, "Part 2 orchestration", ["run_stage", "run_bi_insight"], [], ["orchestrator", "resume"]),
    (12, "Explainability (this agent)", ["xai_search", "rule_answer", "verify_explanation"], [], ["explanation", "xai", "chat"]),
]


def method_records() -> list[dict]:
    out = []
    for i, (step, title, fns, consts, keywords) in enumerate(METHOD_CARDS, 1):
        rules = [f"{fn}: {doc(fn)}" for fn in fns if doc(fn)]
        values = {c: xai_num(globals()[c]) if not isinstance(globals()[c], (set, list, tuple)) else ", ".join(map(str, globals()[c]))
                  for c in consts if c in globals()}
        out.append({"id": f"M{i:02d}", "step": step, "agent": XAI_STEPS.get(step, ""), "subject": "method", "object": title,
                    "decision": f"how it works: {title.lower()}", "why": " ".join(rules), "evidence": values,
                    "decided_by": "code rule", "counterfactual": None, "rejections": [], "terms": [title, *keywords], "audit": []})
    return out


METHODS = method_records()        # complété en 12.4 (les fonctions de l'agent XAI y sont définies)
pd.DataFrame([{"id": m["id"], "step": m["step"], "rules of": m["object"], "documented functions": m["why"].count(": "),
               "thresholds": ", ".join(f"{k} = {v}" for k, v in m["evidence"].items()) or "—"} for m in METHODS])
