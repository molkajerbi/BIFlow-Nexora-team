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
        text, source, errors = rules, "règles", []
        if mode != "règles" and records and intent not in ("résumé", "liste"):
            llm_text, errors = llm_explanation(question, records, self.history)
            if llm_text:
                text, source = llm_text + "\n\n---\n*Détail vérifiable :*\n\n" + render_record(records[0], intent, full=False), \
                    "LLM (vérifié)"
        turn = {"ts": utc_now(), "question": question, "intention": intent, "sources": [r["id"] for r in records],
                "mode": source, "refus_llm": errors, "réponse": text, "seconds": round(time.perf_counter() - t0, 1)}
        self.history.append(turn)
        with (XAI_DIR / "chat.jsonl").open("a", encoding="utf-8") as f:
            f.write(canonical_json(turn) + "\n")
        AUDIT.log("xai_agent", "question_answered", {k: turn[k] for k in ("question", "intention", "sources", "mode", "refus_llm")})
        if show:
            header = f"> **Question :** {question}\n\n"
            footer = f"\n\n<sub>intention : {intent} · réponse : {source} · sources : {', '.join(turn['sources']) or '—'}</sub>"
            try:
                from IPython.display import Markdown
                display(Markdown(header + text + footer))
            except ImportError:
                print(header + text + footer)
        return turn


XAI_CHAT = XAIChat()
ask = XAI_CHAT.ask


def demo_questions() -> list[str]:
    """Questions de démonstration tirées du registre : elles fonctionnent sur n'importe quel dataset."""
    pick = lambda pred: next((r for r in LEDGER if pred(r)), None)
    qs = ["Résume le travail de BIFlow de A à Z."]
    r = pick(lambda r: r["sujet"] == "correction" and "impute" in r["décision"]) or pick(lambda r: r["sujet"] == "correction")
    if r:
        qs += [f"Pourquoi la {r['objet']} a-t-elle été appliquée ?", "Et qu'est-ce qui aurait changé cette décision ?"]
    r = pick(lambda r: r["sujet"] == "secteur métier")
    if r:
        qs.append("Pourquoi ce secteur métier a-t-il été choisi ?")
    r = pick(lambda r: r["sujet"] == "KPI" and r["décidé_par"].startswith("LLM")) or pick(lambda r: r["sujet"] == "KPI")
    if r:
        qs.append(f"Pourquoi le KPI « {r['objet']} » utilise-t-il cette colonne ?")
    r = pick(lambda r: r["sujet"].startswith("fait (") and r["contrefactuel"])
    if r:
        qs.append(f"Le {r['objet']} est-il fiable ?")
    r = pick(lambda r: r["sujet"] == "insight" and r["décidé_par"].startswith("LLM")) or pick(lambda r: r["sujet"] == "insight")
    if r:
        qs.append(f"D'où vient l'{r['objet']} ?")
    qs += ["Quelles décisions le superviseur a-t-il refusées au LLM ?", "Comment BIFlow remplit-il les valeurs manquantes ?"]
    return qs


DEMO_QUESTIONS = demo_questions()
for demo_q in DEMO_QUESTIONS:
    ask(demo_q, mode="règles", show=False)


def chat_widget():
    """Zone de chat interactive (ipywidgets). Sans ipywidgets : utiliser ask("…")."""
    try:
        import ipywidgets as w
        from IPython.display import Markdown
    except ImportError:
        print("Zone de chat indisponible ici : posez vos questions avec ask(\"…\")")
        return None
    box = w.Text(placeholder="Posez une question : pourquoi… ? comment… ? et si… ?", layout=w.Layout(width="78%"))
    send, out = w.Button(description="Demander", button_style="primary"), w.Output()

    def on_send(_=None):
        q = box.value.strip()
        if q:
            box.value = ""
            with out:
                ask(q)
    send.on_click(on_send)
    display(w.VBox([w.HTML("<b>Chat XAI · BIFlow</b> — chaque réponse cite ses sources (D…) et ses preuves"),
                    w.HBox([box, send]), out]))
    return box


XAI_WIDGET = chat_widget()
