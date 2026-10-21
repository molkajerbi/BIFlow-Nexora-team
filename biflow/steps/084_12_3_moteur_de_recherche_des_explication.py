from sklearn.feature_extraction.text import TfidfVectorizer as _Tfidf

STEP_WORDS = {
    1: ["contract", "ingestion", "file", "format", "type", "grain", "role", "identifier"],
    2: ["profil", "relation", "link", "join", "tool"],
    3: ["domain", "business", "diagnos", "finding", "interpret", "profiler", "severity"],
    4: ["quality", "clean", "correction", "correct", "imput", "median", "missing", "duplicate", "rule", "score",
        "cap", "extreme", "replace", "fill"],
    5: ["etl", "star", "dimension", "warehouse", "schema", "derived indicator", "delay"],
    6: ["orchestr", "preparation", "langgraph"],
    7: ["sector", "bridge", "knowledge", "rag", "rebuil", "computable"],
    8: ["kpi", "indicator", "catalog", "binding", "formula", "sql", "column chosen", "chosen column", "dropped"],
    9: ["signal", "trend", "anomal", "level shift", "insight", "segment", "investigation", "analys", "alert", "increase", "decrease"],
    10: ["dashboard", "tile", "chart", "layout", "main figure"],
    11: ["orchestr", "langgraph", "run_bi_insight"],
    13: ["orchestr", "full pipeline", "from a to z"],
}


def norm(text) -> str:
    """lower case, no accents, punctuation and underscores replaced by spaces: 'Late_Delivery Rate' -> 'late delivery rate'."""
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", t).strip() + " "


def record_text(r: dict) -> str:
    ev = " ".join(f"{k} {v}" for k, v in list(r["evidence"].items())[:8])
    return f"{r['subject']} {r['object']} {r['decision']} {r['why'][:600]} {ev} {' '.join(r['terms'])}"


class XAIIndex:
    """Index of the decisions and rules: cited names + step + meaning (7.5 embeddings if available)."""

    def __init__(self, records: list[dict]):
        self.records = records
        self.texts = [record_text(r) for r in records]
        self.tfidf = _Tfidf(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit([norm(t) for t in self.texts])
        self.lex = self.tfidf.transform([norm(t) for t in self.texts])
        self.model = getattr(globals().get("SEARCH"), "model", None)
        self.emb = None
        if self.model is not None:
            self.emb = self.model.encode(["passage: " + t[:500] for t in self.texts], normalize_embeddings=True, batch_size=64)
        self.terms = {}
        for i, r in enumerate(records):
            for t in r["terms"] + [r["id"]]:
                k = norm(t)
                if len(k.strip()) >= 3:
                    self.terms.setdefault(k, set()).add(i)

    def entity_scores(self, q: str) -> np.ndarray:
        """Cited names: a long and precise name counts more than a short word; a name included in a longer name also cited
        ("orders" in "fact_orders") counts only once."""
        nq, s = norm(q), np.zeros(len(self.records))
        hits = [k for k in self.terms if k in nq]
        hits = [k for k in hits if not any(k != h and k in h for h in hits)]
        for k in hits:
            w = min(len(k.strip()) / 12, 1.5)
            for i in self.terms[k]:
                s[i] += w * (0.5 if self.records[i]["subject"] == "method" else 1.0)   # un mot-clé de règle compte moins qu'un nom
        return s

    def semantic(self, q: str) -> np.ndarray:
        lex = (self.tfidf.transform([norm(q)]) @ self.lex.T).toarray()[0]
        if self.emb is None:
            return lex
        e = self.model.encode(["query: " + q], normalize_embeddings=True) @ self.emb.T
        return 0.75 * np.clip((e[0] - 0.7) / 0.3, 0, 1) + 0.25 * lex

    def search(self, q: str, k: int = 3, previous: list[str] | None = None) -> list[tuple[dict, float]]:
        ent, sem = self.entity_scores(q), self.semantic(q)
        nq = norm(q)
        steps = {s for s, words in STEP_WORDS.items() if any(" " + w in nq for w in words)}
        step_bonus = np.array([0.3 if r["step"] in steps else 0.0 for r in self.records])
        follow = np.zeros(len(self.records))
        follow_up = re.match(r"^ (and|but|so|then|why not|what if) ", nq) or \
            re.search(r" (that|this|it|this decision|this choice|this one|that one|this correction|this kpi|this insight) ", nq)
        if previous and ent.max() == 0 and follow_up:
            follow = np.array([1.0 if r["id"] in previous else 0.0 for r in self.records])
        method_penalty = np.array([0.15 if r["subject"] == "method" and not re.search(r" how | in general | rule", nq) else 0.0
                                   for r in self.records])
        named = np.array([0.3 if len(norm(r["object"]).strip()) >= 4 and norm(r["object"]) in nq else 0.0 for r in self.records])
        score = sem + ent + step_bonus + follow + named - method_penalty      # l'objet exact de la décision est cité
        order = np.argsort(-score, kind="mergesort")[:k]
        best = score[order[0]] if len(order) else 0
        return [(self.records[i], float(score[i])) for i in order if score[i] > 0 and score[i] >= 0.6 * best]


def xai_search(question: str, k: int = 3, previous: list[str] | None = None) -> list[tuple[dict, float]]:
    """Most relevant decisions (or rules) for a question."""
    return XAI_INDEX.search(question, k, previous)


XAI_INDEX = XAIIndex(LEDGER + METHODS)
print(f"Explanation index: {len(XAI_INDEX.records)} entries ({len(LEDGER)} decisions, {len(METHODS)} rules) · "
      f"{len(XAI_INDEX.terms)} recognised names · meaning: {'embeddings + lexical' if XAI_INDEX.emb is not None else 'lexical'}")
example_q = f"Why {LEDGER[-1]['object']}?" if LEDGER else "How does the cleaning work?"
pd.DataFrame([{"question": example_q, "decision found": r["id"], "object": r["object"], "score": round(s, 3)}
              for r, s in xai_search(example_q)])
