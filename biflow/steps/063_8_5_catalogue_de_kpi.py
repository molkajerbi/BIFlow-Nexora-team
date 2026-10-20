def fmt_value(v: float | None, unit: str) -> str:
    if v is None:
        return "—"
    sep = lambda s: s.replace(",", " ").replace(".", ",")
    if unit == "percent":
        return sep(f"{100 * v:,.1f}") + " %"
    if unit == "count":
        return sep(f"{v:,.0f}")
    if unit == "days":
        return sep(f"{v:,.1f}") + " j"
    if unit == "currency":
        return sep(f"{v:,.2f}")
    return sep(f"{v:,.2f}")


def flagged_share(fact: str) -> float | None:
    if "_dq_flags" not in BI_INPUT["tables"][fact]["columns"]:
        return None
    return float(BI_WH.query(f"SELECT AVG(CASE WHEN _dq_flags IS NOT NULL THEN 1.0 ELSE 0.0 END) AS v FROM {qi(fact)}")["v"].iloc[0])


FLAGGED = {f: flagged_share(f) for f in BI_FACTS}
reliability = lambda s: "—" if s is None else "fiable" if s < 0.01 else "à surveiller" if s < 0.05 else "fragile"

rows = []
for kid, r in RESULTS.items():
    if not r["passed"]:
        continue
    card, b = KB_BY_ID[kid], BINDINGS[kid]
    status = "validé" if b["source"] in {"évidente", "LLM"} else "à confirmer"
    rows.append({"id": kid, "name": card["name"], "sector": card["sectors"][0], "value": r["value"], "unit": card["unit"],
                 "direction": card["direction"], "definition": card["definition"], "formula": readable(card, b),
                 "fact": b["fact"], "columns": sorted({f"{t}.{c}" for t, c in b["slots"].values()}), "binding": b["source"],
                 "status": status, "flagged_rows_pct": FLAGGED[b["fact"]], "reliability": reliability(FLAGGED[b["fact"]]),
                 "relevance": float(RELEVANCE.get(kid, 0.5)), "sql": r["sql"], "tests": r["tests"],
                 "periods": 0 if r.get("series") is None else int(r["series"]["v"].notna().sum()),
                 "growth_detail": r.get("growth_detail")})
catalog = pd.DataFrame(rows)

# doublons : même valeur, même unité, mêmes colonnes → on garde la fiche sectorielle, puis la plus pertinente
if len(catalog):
    catalog["_key"] = catalog.apply(lambda r: (round(r["value"], 9), tuple(r["columns"])), axis=1)
    catalog["_rank"] = catalog["sector"].map(lambda s: 0 if s not in {"générique", "proposé"} else 1 if s == "proposé" else 2)
    catalog = catalog.sort_values(["_rank", "relevance"], ascending=[True, False])
    DUPLICATES = catalog[catalog.duplicated("_key")]["id"].tolist()
    catalog = catalog.drop_duplicates("_key").drop(columns=["_key", "_rank"])
else:
    DUPLICATES = []

# un KPI générique est remplacé par son équivalent sectoriel quand celui-ci est calculé (ex. « entités actives » → « clients acheteurs »)
SUPERSEDED_BY = {
    "GEN_TRANSACTIONS": ["COM_ORDERS", "TRP_TRIPS"], "GEN_RECORDS": ["COM_ORDERS", "TRP_TRIPS", "GEN_TRANSACTIONS"],
    "GEN_ACTIVE_ENTITIES": ["COM_CUSTOMERS"], "GEN_TOTAL": ["COM_REVENUE", "TEL_MRR", "TRP_REVENUE", "BNK_OUTSTANDING"],
    "GEN_AVG_PER_TRX": ["COM_AOV", "TRP_REVENUE_PER_TRIP"], "GEN_AVG_PER_ENTITY": ["COM_REVENUE_PER_CUSTOMER", "TEL_ARPU"],
    "GEN_AVG_DELAY": ["COM_DELIVERY_TIME", "TRP_AVG_DURATION", "TEL_TENURE"], "GEN_OVERDUE_RATE": ["COM_LATE_DELIVERY", "TRP_DELAY_RATE"],
    "GEN_STATUS_RATE": ["COM_CANCEL_RATE"], "GEN_AVG_MEASURE": ["COM_AVG_RATING", "TEL_TENURE", "BNK_AVG_BALANCE"],
    "GEN_FLAG_RATE": ["COM_LATE_DELIVERY", "TEL_CHURN_RATE", "BNK_SUBSCRIPTION_RATE", "BNK_DEFAULT_RATE"],
    "GEN_TOP_CATEGORY_SHARE": ["COM_CATEGORY_CONCENTRATION"],
}
present = set(catalog["id"]) if len(catalog) else set()
REPLACED = {g: next(k for k in subs if k in present) for g, subs in SUPERSEDED_BY.items() if g in present and set(subs) & present}
catalog = catalog[~catalog["id"].isin(REPLACED)] if len(catalog) else catalog

# validation humaine facultative
KPI_REVIEW = globals().get("OVERRIDES", {}).get("kpis", {})
if KPI_REVIEW:
    catalog.loc[catalog["id"].isin(KPI_REVIEW.get("approved", [])), "status"] = "validé (humain)"
    catalog = catalog[~catalog["id"].isin(KPI_REVIEW.get("rejected", []))]
    AUDIT.log("human", "kpi_catalog_reviewed", KPI_REVIEW, level="DECISION")

STATUS_ORDER = {"validé (humain)": 0, "validé": 1, "à confirmer": 2}
catalog = catalog.sort_values(["status", "relevance"], key=lambda c: c.map(STATUS_ORDER) if c.name == "status" else -c) \
                 .reset_index(drop=True)
KPI_CATALOG = catalog
KPI_SERIES = {k: RESULTS[k]["series"].assign(id=k) for k in catalog["id"] if RESULTS[k].get("series") is not None}
FAILED = {k: (r["error"] or [t for t, ok in r["tests"].items() if not ok]) for k, r in RESULTS.items() if not r["passed"]}

(BI_DIR / "kpi_catalog.json").write_text(canonical_json(
    {"run_id": RUN_ID, "domain": BI_INPUT["domain"], "sectors": BI_SECTORS, "mode": BI_MODE, "reference_date": REF_DATE,
     "kpis": catalog.to_dict(orient="records"), "dropped": DROPPED, "failed": FAILED, "duplicates": DUPLICATES,
     "replaced": REPLACED}), encoding="utf-8")
catalog.drop(columns=["sql", "tests", "growth_detail"]).to_csv(BI_DIR / "kpi_catalog.csv", index=False)
if KPI_SERIES:
    pd.concat(KPI_SERIES.values(), ignore_index=True)[["id", "period", "v"]].to_csv(BI_DIR / "kpi_series.csv", index=False)
CATALOG_SHA256 = sha256_text(canonical_json(catalog[["id", "value", "sql"]].to_dict(orient="records")))
AUDIT.log("kpi_agent", "kpi_catalog_built", {"kpis": len(catalog), "validated": int(catalog["status"].str.startswith("validé").sum()),
                                             "to_confirm": int((catalog["status"] == "à confirmer").sum()), "duplicates": DUPLICATES,
                                             "failed": FAILED, "sha256": CATALOG_SHA256}, level="DECISION")
print(f"Catalogue : {len(catalog)} KPI · {int(catalog['status'].str.startswith('validé').sum())} validé(s) · "
      f"{int((catalog['status'] == 'à confirmer').sum())} à confirmer · {len(DUPLICATES)} doublon(s) et "
      f"{len(REPLACED)} générique(s) remplacé(s) retiré(s) · "
      f"{len(FAILED)} en échec · {len(KPI_SERIES)} avec série mensuelle")
catalog.assign(valeur=[fmt_value(v, u) for v, u in zip(catalog["value"], catalog["unit"])])[
    ["id", "name", "valeur", "status", "binding", "reliability", "periods", "formula"]]
