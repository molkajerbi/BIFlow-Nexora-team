def dimensions(kid: str) -> list[tuple[str, str]]:
    """Breakdown axes of a KPI: categories or locations reachable from its base table (2 to 100 values), except the
    formula columns, statuses and yes/no flags (outcomes, not segments) and "twin" axes."""
    b, card = BINDINGS[kid], KB_BY_ID[kid]
    if card["formula"]["kind"] not in {"value", "ratio", "rate", "growth"}:
        return []
    reach, used = reachable_tables(b["fact"]), set(b["slots"].values())
    rows = BI_INVENTORY[BI_INVENTORY["table"].isin(reach) & BI_INVENTORY["semantic"].isin(["category", "zip"])]
    return sorted((r.table, r.column) for r in rows.itertuples()
                  if ({"category", "location"} & set(r.roles)) and not {"status", "flag"} & set(r.roles)   # un statut ou un indicateur oui/non est un résultat, pas un segment
                  and 2 <= (r.distinct or 0) <= MAX_GROUP_VALUES and (r.table, r.column) not in used
                  and not twin_axis((r.table, r.column), used))


def twin_axis(dim: tuple[str, str], used: set) -> bool:
    """"Twin" axis of a formula column (same values, e.g. assigned room / reserved room): the breakdown
    would only rediscover the KPI's condition ("type F" at 73% in segment "F")."""
    vals = set(observed_values(*dim))
    return any(len(vals & set(observed_values(*u))) >= 0.8 * len(vals) for u in used
               if INV.loc[u, "semantic"] in {"category", "zip"})


def decompose(card: dict) -> tuple[dict, dict | None, bool, str]:
    """Numerator, denominator, additivity and interpretation mode ("share" of a total or "level" of a rate / an average)."""
    f = card["formula"]
    if f["kind"] in {"ratio", "rate"}:
        additive = "count_distinct" not in (f["num"]["agg"], f["den"]["agg"])
        return f["num"], f["den"], additive, "level"
    m = f["measure"]
    if m["agg"] == "avg":
        return {**m, "agg": "sum"}, {**m, "agg": "count"}, True, "level"
    return m, None, m["agg"] != "count_distinct", "share"


def breakdown(kid: str, dim: tuple[str, str], window: list[int] | None = None) -> pd.DataFrame:
    """KPI per segment: numerator, denominator, rows and value (SQL, same joins as the catalog)."""
    card, b = KB_BY_ID[kid], BINDINGS[kid]
    num, den, _, _ = decompose(card)
    q = KPIQuery(card, {**b, "slots": {**b["slots"], "__by": dim}})
    where = ""
    if window:
        key = time_key(b["fact"])
        where = f"WHERE b.{qi(key)} BETWEEN {window[0] * 100} AND {window[1] * 100 + 99}"
    sql = (f"SELECT {q.col('__by')} AS g, {q.measure(num)} AS num, {q.measure(den) if den else 'NULL'} AS den, COUNT(*) AS n "
           f"{q.from_sql} {where} GROUP BY 1")
    d = BI_WH.query(sql)
    d["g"] = d["g"].astype(object).where(d["g"].notna(), "(not specified)").astype(str)
    d[["num", "den"]] = d[["num", "den"]].apply(pd.to_numeric, errors="coerce")
    d["value"] = d["num"] / d["den"].where(d["den"] != 0) if den else d["num"]
    d.attrs["sql"] = sql
    return d


def reconciles(kid: str, d: pd.DataFrame) -> bool:
    """Does the sum of the segments give back the catalog value? (impossible to check for a distinct count)"""
    card = KB_BY_ID[kid]
    num, den, additive, _ = decompose(card)
    if not additive or card["formula"]["kind"] == "growth":
        return True
    total = d["num"].sum() / d["den"].sum() if den else d["num"].sum()
    ref = float(KPI_CATALOG.set_index("id").loc[kid, "value"])
    return abs(total - ref) <= 1e-6 * max(1.0, abs(ref))


def ranked(df: pd.DataFrame, col: str, by_abs: bool = False) -> pd.DataFrame:
    """Reproducible descending sort: ties (within 1e-12, since parallel SQL sums may differ in the last
    digit) are broken by the segment name, never by the order returned by the database."""
    key = (df[col].abs() if by_abs else df[col]).astype(float).round(12)
    return df.assign(_k=key).sort_values(["_k", "g"], ascending=[False, True], kind="mergesort").drop(columns="_k")


def segment_spread(kid: str, d: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    """Discriminating power of an axis: spread of the segments (level) or concentration (share)."""
    _, den, additive, mode = decompose(KB_BY_ID[kid])
    if mode == "share" and not additive:                 # des comptages distincts ne s'additionnent pas : pas de part
        return 0.0, d.iloc[0:0]
    big = d[(d["n"] >= MIN_SEGMENT_ROWS) & (d["g"] != "(not specified)")].copy()
    if len(big) < 2:
        return 0.0, big
    if mode == "share":
        big["share"] = big["num"] / d["num"].sum()
        return float(big["share"].max() - 1 / len(d)), ranked(big, "share")
    overall = d["num"].sum() / d["den"].sum()
    w = big["den"] / big["den"].sum()
    spread = math.sqrt(float((w * (big["value"] - overall) ** 2).sum())) / abs(overall) if overall else 0.0
    return spread, ranked(big, "value")


def segment_fact(kid: str, dim: tuple[str, str], d: pd.DataFrame, spread: float, big: pd.DataFrame, weight: float) -> str | None:
    card = KB_BY_ID[kid]
    _, _, _, mode = decompose(card)
    unit = series_meta(kid)["unit"] if card["formula"]["kind"] == "growth" else card["unit"]
    label = series_meta(kid)["label"] if card["formula"]["kind"] == "growth" else card["name"]
    if mode == "share":
        top = big.head(3)
        nums = [fmt_value(v, "percent") for v in top["share"]] + [fmt_value(float(top["share"].sum()), "percent")]
        text = (f"{label} by {dim[1]}: “{top['g'].iloc[0]}” accounts for {nums[0]} of the total" +
                (f", the top {len(top)} segments {nums[-1]}" if len(top) > 1 else "") + f" ({len(d)} segments).")
        figures = {f"share of total for “{g}”": v for g, v in zip(top["g"], nums)}
        if len(top) > 1:
            figures[f"cumulative share of the top {len(top)} segments"] = nums[-1]
        return add_fact(kid, "segment", text, nums, min(spread * 2, 1) * weight * 0.7, direction=None, valence="neutral", by=list(dim), label=label,
                        figures=figures,
                        segments=top[["g", "share"]].to_dict(orient="records"))
    overall = d["num"].sum() / d["den"].sum()
    hi, lo = big.iloc[0], big.iloc[-1]
    nums = [fmt_value(overall, unit), fmt_value(hi["value"], unit), fmt_value(lo["value"], unit)]
    worst = lo if card["direction"] == "up" else hi
    text = (f"{label} by {dim[1]}: from {nums[2]} (“{lo['g']}”) to {nums[1]} (“{hi['g']}”) for an average of {nums[0]}; "
            f"{len(big)} segments of at least {MIN_SEGMENT_ROWS} rows.")
    return add_fact(kid, "segment", text, nums, min(spread, 1) * weight * 0.9, direction=None,
                    # un écart entre segments n'est une alerte que pour un taux orienté (retard, churn…) ; un panier moyen
                    # plus élevé dans une catégorie de produits chers est structurel
                    valence="unfavorable" if unit == "percent" and card["direction"] != "neutral" else "neutral",
                    by=list(dim), worst_segment=str(worst["g"]), label=label,
                    figures={"average across all segments": nums[0], f"highest value (“{hi['g']}”)": nums[1],
                             f"lowest value (“{lo['g']}”)": nums[2],
                             **{f"value of “{r.g}”": fmt_value(r.value, unit)            # segments intermédiaires, citables
                                for r in big.iloc[1:-1].head(4).itertuples()}},
                    segments=big[["g", "value", "n"]].head(10).to_dict(orient="records"))


def contribution_fact(kid: str, dim: tuple[str, str], windows: list[list[int]], parent: str) -> str | None:
    """Which segments explain the change between two time windows?"""
    card = KB_BY_ID[kid]
    _, den, additive, mode = decompose(card)
    before, after = breakdown(kid, dim, windows[0]), breakdown(kid, dim, windows[1])
    m = before.merge(after, on="g", how="outer", suffixes=("_a", "_b")).fillna({"num_a": 0, "num_b": 0, "den_a": 0, "den_b": 0, "n_a": 0, "n_b": 0})
    m = m[(m["n_a"] + m["n_b"]) >= MIN_SEGMENT_ROWS]
    if not additive or m.empty:
        return None
    unit = series_meta(kid)["unit"] if card["formula"]["kind"] == "growth" else card["unit"]
    label = series_meta(kid)["label"] if card["formula"]["kind"] == "growth" else card["name"]
    span = lambda w: plabel(w[0]) if w[0] == w[1] else f"{plabel(w[0])}–{plabel(w[1])}"
    period = f"between {span(windows[0])} and {span(windows[1])}"
    if mode == "share":                                  # totaux ramenés à une moyenne mensuelle : fenêtres de durées différentes
        months = [mindex(w[1]) - mindex(w[0]) + 1 for w in windows]
        m["ma"], m["mb"] = m["num_a"] / months[0], m["num_b"] / months[1]
        total = m["mb"].sum() - m["ma"].sum()
        if not total:
            return None
        m["c"] = (m["mb"] - m["ma"]) / total
        top = ranked(m, "c", by_abs=True).iloc[0]
        nums = [fmt_value(float(top["c"]), "percent"), fmt_value(float(top["ma"]), unit), fmt_value(float(top["mb"]), unit)]
        text = (f"{label}: {period}, the segment {dim[1]} = “{top['g']}” alone explains {nums[0]} of the total change "
                f"(as a monthly average, this segment goes from {nums[1]} to {nums[2]}).")
        figures = {f"share of the total change explained by “{top['g']}” (this is NOT an increase of the KPI)": nums[0],
                   f"monthly average of “{top['g']}” before": nums[1], f"monthly average of “{top['g']}” after": nums[2]}
        steps = ranked(m.assign(d=m["mb"] - m["ma"]), "d", by_abs=True)       # décomposition complète (cascade du dashboard)
        bridge = {"start": float(m["ma"].sum()), "end": float(m["mb"].sum()),
                  "steps": [{"g": str(r.g), "delta": float(r.d)} for r in steps.head(6).itertuples()]}
    else:
        va = m["num_a"].sum() / m["den_a"].sum() if m["den_a"].sum() else None
        vb = m["num_b"].sum() / m["den_b"].sum() if m["den_b"].sum() else None
        if va is None or vb is None or va == vb:
            return None
        m["ra"] = m["num_a"] / m["den_a"].where(m["den_a"] > 0)
        m["rb"] = m["num_b"] / m["den_b"].where(m["den_b"] > 0)
        m["effect"] = (m["rb"] - m["ra"]) * m["den_b"] / m["den_b"].sum()        # effet « taux » pondéré par le poids récent
        m = m.dropna(subset=["effect"])
        if m.empty:
            return None
        top = ranked(m, "effect", by_abs=True).iloc[0]
        share = float(top["effect"] / (vb - va))
        nums = [fmt_value(float(top["ra"]), unit), fmt_value(float(top["rb"]), unit), fmt_value(abs(share), "percent")]
        if unit == "percent":
            nums.append(fmt_pp(float(top["rb"] - top["ra"])))
        text = (f"{label}: {period}, the largest contribution comes from {dim[1]} = “{top['g']}”: in this segment, the KPI goes "
                f"from {nums[0]} to {nums[1]}{f' ({nums[3]})' if len(nums) > 3 else ''}; this segment explains about {nums[2]} "
                f"of the overall change.")
        figures = {f"value of “{top['g']}” before": nums[0], f"value of “{top['g']}” after": nums[1],
                   f"share of the overall change explained by “{top['g']}” (this is NOT an increase of the KPI)": nums[2]}
        if len(nums) > 3:
            figures[f"gap in points within “{top['g']}”"] = nums[3]
        steps = ranked(m, "effect", by_abs=True)                              # décomposition complète (cascade du dashboard)
        bridge = {"start": float(va), "end": float(vb),
                  "steps": [{"g": str(r.g), "delta": float(r.effect)} for r in steps.head(6).itertuples()]}
    return add_fact(kid, "contribution", text, nums, FACTS[parent]["priority"] * 0.95, direction=FACTS[parent].get("direction"), figures=figures,
                    valence=FACTS[parent].get("valence", "neutral"), by=list(dim), parent=parent, label=label, segment=str(top["g"]),
                    bridge={**bridge, "unit": unit, "windows": windows})


DIMS = {kid: dimensions(kid) for kid in KPI_CATALOG["id"]}
EXPLORATION, BREAKDOWN_CHECKS, SPREADS = {}, {}, {}
weights = {r["id"]: kpi_weight(r) for _, r in KPI_CATALOG.iterrows()}
for kid, dims in DIMS.items():
    if KB_BY_ID[kid]["formula"]["kind"] == "growth" or is_quality_kpi(kid):   # mesure déjà couverte / indicateur technique
        continue
    best = None
    for dim in dims:
        try:
            d = breakdown(kid, dim)
        except Exception as exc:                          # un axe qui échoue est ignoré, l'analyse continue
            BREAKDOWN_CHECKS[f"{kid} × {dim[1]}"] = f"error: {type(exc).__name__}"
            continue
        ok = reconciles(kid, d)
        BREAKDOWN_CHECKS[f"{kid} × {dim[1]}"] = "reconciled" if ok else "dropped (does not reconcile)"
        if not ok:
            continue
        spread, big = segment_spread(kid, d)
        SPREADS.setdefault(kid, {})[dim] = spread
        if spread >= MIN_SPREAD and (best is None or spread > best[0]):
            best = (spread, dim, d, big)
    if best:
        EXPLORATION[kid] = {"by": best[1], "spread": round(best[0], 4)}
        EXPLORATION[kid]["fact"] = segment_fact(kid, best[1], best[2], best[0], best[3], float(weights[kid]))

n_ok = sum(v == "reconciled" for v in BREAKDOWN_CHECKS.values())
AUDIT.log("bi_analyst", "segments_explored", {"checks": BREAKDOWN_CHECKS, "best_axis": {k: v["by"] for k, v in EXPLORATION.items()}})
print(f"{len(BREAKDOWN_CHECKS)} breakdowns computed · {n_ok} reconciled with the catalog · "
      f"{len(EXPLORATION)} KPIs with a discriminating axis")
pd.DataFrame([{"KPI": k, "most discriminating axis": v["by"][1], "spread": v["spread"], "fact": v["fact"],
               "finding": FACTS[v["fact"]]["text"] if v["fact"] else "—"} for k, v in EXPLORATION.items()])
