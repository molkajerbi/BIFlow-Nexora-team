PIPELINE = ["preflight", "profiler_agent", "quality_agent", "human_review", "apply_corrections", "etl_agent", "finalize"]
NODES = {"preflight": node_preflight, "profiler_agent": node_profiler, "quality_agent": node_quality,
         "human_review": node_human_review, "apply_corrections": node_apply, "etl_agent": node_etl,
         "finalize": node_finalize, "report": node_report}

builder = StateGraph(DataPrepState)
for name, fn in NODES.items():
    builder.add_node(name, fn)
builder.add_edge(START, PIPELINE[0])
for current, nxt in zip(PIPELINE, PIPELINE[1:]):             # après chaque nœud : continuer ou s'arrêter
    builder.add_conditional_edges(current, route, {"continue": nxt, "stop": "report"})
builder.add_edge("finalize", END)
builder.add_edge("report", END)
DATA_PREP_GRAPH = builder.compile()

MERMAID = DATA_PREP_GRAPH.get_graph().draw_mermaid()
(RUN_DIR / "data_preparation_graph.mmd").write_text(MERMAID, encoding="utf-8")
try:                                                        # image du graphe (nécessite Internet)
    from IPython.display import Image
    display(Image(DATA_PREP_GRAPH.get_graph().draw_mermaid_png()))
except Exception:
    print(MERMAID)
