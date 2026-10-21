from sklearn.feature_extraction.text import TfidfVectorizer

EMBED_MODEL_ID = os.environ.get("BIFLOW_EMBED_MODEL", "intfloat/multilingual-e5-small")


class SemanticSearch:
    """Meaning similarity between texts: multilingual embeddings + character n-grams (lexical fallback without Internet)."""

    def __init__(self, corpus: list[str]):
        self.tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit(corpus)
        self.model, self.mode = None, "lexical"
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(EMBED_MODEL_ID, device="cpu")   # petit modèle : le GPU reste au LLM
            self.mode = "embeddings + lexical"
        except Exception as exc:                          # pas d'Internet ou bibliothèque absente
            self.error = f"{type(exc).__name__}: {str(exc)[:120]}"

    def _embed(self, texts: list[str], kind: str) -> np.ndarray:
        prefix = "query: " if kind == "query" else "passage: "     # convention des modèles e5
        return self.model.encode([prefix + t for t in texts], normalize_embeddings=True, batch_size=64)

    def similarity(self, queries: list[str], passages: list[str]) -> np.ndarray:
        lex = (self.tfidf.transform(queries) @ self.tfidf.transform(passages).T).toarray()
        if self.model is None:
            return lex
        emb = self._embed(queries, "query") @ self._embed(passages, "passage").T
        emb = np.clip((emb - 0.7) / 0.3, 0, 1)            # les cosinus e5 se concentrent entre 0,7 et 1
        return 0.75 * emb + 0.25 * lex


def card_text(c: dict) -> str:
    return f"{c['name']}. {c['definition']} {c['synonyms']}"


def slot_text(c: dict, slot: str) -> str:
    s = c["slots"][slot]
    return f"{s['hint']}. {' / '.join(ROLES[r]['label'] for r in s['roles'])}"


def column_text(r) -> str:
    desc = BI_INPUT["tables"][r.table]["description"]
    values = ", ".join(list((r.top_values or {}).keys())[:5])
    return f"{words(r.column)} ({desc}){' · values: ' + values if values else ''}"


def dataset_text() -> str:
    parts = [BI_INPUT["domain"]]
    for t, s in BI_INPUT["tables"].items():
        cols = [words(c) for c, m in s["columns"].items() if m["semantic"] not in {"technical", "key", "calendar"}]
        parts.append(f"{words(re.sub(r'^(dim|fact)_', '', t))}: {s['description']} · {', '.join(cols[:25])}")
    return " | ".join(parts)


COLUMN_TEXTS = [column_text(r) for r in BI_INVENTORY.itertuples()]
SLOT_KEYS = [(c["id"], s) for c in KPI_KB for s in c["slots"]]
SLOT_TEXTS = [slot_text(next(c for c in KPI_KB if c["id"] == cid), s) for cid, s in SLOT_KEYS]
t0 = time.perf_counter()
SEARCH = SemanticSearch([*COLUMN_TEXTS, *SLOT_TEXTS, *map(card_text, KPI_KB), *SECTORS.values(), dataset_text()])
SLOT_COLUMN_SIM = SEARCH.similarity(SLOT_TEXTS, COLUMN_TEXTS) if SLOT_TEXTS and COLUMN_TEXTS else np.zeros((len(SLOT_TEXTS), 0))
AUDIT.log("bi_knowledge", "search_engine_ready", {"mode": SEARCH.mode, "model": EMBED_MODEL_ID if SEARCH.model else None,
                                                  "fallback_reason": getattr(SEARCH, "error", None),
                                                  "seconds": round(time.perf_counter() - t0, 1)},
          level="INFO" if SEARCH.model else "WARNING")
print(f"Search engine: {SEARCH.mode}" + (f" (fallback: {SEARCH.error})" if SEARCH.model is None else f" · {EMBED_MODEL_ID}"))
