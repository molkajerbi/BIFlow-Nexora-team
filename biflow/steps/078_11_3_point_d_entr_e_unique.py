def run_bi_insight(start_from: str | int = "bridge_agent", show: bool = True) -> BIInsightState:
    """Single entry point of the BI & Insight Agent (called by the global BI Orchestrator after run_data_preparation)."""
    if start_from not in STAGE_ALIASES:
        raise ValueError(f"unknown start_from: {start_from!r} (expected: {', '.join(STAGE_NAMES)}, 7…10)")
    start = STAGE_ALIASES[start_from]
    t0 = time.perf_counter()
    AUDIT.log("orchestrator", "bi_insight_started", {"engine": GRAPH_ENGINE, "start_from": start})
    final = BI_INSIGHT_GRAPH.invoke({"run_id": RUN_ID, "start_from": start, "status": "running", "error": None,
                                     "history": [], "stages": {}, "outputs": {}})
    AUDIT.log("orchestrator", "bi_insight_finished", {"status": final["status"], "error": final.get("error"),
                                                      "seconds": round(time.perf_counter() - t0, 1)},
              level="INFO" if final["status"] == "success" else "WARNING")
    if show:
        print(f"Part 2 · status: {final['status']} · duration: {time.perf_counter() - t0:.0f} s"
              + (f" · {final['error']}" if final.get("error") else ""))
    return final


def bi_history_table(result: BIInsightState) -> pd.DataFrame:
    return pd.DataFrame([{"node": h["node"], "status": h["status"], "seconds": h["seconds"],
                          "LLM calls": (h["summary"] or {}).get("llm_calls", ""),
                          "summary": ", ".join(f"{k}={v}" for k, v in (h["summary"] or {}).items() if k not in {"llm_calls", "journal"})}
                         for h in result["history"]])


print("run_bi_insight() ready")
