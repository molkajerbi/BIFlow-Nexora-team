def run_biflow() -> BIFlowState:
    """Point d'entrée unique de BIFlow : préparation → BI & insights → explicabilité. 100 % automatique."""
    t0 = time.perf_counter()
    AUDIT.log("orchestrator", "biflow_started", {"engine": GRAPH_ENGINE, "dataset": str(CONFIG.data_dir)})
    final = BIFLOW_GRAPH.invoke({"run_id": RUN_ID, "status": "running", "error": None, "stopped_at": None,
                                 "history": [], "parts": {}, "outputs": {}})
    final["seconds"] = round(time.perf_counter() - t0, 1)
    AUDIT.log("orchestrator", "biflow_finished", {"status": final["status"], "stopped_at": final.get("stopped_at"),
                                                  "error": final.get("error"), "seconds": final["seconds"]},
              level="INFO" if final["status"] == "success" else "WARNING")
    print(f"BIFlow · statut : {final['status']} · durée : {final['seconds']:.0f} s"
          + (f" · arrêt à « {final['stopped_at']} » : {final['error']}" if final.get("stopped_at") else ""))
    return final


def biflow_history(result: BIFlowState) -> pd.DataFrame:
    return pd.DataFrame([{"nœud": h["node"], "statut": h["status"], "secondes": h["seconds"],
                          "résumé": ", ".join(f"{k}={v}" for k, v in (h["summary"] or {}).items())} for h in result["history"]])


print("run_biflow() prêt")
