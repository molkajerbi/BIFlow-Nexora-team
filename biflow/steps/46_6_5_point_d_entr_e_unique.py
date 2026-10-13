def run_data_preparation(human_decision: dict | None = None, autonomy: str | None = None) -> DataPrepState:
    """Point d'entrée unique de la Data Preparation Agent (appelé plus tard par le BI Orchestrator global)."""
    autonomy = autonomy or CONFIG.autonomy
    AUDIT.log("orchestrator", "data_preparation_started",
              {"engine": GRAPH_ENGINE, "autonomy": autonomy, "human_decision_provided": bool(human_decision)})
    final = DATA_PREP_GRAPH.invoke({"run_id": RUN_ID, "human_decision": human_decision, "autonomy": autonomy,
                                    "status": "running", "error": None, "history": []})
    AUDIT.log("orchestrator", "data_preparation_finished", {"status": final["status"], "error": final.get("error")},
              level="INFO" if final["status"] == "success" else "WARNING")
    return final
