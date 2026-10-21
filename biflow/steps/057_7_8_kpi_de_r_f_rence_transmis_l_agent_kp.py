def kpi_relevance() -> pd.Series:
    sim = SEARCH.similarity([dataset_text()], [card_text(c) for c in KPI_KB])[0]
    rel = sim / sim.max() if sim.max() > 0 else sim
    fits = pd.Series({i: a["fit"] for i, a in KPI_ASSESSMENT.items()})
    fit_rel = fits / fits.max() if fits.max() > 0 else fits
    return pd.Series({c["id"]: round(0.4 * float(r) + 0.3 * float(fit_rel[c["id"]]) + 0.3 * KPI_ASSESSMENT[c["id"]]["confidence"], 3)
                      for c, r in zip(KPI_KB, rel)})


RELEVANCE = kpi_relevance()
selected = [c for c in KPI_KB if (set(c["sectors"]) & {"generic", *BI_SECTORS})]
KPI_REFERENCES = sorted(
    [{"id": c["id"], "name": c["name"], "sector": c["sectors"][0], "relevance": float(RELEVANCE[c["id"]]),
      **{k: KPI_ASSESSMENT[c["id"]][k] for k in ("feasible", "fact", "missing", "fit", "confidence", "candidates")}} for c in selected],
    key=lambda r: (-r["feasible"], r["sector"] == "generic", -r["relevance"]))
references_df = pd.DataFrame([{**{k: r[k] for k in ("id", "name", "sector", "feasible", "confidence", "relevance", "fact")},
                               "suggested binding": "; ".join(f"{s}→{v[0]['column']}" for s, v in r["candidates"].items() if v) or "—",
                               "missing": ", ".join(r["missing"]) or "—"} for r in KPI_REFERENCES])
(RUN_DIR / "bi").mkdir(exist_ok=True)
(RUN_DIR / "bi" / "kpi_references.json").write_text(canonical_json(KPI_REFERENCES), encoding="utf-8")
BI_INVENTORY.to_csv(RUN_DIR / "bi" / "semantic_inventory.csv", index=False)
AUDIT.log("bi_knowledge", "kpi_references_selected",
          {"selected": len(KPI_REFERENCES), "feasible": int(references_df["feasible"].sum()), "mode": BI_MODE,
           "ids": [r["id"] for r in KPI_REFERENCES if r["feasible"]]})
print(f"{len(KPI_REFERENCES)} cards handed to the KPI agent · {int(references_df['feasible'].sum())} computable · {BI_MODE} mode")
references_df
