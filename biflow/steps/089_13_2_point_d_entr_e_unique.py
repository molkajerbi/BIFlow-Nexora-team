def run_biflow() -> BIFlowState:
    """Single entry point of BIFlow: preparation → BI & insights → explainability. 100% automatic."""
    t0 = time.perf_counter()
    AUDIT.log("orchestrator", "biflow_started", {"engine": GRAPH_ENGINE, "dataset": str(CONFIG.data_dir)})
    final = BIFLOW_GRAPH.invoke({"run_id": RUN_ID, "status": "running", "error": None, "stopped_at": None,
                                 "history": [], "parts": {}, "outputs": {}})
    final["seconds"] = round(time.perf_counter() - t0, 1)
    AUDIT.log("orchestrator", "biflow_finished", {"status": final["status"], "stopped_at": final.get("stopped_at"),
                                                  "error": final.get("error"), "seconds": final["seconds"]},
              level="INFO" if final["status"] == "success" else "WARNING")
    print(f"BIFlow · status: {final['status']} · duration: {final['seconds']:.0f} s"
          + (f" · stopped at “{final['stopped_at']}”: {final['error']}" if final.get("stopped_at") else ""))
    return final


def biflow_history(result: BIFlowState) -> pd.DataFrame:
    return pd.DataFrame([{"node": h["node"], "status": h["status"], "seconds": h["seconds"],
                          "summary": ", ".join(f"{k}={v}" for k, v in (h["summary"] or {}).items())} for h in result["history"]])


print("run_biflow() ready")
