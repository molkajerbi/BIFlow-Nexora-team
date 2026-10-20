import math

BI_ENGINE = getattr(BI_WH, "engine", None) or globals().get("SQL_ENGINE", "duckdb")
BI_DIR = RUN_DIR / "bi"
BI_DIR.mkdir(exist_ok=True)
KB_BY_ID = {c["id"]: c for c in KPI_KB}
INV = BI_INVENTORY.set_index(["table", "column"])


def lit(v) -> str:
    """Littéral SQL texte (apostrophes doublées)."""
    return "'" + str(v).replace("'", "''") + "'"


def reference_date() -> str | None:
    """Date d'où partent les délais calculés par la partie 1 (« A_to_B_days » → A) ; sinon la date la mieux renseignée."""
    starts = [re.match(r"(.+)_to_.+_days$", c).group(1) for s in BI_INPUT["tables"].values() for c, m in s["columns"].items()
              if m.get("derived") == "duration" and re.match(r"(.+)_to_.+_days$", c)]
    if starts:
        return pd.Series(starts).mode()[0]
    dates = BI_INVENTORY[BI_INVENTORY["semantic"] == "datetime"].assign(
        rebuilt=lambda d: d["origin"].str.contains("date reconstituée"))   # date que le dataset avait éclatée (ex. date d'arrivée)
    dates = dates.sort_values(["rebuilt", "non_null_pct", "column"], ascending=[False, False, True])
    return dates["column"].iloc[0] if len(dates) else None


REF_DATE = reference_date()


def time_key(table: str) -> str | None:
    """Clé de date (AAAAMMJJ) utilisée pour les séries mensuelles d'une table de base."""
    cols = BI_INPUT["tables"][table]["columns"]
    if REF_DATE and f"{REF_DATE}_date_key" in cols:
        return f"{REF_DATE}_date_key"
    keys = [c for c in cols if c.endswith("_date_key")]
    return keys[0] if keys else None


class KPIQuery:
    """Compile une fiche liée à des colonnes : clause FROM avec jointures, expressions SQL des mesures et des conditions."""

    def __init__(self, card: dict, binding: dict):
        self.card, self.b = card, binding
        self.fact = binding["fact"]
        self.alias = {self.fact: "b"}
        self.joins = []
        fks = BI_INPUT["tables"][self.fact]["fks"]
        for t in dict.fromkeys(t for t, _ in binding["slots"].values()):
            if t == self.fact:
                continue
            col, key = next((c, k) for c, (tg, k) in fks.items() if tg == t)
            self.alias[t] = f"j{len(self.joins)}"
            self.joins.append(f"LEFT JOIN {qi(t)} {self.alias[t]} ON {self.alias[t]}.{qi(key)} = b.{qi(col)}")

    @property
    def from_sql(self) -> str:
        return f"FROM {qi(self.fact)} b " + " ".join(self.joins)

    def col(self, slot: str) -> str:
        t, c = self.b["slots"][slot]
        return f"{self.alias[t]}.{qi(c)}"

    def is_numeric(self, slot: str) -> bool:
        return INV.loc[self.b["slots"][slot], "semantic"] in {"numeric", "integer", "geo"}

    def cond(self, w: dict) -> str:
        p, op = self.b["params"], w["op"]
        if op == "dq_flagged":
            return "b._dq_flags IS NOT NULL" if "_dq_flags" in BI_INPUT["tables"][self.fact]["columns"] else "1 = 0"
        c = self.col(w["slot"])
        if op == "is_true":
            tv = p["true_value"][w["slot"]]
            return f"{c} = {float(tv):g}" if self.is_numeric(w["slot"]) else f"{c} = {lit(tv)}"
        if op == "in_values":
            return f"{c} IN ({', '.join(lit(v) for v in p['values'][w['slot']])})"
        if op == "negative":
            return f"{c} < 0"
        return f"{c} {'<=' if op == 'low_score' else '>'} {float(p['threshold'][w['slot']]):g}"     # low_score / above

    def measure(self, m: dict) -> str:
        if m["agg"] == "add":
            return "(" + " + ".join(f"COALESCE({self.measure(t)}, 0)" for t in m["terms"]) + ")"
        cond = self.cond(m["where"]) if m.get("where") else None
        col = self.col(m["slot"]) if m.get("slot") else None
        if m["agg"] == "count":
            if cond:
                return f"SUM(CASE WHEN {cond}{f' AND {col} IS NOT NULL' if col else ''} THEN 1 ELSE 0 END)"
            return f"COUNT({col})" if col else "COUNT(*)"
        inner = f"CASE WHEN {cond} THEN {col} END" if cond else col
        return {"count_distinct": f"COUNT(DISTINCT {inner})", "sum": f"SUM({inner})", "avg": f"AVG({inner})"}[m["agg"]]

    def scalar(self) -> str:
        f = self.card["formula"]
        if f["kind"] == "value":
            return self.measure(f["measure"])
        return f"1.0 * ({self.measure(f['num'])}) / NULLIF({self.measure(f['den'])}, 0)"     # ratio, rate


def run_sql(card: dict, binding: dict) -> dict:
    """Calcule un KPI dans l'entrepôt. Renvoie la valeur, la requête et, si possible, la série mensuelle."""
    q, f = KPIQuery(card, binding), card["formula"]
    out = {"series": None}
    if f["kind"] in {"value", "ratio", "rate"}:
        out["sql"] = f"SELECT {q.scalar()} AS v {q.from_sql}"
        out["value"] = BI_WH.query(out["sql"])["v"].iloc[0]
        key = time_key(q.fact)
        if key:
            out["series_sql"] = (f"SELECT CAST(b.{qi(key)} / 100 AS INTEGER) AS period, {q.scalar()} AS v {q.from_sql} "
                                 f"WHERE b.{qi(key)} IS NOT NULL GROUP BY 1 ORDER BY 1")
            out["series"] = BI_WH.query(out["series_sql"])
    elif f["kind"] == "growth":
        t, c = binding["slots"][f["date"]]
        key = f"{c}_date_key" if f"{c}_date_key" in BI_INPUT["tables"][t]["columns"] else time_key(q.fact)
        out["sql"] = (f"SELECT CAST({q.alias[t]}.{qi(key)} / 100 AS INTEGER) AS period, {q.measure(f['measure'])} AS v "
                      f"{q.from_sql} WHERE {q.alias[t]}.{qi(key)} IS NOT NULL GROUP BY 1 ORDER BY 1")
        out["series"] = BI_WH.query(out["sql"])
        out["value"], out["growth_detail"] = growth_from_series(out["series"])
    elif f["kind"] == "top_share":
        out["sql"] = f"SELECT {q.col(f['by'])} AS g, {q.measure(f['measure'])} AS v {q.from_sql} GROUP BY 1"
        out["value"] = top_share_value(BI_WH.query(out["sql"]), f["top"])
    elif f["kind"] == "repeat_rate":
        out["sql"] = (f"SELECT {q.col(f['entity'])} AS e, COUNT(DISTINCT {q.col(f['transaction'])}) AS n {q.from_sql} "
                      f"WHERE {q.col(f['entity'])} IS NOT NULL GROUP BY 1")
        g = BI_WH.query(out["sql"])
        out["value"] = float((g["n"] > 1).mean()) if len(g) else None
    return out


def growth_from_series(s: pd.DataFrame) -> tuple[float | None, dict]:
    """Évolution entre les deux dernières périodes COMPLÈTES : les périodes finales anormalement faibles
    (extraction incomplète, moins de 20 % de la médiane des 6 précédentes) sont écartées et signalées."""
    s = s.dropna(subset=["v"]).sort_values("period").reset_index(drop=True)
    dropped = []
    while len(s) >= 3 and s["v"].iloc[-1] < 0.2 * s["v"].iloc[-7:-1].median():
        dropped.append(int(s["period"].iloc[-1]))
        s = s.iloc[:-1]
    if len(s) < 2 or not s["v"].iloc[-2]:
        return None, {"dropped_periods": dropped}
    last, prev = float(s["v"].iloc[-1]), float(s["v"].iloc[-2])
    return (last - prev) / abs(prev), {"last_period": int(s["period"].iloc[-1]), "previous_period": int(s["period"].iloc[-2]),
                                      "last": last, "previous": prev, "dropped_periods": dropped}


def top_share_value(g: pd.DataFrame, top: float) -> float | None:
    g = g.dropna(subset=["g"])
    v = pd.to_numeric(g["v"], errors="coerce").fillna(0).sort_values(ascending=False)
    if v.sum() <= 0:
        return None
    n = int(top) if top >= 1 else max(1, math.ceil(top * len(v)))
    return float(v.iloc[:n].sum() / v.sum())


# ---------------------------------------------------------------- second calcul, indépendant, en pandas
_FRAMES: dict = {}


def kpi_frame(binding: dict) -> pd.DataFrame:
    """Table de base + colonnes jointes, assemblées en pandas (colonnes nommées « table.colonne »)."""
    fact = binding["fact"]
    tables = tuple(sorted({t for t, _ in binding["slots"].values()} - {fact}))
    if (fact, tables) not in _FRAMES:
        df = BI_WH.query(f"SELECT * FROM {qi(fact)}")
        df.columns = [f"{fact}.{c}" for c in df.columns]
        for t in tables:
            col, key = next((c, k) for c, (tg, k) in BI_INPUT["tables"][fact]["fks"].items() if tg == t)
            d = BI_WH.query(f"SELECT * FROM {qi(t)}")
            d.columns = [f"{t}.{c}" for c in d.columns]
            df = df.merge(d, how="left", left_on=f"{fact}.{col}", right_on=f"{t}.{key}", validate="many_to_one")
        _FRAMES[(fact, tables)] = df
    return _FRAMES[(fact, tables)]


def run_pandas(card: dict, binding: dict) -> float | None:
    df, f, p = kpi_frame(binding), card["formula"], binding["params"]
    col = lambda s: df["{}.{}".format(*binding["slots"][s])]
    num = lambda s: pd.to_numeric(col(s), errors="coerce")

    def cond(w):
        op = w["op"]
        if op == "dq_flagged":
            c = f"{binding['fact']}._dq_flags"
            return df[c].notna() if c in df else pd.Series(False, index=df.index)
        s = w["slot"]
        if op == "is_true":
            tv = p["true_value"][s]
            numeric = INV.loc[binding["slots"][s], "semantic"] in {"numeric", "integer", "geo"}
            return (num(s) == float(tv)) if numeric else (col(s).astype("string") == str(tv))
        if op == "in_values":
            return col(s).astype("string").isin([str(v) for v in p["values"][s]])
        if op == "negative":
            return num(s) < 0
        return (num(s) <= float(p["threshold"][s])) if op == "low_score" else (num(s) > float(p["threshold"][s]))

    def measure(m, rows=None):
        rows = pd.Series(True, index=df.index) if rows is None else rows
        if m["agg"] == "add":
            return sum((lambda x: 0.0 if x is None or pd.isna(x) else x)(measure(t, rows)) for t in m["terms"])
        mask = rows & (cond(m["where"]).fillna(False).astype(bool) if m.get("where") else True)
        if m["agg"] == "count":
            return float((mask & col(m["slot"]).notna()).sum()) if m.get("slot") else float(mask.sum())
        if m["agg"] == "count_distinct":
            return float(col(m["slot"])[mask].nunique())
        x = num(m["slot"])[mask].dropna()
        if not len(x):
            return None
        return float(x.sum()) if m["agg"] == "sum" else float(x.mean())

    def grouped(m, keys):
        """Mesure par groupe (mois, catégorie…), calculée par groupby : indépendante de la requête SQL."""
        if m["agg"] == "add":
            return sum(grouped(t, keys).fillna(0) for t in m["terms"])
        mask = cond(m["where"]).fillna(False).astype(bool) if m.get("where") else pd.Series(True, index=df.index)
        if m["agg"] == "count":
            ok = mask & col(m["slot"]).notna() if m.get("slot") else mask
            return ok.astype(float).groupby(keys).sum()
        if m["agg"] == "count_distinct":
            return col(m["slot"]).where(mask).groupby(keys).nunique().astype(float)
        x = num(m["slot"]).where(mask)
        return x.groupby(keys).sum(min_count=1) if m["agg"] == "sum" else x.groupby(keys).mean()

    if f["kind"] == "value":
        return measure(f["measure"])
    if f["kind"] in {"ratio", "rate"}:
        n, d = measure(f["num"]), measure(f["den"])
        return None if not d or n is None else n / d
    if f["kind"] == "growth":
        t, c = binding["slots"][f["date"]]
        key = f"{t}.{c}_date_key" if f"{t}.{c}_date_key" in df else f"{binding['fact']}.{time_key(binding['fact'])}"
        per = pd.to_numeric(df[key], errors="coerce") // 100
        g = grouped(f["measure"], per).dropna(how="all")
        return growth_from_series(pd.DataFrame({"period": g.index.astype(int), "v": g.to_numpy()}))[0]
    if f["kind"] == "top_share":
        g = grouped(f["measure"], col(f["by"]))
        return top_share_value(pd.DataFrame({"g": g.index, "v": g.to_numpy()}), f["top"])
    if f["kind"] == "repeat_rate":
        g = pd.DataFrame({"e": col(f["entity"]), "t": col(f["transaction"])}).dropna(subset=["e"])
        n = g.groupby("e")["t"].nunique()
        return float((n > 1).mean()) if len(n) else None


# ---------------------------------------------------------------- formule lisible (catalogue, XAI)
def readable(card: dict, binding: dict) -> str:
    c = lambda s: binding["slots"][s][1]
    p = binding["params"]

    def cond(w):
        op = w["op"]
        if op == "dq_flagged":
            return "ligne signalée par la qualité"
        return {"is_true": lambda: f"{c(w['slot'])} = {p['true_value'][w['slot']]}",
                "in_values": lambda: f"{c(w['slot'])} ∈ {{{', '.join(map(str, p['values'][w['slot']]))}}}",
                "negative": lambda: f"{c(w['slot'])} < 0",
                "low_score": lambda: f"{c(w['slot'])} ≤ {p['threshold'][w['slot']]:g}",
                "above": lambda: f"{c(w['slot'])} > {p['threshold'][w['slot']]:g}"}[op]()

    def meas(m):
        if m["agg"] == "add":
            return "(" + " + ".join(meas(t) for t in m["terms"]) + ")"
        target = c(m["slot"]) if m.get("slot") else "*"
        base = {"count": f"COUNT({target})", "count_distinct": f"COUNT(DISTINCT {target})",
                "sum": f"SUM({target})", "avg": f"AVG({target})"}[m["agg"]]
        return base + (f" [si {cond(m['where'])}]" if m.get("where") else "")

    f = card["formula"]
    return {"value": lambda: meas(f["measure"]), "ratio": lambda: f"{meas(f['num'])} / {meas(f['den'])}",
            "rate": lambda: f"{meas(f['num'])} / {meas(f['den'])}",
            "growth": lambda: f"évolution mensuelle de {meas(f['measure'])} (date : {c(f['date'])})",
            "top_share": lambda: f"part des {int(f['top']) if f['top'] >= 1 else format(f['top'], '.0%')} premiers {c(f['by'])} "
                                 f"dans {meas(f['measure'])}",
            "repeat_rate": lambda: f"part des {c(f['entity'])} avec au moins 2 {c(f['transaction'])} distincts"}[f["kind"]]()


print(f"Compilateur prêt · moteur SQL : {BI_ENGINE} · date de référence : {REF_DATE or 'aucune (pas de série temporelle)'}")
