try:
    from langgraph.graph import StateGraph, START, END
    GRAPH_ENGINE = "langgraph"
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "langgraph"], check=False)
    try:
        from langgraph.graph import StateGraph, START, END
        GRAPH_ENGINE = "langgraph"
    except ImportError:
        GRAPH_ENGINE = "mini"

if GRAPH_ENGINE == "mini":
    START, END = "__start__", "__end__"

    class _CompiledMiniGraph:
        """Exécuteur minimal reproduisant le sous-ensemble de l'API LangGraph utilisé ici."""

        def __init__(self, nodes, edges, conditional):
            self.nodes, self.edges, self.conditional = nodes, edges, conditional

        def invoke(self, state: dict) -> dict:
            state, current = dict(state), self.edges[START]
            while current != END:
                state.update(self.nodes[current](state))
                if current in self.conditional:
                    route, mapping = self.conditional[current]
                    current = mapping[route(state)]
                else:
                    current = self.edges[current]
            return state

        def get_graph(self):
            return self

        def draw_mermaid(self) -> str:
            lines = ["graph TD"]
            for a, b in self.edges.items():
                lines.append(f"    {a} --> {b}")
            for a, (_, mapping) in self.conditional.items():
                lines += [f"    {a} -. {label} .-> {b}" for label, b in mapping.items()]
            return "\n".join(lines)

    class StateGraph:
        def __init__(self, state_schema):
            self.nodes, self.edges, self.conditional = {}, {}, {}

        def add_node(self, name, fn):
            self.nodes[name] = fn

        def add_edge(self, a, b):
            self.edges[a] = b

        def add_conditional_edges(self, a, route, mapping):
            self.conditional[a] = (route, mapping)

        def compile(self):
            return _CompiledMiniGraph(self.nodes, self.edges, self.conditional)

print(f"Moteur d'orchestration : {GRAPH_ENGINE}")
