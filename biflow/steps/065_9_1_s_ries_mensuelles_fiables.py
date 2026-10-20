WINDOW = 3                  # fenêtre de comparaison (mois)
MIN_POINTS = 6              # nombre minimal de mois fiables pour analyser une série
MIN_SEGMENT_ROWS = 30       # taille minimale d'un segment pour être interprété
MIN_SPREAD = 0.10           # écart minimal entre segments (10 % de la moyenne, ou 10 points de part au-dessus d'une répartition égale)
MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def mindex(p: int) -> int:
    return (p // 100) * 12 + p % 100 - 1


def plabel(p: int) -> str:
    return f"{MONTHS_FR[p % 100 - 1]} {p // 100}"


def fmt_rel(r: float) -> str:
    return ("+" if r >= 0 else "−") + f"{abs(100 * r):,.1f}".replace(",", " ").replace(".", ",") + " %"


def fmt_pp(d: float) -> str:
    return ("+" if d >= 0 else "−") + f"{abs(100 * d):,.1f}".replace(".", ",") + " pt"


def reliable_periods(fact: str) -> list[int]:
    """Plus longue suite de mois consécutifs dont le volume atteint 20 % du volume médian de la table."""
    key = time_key(fact)
    if not key:
        return []
    vol = BI_WH.query(f"SELECT CAST(b.{qi(key)} / 100 AS INTEGER) AS period, COUNT(*) AS n FROM {qi(fact)} b "
                      f"WHERE b.{qi(key)} IS NOT NULL GROUP BY 1 ORDER BY 1")
    ok = vol[vol["n"] >= 0.2 * vol["n"].median()]["period"].astype(int).tolist()
    best, run = [], []
    for p in ok:
        run = run + [p] if run and mindex(p) == mindex(run[-1]) + 1 else [p]
        best = run if len(run) > len(best) else best
    return best


def series_meta(kid: str) -> dict:
    """Libellé et unité de la série d'un KPI (pour une évolution : la mesure sous-jacente, mois par mois)."""
    card, b = KB_BY_ID[kid], BINDINGS[kid]
    if card["formula"]["kind"] != "growth":
        return {"label": card["name"], "unit": card["unit"], "direction": card["direction"]}
    m = card["formula"]["measure"]
    if m["agg"] in {"count", "count_distinct"}:
        return {"label": "Volume mensuel (" + ("nombre d'enregistrements" if not m.get("slot") else f"{b['slots'][m['slot']][1]} distincts") + ")",
                "unit": "count", "direction": "up"}
    t, c = b["slots"][m["slot"]]
    return {"label": f"Total mensuel de {c}", "unit": "currency" if "amount" in INV.loc[(t, c), "roles"] else "number",
            "direction": card["direction"] if card["direction"] != "neutral" else "up"}


def is_quality_kpi(kid: str) -> bool:
    """KPI de qualité des données (lignes signalées par la partie 1) : utile au data engineer, pas au décideur."""
    return any(c["op"] == "dq_flagged" for c in conditions_of(KB_BY_ID[kid]["formula"]))


def kpi_weight(row) -> float:
    """Importance d'un KPI pour l'analyse : pertinence, statut, et KPI de qualité des données relégués."""
    w = 0.5 + 0.5 * float(row["relevance"])
    w *= 0.8 if row["status"] == "à confirmer" else 1.0
    if is_quality_kpi(row["id"]):
        w *= 0.3
    return w


RELIABLE = {f: reliable_periods(f) for f in BI_FACTS}
SERIES, SKIPPED_SERIES = {}, {}
order = KPI_CATALOG.assign(_w=KPI_CATALOG.apply(kpi_weight, axis=1),
                           _g=[KB_BY_ID[k]["formula"]["kind"] == "growth" or KB_BY_ID[k]["sectors"][0] == "générique" for k in KPI_CATALOG["id"]])
for _, row in order.sort_values(["_g", "_w"], ascending=[True, False]).iterrows():   # KPI sectoriels d'abord : ils gardent la série
    kid = row["id"]
    if kid not in KPI_SERIES:
        continue
    keep = set(RELIABLE.get(BINDINGS[kid]["fact"], []))
    s = KPI_SERIES[kid].assign(period=lambda d: d["period"].astype(int))
    s = s[s["period"].isin(keep)].dropna(subset=["v"]).set_index("period")["v"].astype(float).sort_index()
    if len(s) < MIN_POINTS:
        SKIPPED_SERIES[kid] = f"{len(s)} mois fiables (minimum {MIN_POINTS})"
        continue
    meta = series_meta(kid)
    twin = next((k for k, o in SERIES.items() if o["unit"] == meta["unit"] and len(o["s"].index.intersection(s.index)) >= MIN_POINTS
                 and np.nan_to_num(o["s"].reindex(s.index).corr(s) if s.std() and o["s"].std() else 0) > 0.995), None)
    if twin:
        SKIPPED_SERIES[kid] = f"redondante avec {twin}"
        continue
    SERIES[kid] = {**meta, "s": s, "weight": row["_w"], "fact_table": BINDINGS[kid]["fact"]}

AUDIT.log("bi_analyst", "series_prepared", {"reliable_periods": {f: [p[0], p[-1]] if p else [] for f, p in RELIABLE.items()},
                                            "analysed": list(SERIES), "skipped": SKIPPED_SERIES})
print(f"{len(SERIES)} séries analysées · {len(SKIPPED_SERIES)} écartées")
for f, p in RELIABLE.items():
    print(f"  {f} : " + (f"{len(p)} mois fiables ({plabel(p[0])} → {plabel(p[-1])})" if p else "aucune date"))
pd.DataFrame([{"id": k, "série": o["label"], "mois": len(o["s"]), "début": plabel(o["s"].index[0]), "fin": plabel(o["s"].index[-1]),
               "poids": round(o["weight"], 2)} for k, o in SERIES.items()]
             + [{"id": k, "série": "écartée", "fin": r} for k, r in SKIPPED_SERIES.items()])
