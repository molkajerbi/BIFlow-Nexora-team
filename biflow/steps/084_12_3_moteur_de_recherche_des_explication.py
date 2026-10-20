from sklearn.feature_extraction.text import TfidfVectorizer as _Tfidf

STEP_WORDS = {
    1: ["contrat", "ingestion", "fichier", "format", "type", "grain", "role", "identifiant"],
    2: ["profil", "relation", "lien", "jointure", "outil"],
    3: ["domaine", "metier", "diagnostic", "constat", "interpretation", "profiler", "gravite"],
    4: ["qualite", "nettoyage", "nettoye", "correction", "corrige", "imput", "mediane", "manquant", "doublon", "regle", "score",
        "plafon", "extreme", "remplace", "rempli"],
    5: ["etl", "etoile", "dimension", "entrepot", "modele", "indicateur derive", "delai"],
    6: ["orchestr", "preparation", "langgraph"],
    7: ["secteur", "pont", "connaissance", "rag", "reconstitu", "calculable"],
    8: ["kpi", "indicateur", "catalogue", "liaison", "formule", "sql", "colonne choisie", "ecarte"],
    9: ["signal", "tendance", "anomalie", "rupture", "insight", "segment", "investigation", "analyse", "alerte", "hausse", "baisse"],
    10: ["dashboard", "tableau de bord", "tuile", "graphique", "mise en page", "chiffre principal"],
    11: ["orchestr", "langgraph", "run_bi_insight"],
    13: ["orchestr", "pipeline complet", "de a a z"],
}


def norm(text) -> str:
    """minuscules, sans accents, ponctuation et tirets bas remplacés par des espaces : 'Taux_de Retard' -> 'taux de retard'."""
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", t).strip() + " "


def record_text(r: dict) -> str:
    ev = " ".join(f"{k} {v}" for k, v in list(r["preuves"].items())[:8])
    return f"{r['sujet']} {r['objet']} {r['décision']} {r['pourquoi'][:600]} {ev} {' '.join(r['termes'])}"


class XAIIndex:
    """Index des décisions et des règles : noms cités + étape + sens (embeddings du 7.5 si disponibles)."""

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
            for t in r["termes"] + [r["id"]]:
                k = norm(t)
                if len(k.strip()) >= 3:
                    self.terms.setdefault(k, set()).add(i)

    def entity_scores(self, q: str) -> np.ndarray:
        """Noms cités : un nom long et précis compte plus qu'un mot court ; un nom inclus dans un nom plus long cité aussi
        (« orders » dans « fact_orders ») ne compte qu'une fois."""
        nq, s = norm(q), np.zeros(len(self.records))
        hits = [k for k in self.terms if k in nq]
        hits = [k for k in hits if not any(k != h and k in h for h in hits)]
        for k in hits:
            w = min(len(k.strip()) / 12, 1.5)
            for i in self.terms[k]:
                s[i] += w * (0.5 if self.records[i]["sujet"] == "méthode" else 1.0)   # un mot-clé de règle compte moins qu'un nom
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
        step_bonus = np.array([0.3 if r["étape"] in steps else 0.0 for r in self.records])
        follow = np.zeros(len(self.records))
        follow_up = re.match(r"^ (et|mais|alors|donc|pourquoi pas|et si) ", nq) or \
            re.search(r" (ca|cela|cette decision|ce choix|celle ci|celui ci|cette correction|ce kpi|cet insight) ", nq)
        if previous and ent.max() == 0 and follow_up:
            follow = np.array([1.0 if r["id"] in previous else 0.0 for r in self.records])
        method_penalty = np.array([0.15 if r["sujet"] == "méthode" and not re.search(r" comment | en general | regle", nq) else 0.0
                                   for r in self.records])
        named = np.array([0.3 if len(norm(r["objet"]).strip()) >= 4 and norm(r["objet"]) in nq else 0.0 for r in self.records])
        score = sem + ent + step_bonus + follow + named - method_penalty      # l'objet exact de la décision est cité
        order = np.argsort(-score, kind="mergesort")[:k]
        best = score[order[0]] if len(order) else 0
        return [(self.records[i], float(score[i])) for i in order if score[i] > 0 and score[i] >= 0.6 * best]


def xai_search(question: str, k: int = 3, previous: list[str] | None = None) -> list[tuple[dict, float]]:
    """Décisions (ou règles) les plus pertinentes pour une question."""
    return XAI_INDEX.search(question, k, previous)


XAI_INDEX = XAIIndex(LEDGER + METHODS)
print(f"Index des explications : {len(XAI_INDEX.records)} entrées ({len(LEDGER)} décisions, {len(METHODS)} règles) · "
      f"{len(XAI_INDEX.terms)} noms reconnus · sens : {'embeddings + lexical' if XAI_INDEX.emb is not None else 'lexical'}")
example_q = f"Pourquoi {LEDGER[-1]['objet']} ?" if LEDGER else "Comment fonctionne le nettoyage ?"
pd.DataFrame([{"question": example_q, "décision trouvée": r["id"], "objet": r["objet"], "score": round(s, 3)}
              for r, s in xai_search(example_q)])
