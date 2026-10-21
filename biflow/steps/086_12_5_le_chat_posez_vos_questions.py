class XAIChat:
    def __init__(self):
        self.history: list[dict] = []

    def ask(self, question: str, mode: str = "auto", show: bool = True) -> dict:
        t0 = time.perf_counter()
        intent = intent_of(question)
        previous = self.history[-1]["sources"] if self.history else None
        hits = xai_search(question, k=3, previous=previous)
        rules = rule_answer(question, hits, intent)
        records = [r for r, _ in hits]
        text, source, errors = rules, "rules", []
        if mode not in ("rules", "règles") and records and intent not in ("summary", "list"):
            llm_text, errors = llm_explanation(question, records, self.history)
            if llm_text:
                text, source = llm_text + "\n\n---\n*Verifiable detail:*\n\n" + render_record(records[0], intent, full=False), \
                    "LLM (verified)"
        turn = {"ts": utc_now(), "question": question, "intent": intent, "sources": [r["id"] for r in records],
                "mode": source, "llm_rejections": errors, "answer": text, "seconds": round(time.perf_counter() - t0, 1)}
        self.history.append(turn)
        with (XAI_DIR / "chat.jsonl").open("a", encoding="utf-8") as f:
            f.write(canonical_json(turn) + "\n")
        AUDIT.log("xai_agent", "question_answered", {k: turn[k] for k in ("question", "intent", "sources", "mode", "llm_rejections")})
        if show:
            header = f"> **Question:** {question}\n\n"
            footer = f"\n\n<sub>intent: {intent} · answer: {source} · sources: {', '.join(turn['sources']) or '—'}</sub>"
            try:
                from IPython.display import Markdown
                display(Markdown(header + text + footer))
            except ImportError:
                print(header + text + footer)
        return turn


XAI_CHAT = XAIChat()
ask = XAI_CHAT.ask


def demo_questions() -> list[str]:
    """Demonstration questions taken from the ledger: they work on any dataset."""
    pick = lambda pred: next((r for r in LEDGER if pred(r)), None)
    qs = ["Summarise BIFlow's work from A to Z."]
    r = pick(lambda r: r["subject"] == "correction" and "impute" in r["decision"]) or pick(lambda r: r["subject"] == "correction")
    if r:
        qs += [f"Why was {r['object']} applied?", "And what would have changed this decision?"]
    r = pick(lambda r: r["subject"] == "business sector")
    if r:
        qs.append("Why was this business sector chosen?")
    r = pick(lambda r: r["subject"] == "KPI" and r["decided_by"].startswith("LLM")) or pick(lambda r: r["subject"] == "KPI")
    if r:
        qs.append(f"Why does the KPI “{r['object']}” use this column?")
    r = pick(lambda r: r["subject"].startswith("fact (") and r["counterfactual"])
    if r:
        qs.append(f"Is {r['object']} reliable?")
    r = pick(lambda r: r["subject"] == "insight" and r["decided_by"].startswith("LLM")) or pick(lambda r: r["subject"] == "insight")
    if r:
        qs.append(f"Where does {r['object']} come from?")
    qs += ["Which decisions did the supervisor reject from the LLM?", "How does BIFlow fill in missing values?"]
    return qs


DEMO_QUESTIONS = demo_questions()
for demo_q in DEMO_QUESTIONS:
    ask(demo_q, mode="rules", show=False)


def chat_widget():
    """Interactive chat box (ipywidgets). Without ipywidgets: use ask("…")."""
    try:
        import ipywidgets as w
        from IPython.display import Markdown
    except ImportError:
        print("Chat box unavailable here: ask your questions with ask(\"…\")")
        return None
    box = w.Text(placeholder="Ask a question: why…? how…? what if…?", layout=w.Layout(width="78%"))
    send, out = w.Button(description="Ask", button_style="primary"), w.Output()

    def on_send(_=None):
        q = box.value.strip()
        if q:
            box.value = ""
            with out:
                ask(q)
    send.on_click(on_send)
    display(w.VBox([w.HTML("<b>XAI chat · BIFlow</b> — every answer cites its sources (D…) and its evidence"),
                    w.HBox([box, send]), out]))
    return box


XAI_WIDGET = chat_widget()
