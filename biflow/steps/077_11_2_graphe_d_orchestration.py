class BIInsightState(TypedDict, total=False):
    run_id: str
    start_from: str
    status: str                 # running · failed · blocked · success
    error: str | None
    history: list
    stages: dict                # résumé de chaque étape exécutée
    outputs: dict


BI_LOG_DIR = RUN_DIR / "bi_insight_logs"
BI_LOG_DIR.mkdir(exist_ok=True)


def bi_graph_node(name: str):
    """Part 1 graph_node wrapper, annotated with the part 2 state. LangGraph reads the annotation of a node's
    parameter to know which keys to pass to it: with the part 1 annotation, "start_from" would be filtered out."""
    def decorator(fn):
        wrapper = graph_node(name)(fn)
        wrapper.__annotations__ = {"state": BIInsightState, "return": dict}
        return wrapper
    return decorator


def bi_route(state: BIInsightState) -> str:
    return "stop" if state.get("status") in STOP_STATES else "continue"


def llm_calls_so_far() -> int:
    return sum(1 for _ in LLM_LOG.open(encoding="utf-8")) if LLM_LOG.exists() else 0


STAGE_SUMMARIES = {
    "bridge_agent": lambda: {"domain": BI_INPUT["domain"], "sectors": BI_SECTORS or ["generic"],
                             "reference_kpis": len(KPI_REFERENCES)},
    "kpi_agent": lambda: {"kpis_in_catalog": len(KPI_CATALOG), "validated": int((KPI_CATALOG["status"] == "validated").sum()),
                          "catalog_sha256": CATALOG_SHA256[:12]},
    "analyst_agent": lambda: {"series": len(SERIES), "facts": len(FACTS), "insights": len(INSIGHTS),
                              "LLM_insights": sum(i["source"] == "LLM" for i in INSIGHTS), "analysis_sha256": ANALYSIS_SHA256[:12]},
    "dashboard_agent": lambda: {"layout": layout_source, "tiles": len(LAYOUT["tiles"]) + 1,
                                "charts": len(LAYOUT["charts"]), "breakdowns": len(LAYOUT["breakdowns"]),
                                "file": DASHBOARD_PATH.name},
}


def run_stage(stage: dict) -> dict:
    """Replays the cells of a step; returns the state update (success, or failure with the reason)."""
    sources = stage_sources(stage)
    g = globals()
    g[stage["checkpoint"]] = False                        # une étape n'est validée que si son point de contrôle est relu
    calls0, log_path = llm_calls_so_far(), BI_LOG_DIR / f"{stage['step']:02d}_{stage['node']}.log"
    buffer, had_display, old_display = io.StringIO(), "display" in g, g.get("display")
    g["display"] = lambda *objs, **kw: print(*[o if isinstance(o, str) else repr(o)[:2000] for o in objs], file=buffer)
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            for i, src in enumerate(sources, 1):
                print(f"\n######## cell {stage['step']}.{i}")
                exec(compile(src, f"<{stage['node']} {stage['step']}.{i}>", "exec"), g)
    finally:
        if had_display:
            g["display"] = old_display
        else:
            g.pop("display", None)
        log_path.write_text(buffer.getvalue(), encoding="utf-8")
    metrics = {"llm_calls": llm_calls_so_far() - calls0, "journal": log_path.name}
    if not g.get(stage["checkpoint"]):
        failed = [k for k, v in g.get(stage["checks"], {}).items() if not v]
        return {"status": "failed", "error": f"checkpoint of step {stage['step']} failed: {', '.join(failed) or '?'}",
                "summary": metrics}
    metrics.update(STAGE_SUMMARIES[stage["node"]]())
    return {"status": "running", "stages": metrics, "summary": metrics}


def make_stage_node(stage: dict):
    @bi_graph_node(stage["node"])
    def node(state: BIInsightState) -> dict:
        update = run_stage(stage)
        if "stages" in update:
            update["stages"] = {**state.get("stages", {}), stage["node"]: update["stages"]}
        return update
    return node


@bi_graph_node("plan")
def node_plan(state: BIInsightState) -> dict:
    start = state["start_from"]
    k = STAGE_NAMES.index(start)
    for s in STAGES[:k]:                                  # reprise : les étapes amont doivent être validées dans la session
        if not globals().get(s["checkpoint"]):
            return {"status": "blocked", "error": f"cannot resume at \"{start}\": step {s['step']} is not validated "
                                                  f"in this session (run again from {s['node']})"}
    for s in STAGES[k:]:
        stage_sources(s)                                  # échoue tôt si une cellule n'a jamais été exécutée
    reused = {s["node"]: {"reused": "result already validated in the session"} for s in STAGES[:k]}
    return {"status": "running", "stages": reused,
            "summary": {"start": start, "reused_steps": list(reused), "steps_to_run": STAGE_NAMES[k:]}}


def bi_run_report(state: BIInsightState, status: str) -> dict:
    g = globals()
    outputs = {name: str(path) for name, path in [
        ("dashboard", g.get("DASHBOARD_PATH")), ("catalog", g.get("BI_DIR") and BI_DIR / "kpi_catalog.json"),
        ("analysis", g.get("BI_DIR") and BI_DIR / "analysis.json"), ("insights", g.get("BI_DIR") and BI_DIR / "insights.json")]
        if path and Path(path).exists()}
    report = {"run_id": RUN_ID, "status": status, "error": state.get("error"), "start_from": state.get("start_from"),
              "engine": GRAPH_ENGINE, "finished_at": utc_now(), "stages": state.get("stages", {}),
              "history": state.get("history", []), "outputs": outputs,
              "hashes": {"handoff": g.get("HANDOFF_SHA256"), "catalog": g.get("CATALOG_SHA256"),
                         "analysis": g.get("ANALYSIS_SHA256"), "dashboard": g.get("DASHBOARD_SHA256")}}
    (RUN_DIR / "bi_insight_run.json").write_text(canonical_json(report), encoding="utf-8")
    return outputs


@bi_graph_node("finalize")
def node_bi_finalize(state: BIInsightState) -> dict:
    outputs = bi_run_report({**state, "status": "success"}, "success")
    return {"status": "success", "outputs": outputs, "summary": {"files": list(outputs)}}


@bi_graph_node("report")
def node_bi_report(state: BIInsightState) -> dict:
    outputs = bi_run_report(state, state.get("status", "failed"))
    return {"outputs": outputs, "summary": {"stop": state.get("status"), "reason": state.get("error")}}


def plan_route(state: BIInsightState) -> str:
    return "stop" if state.get("status") in STOP_STATES else state["start_from"]


bi_builder = StateGraph(BIInsightState)
bi_builder.add_node("plan", node_plan)
for s in STAGES:
    bi_builder.add_node(s["node"], make_stage_node(s))
bi_builder.add_node("finalize", node_bi_finalize)
bi_builder.add_node("report", node_bi_report)
bi_builder.add_edge(START, "plan")
bi_builder.add_conditional_edges("plan", plan_route, {**{n: n for n in STAGE_NAMES}, "stop": "report"})
for current, nxt in zip(STAGE_NAMES, STAGE_NAMES[1:] + ["finalize"]):
    bi_builder.add_conditional_edges(current, bi_route, {"continue": nxt, "stop": "report"})
bi_builder.add_edge("finalize", END)
bi_builder.add_edge("report", END)
BI_INSIGHT_GRAPH = bi_builder.compile()

BI_MERMAID = BI_INSIGHT_GRAPH.get_graph().draw_mermaid()
(RUN_DIR / "bi_insight_graph.mmd").write_text(BI_MERMAID, encoding="utf-8")
print(f"Part 2 graph ready (engine: {GRAPH_ENGINE}) · {len(STAGES)} agents · saved to bi_insight_graph.mmd")
try:
    raise ImportError("aperçu du graphe désactivé en déploiement")
    display(Image(BI_INSIGHT_GRAPH.get_graph().draw_mermaid_png()))
except Exception:
    print(BI_MERMAID)
