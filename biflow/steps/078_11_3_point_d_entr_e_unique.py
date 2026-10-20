def run_bi_insight(start_from: str | int = "bridge_agent", show: bool = True) -> BIInsightState:
    """Point d'entrée unique de la BI & Insight Agent (appelé par le BI Orchestrator global après run_data_preparation)."""
    if start_from not in STAGE_ALIASES:
        raise ValueError(f"start_from inconnu : {start_from!r} (attendu : {', '.join(STAGE_NAMES)}, 7…10)")
    start = STAGE_ALIASES[start_from]
    t0 = time.perf_counter()
    AUDIT.log("orchestrator", "bi_insight_started", {"engine": GRAPH_ENGINE, "start_from": start})
    final = BI_INSIGHT_GRAPH.invoke({"run_id": RUN_ID, "start_from": start, "status": "running", "error": None,
                                     "history": [], "stages": {}, "outputs": {}})
    AUDIT.log("orchestrator", "bi_insight_finished", {"status": final["status"], "error": final.get("error"),
                                                      "seconds": round(time.perf_counter() - t0, 1)},
              level="INFO" if final["status"] == "success" else "WARNING")
    if show:
        print(f"Partie 2 · statut : {final['status']} · durée : {time.perf_counter() - t0:.0f} s"
              + (f" · {final['error']}" if final.get("error") else ""))
    return final


def bi_history_table(result: BIInsightState) -> pd.DataFrame:
    return pd.DataFrame([{"nœud": h["node"], "statut": h["status"], "secondes": h["seconds"],
                          "appels LLM": (h["summary"] or {}).get("llm_calls", ""),
                          "résumé": ", ".join(f"{k}={v}" for k, v in (h["summary"] or {}).items() if k not in {"llm_calls", "journal"})}
                         for h in result["history"]])


print("run_bi_insight() prêt")
