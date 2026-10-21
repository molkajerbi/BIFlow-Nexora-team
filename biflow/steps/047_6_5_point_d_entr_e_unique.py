def run_data_preparation() -> DataPrepState:
    """Single entry point of the Data Preparation Agent (called later by the global BI Orchestrator).
    100% automatic: no parameter, no human validation."""
    AUDIT.log("orchestrator", "data_preparation_started", {"engine": GRAPH_ENGINE, "mode": "automatic"})
    final = DATA_PREP_GRAPH.invoke({"run_id": RUN_ID, "status": "running", "error": None, "history": []})
    AUDIT.log("orchestrator", "data_preparation_finished", {"status": final["status"], "error": final.get("error")},
              level="INFO" if final["status"] == "success" else "WARNING")
    return final
