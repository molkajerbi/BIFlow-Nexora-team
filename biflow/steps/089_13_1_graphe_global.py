class BIFlowState(TypedDict, total=False):
    run_id: str
    status: str                 # running · failed · blocked · success
    error: str | None
    stopped_at: str | None      # partie où le pipeline s'est arrêté
    history: list
    parts: dict                 # résumé de chaque partie
    outputs: dict


def biflow_node(name: str):
    """Même enveloppe que les sous-orchestrateurs (chronométrée, tracée, sans plantage), annotée avec l'état global."""
    def decorator(fn):
        wrapper = graph_node(name)(fn)
        wrapper.__annotations__ = {"state": BIFlowState, "return": dict}
        return wrapper
    return decorator


def part_update(state: BIFlowState, name: str, summary: dict, status: str = "running", error: str | None = None) -> dict:
    update = {"status": status, "parts": {**state.get("parts", {}), name: summary}, "summary": summary}
    if status in STOP_STATES:
        update.update(error=error, stopped_at=name)
    return update


@biflow_node("preflight")
def node_global_preflight(state: BIFlowState) -> dict:
    checks = checkpoint_raw_integrity()
    raw_ok = bool(checks["contenu_inchangé"].all())
    llm_ok = "LLM" in globals() and hasattr(LLM, "chat")
    summary = {"dataset": str(CONFIG.data_dir.name), "tables": len(RAW.names), "données_brutes_intactes": raw_ok,
               "llm": globals().get("LLM_MODEL_ID", "?") if llm_ok else "absent"}
    if not raw_ok or not llm_ok:
        return part_update(state, "preflight", summary, "failed",
                           "données brutes modifiées" if not raw_ok else "LLM non chargé (étape 3.1)")
    return part_update(state, "preflight", summary)


@biflow_node("data_preparation")
def node_global_data_prep(state: BIFlowState) -> dict:
    global DATA_PREP_RESULT
    DATA_PREP_RESULT = run_data_preparation()
    r = DATA_PREP_RESULT
    summary = {"statut": r["status"], "constats": (r.get("profiler") or {}).get("findings"),
               "corrections": (r.get("quality") or {}).get("corrections_applied"),
               "qualité": (r.get("quality") or {}).get("quality_status"), "tables_étoile": (r.get("etl") or {}).get("tables_built")}
    if r["status"] != "success":
        return part_update(state, "data_preparation", summary, r["status"] if r["status"] in STOP_STATES else "failed", r.get("error"))
    return part_update(state, "data_preparation", summary)


@biflow_node("bi_insight")
def node_global_bi(state: BIFlowState) -> dict:
    global BI_RESULT
    BI_RESULT = run_bi_insight(show=False)
    stages = BI_RESULT.get("stages", {})
    summary = {"statut": BI_RESULT["status"], "secteur": ", ".join(BI_SECTORS or ["générique"]) if "BI_SECTORS" in globals() else None,
               "kpi": (stages.get("kpi_agent") or {}).get("kpi_au_catalogue"), "insights": (stages.get("analyst_agent") or {}).get("insights"),
               "dashboard": (stages.get("dashboard_agent") or {}).get("fichier")}
    if BI_RESULT["status"] != "success":
        return part_update(state, "bi_insight", summary, "failed", BI_RESULT.get("error"))
    return part_update(state, "bi_insight", summary)


@biflow_node("explainability")
def node_global_xai(state: BIFlowState) -> dict:
    """Toujours exécuté : explique un run réussi… ou pourquoi il s'est arrêté."""
    global DECISIONS, METHODS, XAI_INDEX
    DECISIONS = build_ledger()
    METHODS = method_records()
    XAI_INDEX = XAIIndex(LEDGER + METHODS)
    (XAI_DIR / "decision_ledger.json").write_text(canonical_json(LEDGER), encoding="utf-8")
    summary = {"décisions": len(LEDGER), "règles": len(METHODS), "blocs_absents": len(LEDGER_ERRORS)}
    return {"parts": {**state.get("parts", {}), "explainability": summary}, "summary": summary}   # le statut est conservé


def deliverables() -> dict:
    """Manifeste de tous les livrables du run (chemins existants seulement)."""
    g = globals()
    paths = {
        "entrepôt (modèle en étoile)": (DATA_PREP_RESULT.get("outputs") or {}).get("warehouse") if g.get("DATA_PREP_RESULT") else None,
        "contrat de données": RUN_DIR / "data_contract.json", "journal d'audit": RUN_DIR / "audit_log.jsonl",
        "échanges avec le LLM": g.get("LLM_LOG"), "catalogue de KPI": g.get("BI_DIR") and BI_DIR / "kpi_catalog.json",
        "analyse et insights": g.get("BI_DIR") and BI_DIR / "analysis.json", "dashboard": g.get("DASHBOARD_PATH"),
        "registre des décisions (XAI)": XAI_DIR / "decision_ledger.json", "règles du système (XAI)": XAI_DIR / "rules.json",
    }
    return {k: str(Path(v).resolve()) for k, v in paths.items() if v and Path(v).exists()}


def biflow_report(state: BIFlowState, status: str) -> dict:
    outputs = deliverables()
    report = {"run_id": RUN_ID, "status": status, "error": state.get("error"), "stopped_at": state.get("stopped_at"),
              "engine": GRAPH_ENGINE, "finished_at": utc_now(), "parts": state.get("parts", {}), "history": state.get("history", []),
              "outputs": outputs, "hashes": {"catalog": globals().get("CATALOG_SHA256"), "analysis": globals().get("ANALYSIS_SHA256"),
                                             "dashboard": globals().get("DASHBOARD_SHA256")}}
    (RUN_DIR / "biflow_run_report.json").write_text(canonical_json(report), encoding="utf-8")
    return outputs


@biflow_node("deliver")
def node_global_deliver(state: BIFlowState) -> dict:
    outputs = biflow_report({**state, "status": "success"}, "success")
    return {"status": "success", "outputs": outputs, "summary": {"livrables": len(outputs)}}


@biflow_node("stop_report")
def node_global_stop(state: BIFlowState) -> dict:
    outputs = biflow_report(state, state.get("status", "failed"))
    return {"outputs": outputs, "summary": {"arrêt": state.get("stopped_at"), "raison": state.get("error")}}


def continue_or_explain(state: BIFlowState) -> str:
    """Après une partie : continuer, ou aller directement à l'explicabilité (qui expliquera l'arrêt)."""
    return "explain" if state.get("status") in STOP_STATES else "continue"


def after_xai(state: BIFlowState) -> str:
    return "stop" if state.get("status") in STOP_STATES else "deliver"


g_builder = StateGraph(BIFlowState)
for name, fn in [("preflight", node_global_preflight), ("data_preparation", node_global_data_prep), ("bi_insight", node_global_bi),
                 ("explainability", node_global_xai), ("deliver", node_global_deliver), ("stop_report", node_global_stop)]:
    g_builder.add_node(name, fn)
g_builder.add_edge(START, "preflight")
g_builder.add_conditional_edges("preflight", continue_or_explain, {"continue": "data_preparation", "explain": "explainability"})
g_builder.add_conditional_edges("data_preparation", continue_or_explain, {"continue": "bi_insight", "explain": "explainability"})
g_builder.add_conditional_edges("bi_insight", continue_or_explain, {"continue": "explainability", "explain": "explainability"})
g_builder.add_conditional_edges("explainability", after_xai, {"deliver": "deliver", "stop": "stop_report"})
g_builder.add_edge("deliver", END)
g_builder.add_edge("stop_report", END)
BIFLOW_GRAPH = g_builder.compile()

BIFLOW_MERMAID = BIFLOW_GRAPH.get_graph().draw_mermaid()
(RUN_DIR / "biflow_global_graph.mmd").write_text(BIFLOW_MERMAID, encoding="utf-8")
print(f"Graphe global prêt (moteur : {GRAPH_ENGINE}) · enregistré dans biflow_global_graph.mmd")
try:
    raise ImportError("aperçu du graphe désactivé en déploiement")
    display(Image(BIFLOW_GRAPH.get_graph().draw_mermaid_png()))
except Exception:
    print(BIFLOW_MERMAID)
