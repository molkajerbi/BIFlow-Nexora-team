def run_data_preparation() -> DataPrepState:
    """Point d'entrée unique de la Data Preparation Agent (appelé plus tard par le BI Orchestrator global).
    100 % automatique : aucun paramètre, aucune validation humaine."""
    AUDIT.log("orchestrator", "data_preparation_started", {"engine": GRAPH_ENGINE, "mode": "automatique"})
    final = DATA_PREP_GRAPH.invoke({"run_id": RUN_ID, "status": "running", "error": None, "history": []})
    AUDIT.log("orchestrator", "data_preparation_finished", {"status": final["status"], "error": final.get("error")},
              level="INFO" if final["status"] == "success" else "WARNING")
    return final

