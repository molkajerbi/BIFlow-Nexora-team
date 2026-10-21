ANALYSIS = {"run_id": RUN_ID, "domain": BI_INPUT["domain"], "sectors": BI_SECTORS, "window_months": WINDOW,
            "reliable_periods": {f: [p[0], p[-1]] if p else [] for f, p in RELIABLE.items()},
            "series": {k: {"label": o["label"], "unit": o["unit"], "periods": [int(p) for p in o["s"].index],
                           "values": [float(v) for v in o["s"].to_numpy()]} for k, o in SERIES.items()},
            "facts": list(FACTS.values()), "insights": INSIGHTS,
            "investigations": [{**i, "axis": list(i["axis"])} for i in INVESTIGATIONS], "breakdown_checks": BREAKDOWN_CHECKS}
(BI_DIR / "analysis.json").write_text(canonical_json(ANALYSIS), encoding="utf-8")
(BI_DIR / "insights.json").write_text(canonical_json(INSIGHTS), encoding="utf-8")
pd.DataFrame(FACTS.values()).drop(columns=["segments"], errors="ignore").to_csv(BI_DIR / "analysis_facts.csv", index=False)
ANALYSIS_SHA256 = sha256_text(canonical_json({"facts": ANALYSIS["facts"], "insights": INSIGHTS}))

chain_ok, chain_msg = AUDIT.verify()
checks9 = {
    "insights produced (or no signal to report)": len(INSIGHTS) >= 1 or not any(f["priority"] > 0 for f in FACTS.values()),
    "each insight cites at least one fact": all(i["facts"] for i in INSIGHTS),
    "all insight figures verified": all(i["verified"] for i in INSIGHTS),
    "segment facts from reconciled breakdowns": all(BREAKDOWN_CHECKS.get(f"{f['kpi']} × {f['by'][1]}") == "reconciled"
                                                    for f in FACTS.values() if f["type"] == "segment"),
    "analysis exported": (BI_DIR / "insights.json").exists(),
    "audit log intact": chain_ok,
}
ok9 = all(checks9.values())
AUDIT.log("orchestrator", "checkpoint_step9", {"passed": ok9, **checks9, "analysis_sha256": ANALYSIS_SHA256, "audit_chain": chain_msg},
          level="INFO" if ok9 else "ERROR")
for k, v in checks9.items():
    print(f"{k:50s}: {v}")
print(f"{'Audit log':50s}: {chain_msg}")
print("STEP 9 PASSED" if ok9 else "STEP 9 FAILED")
pd.DataFrame([{"id": i["id"], "type": i["type"], "title": i["title"], "facts": ", ".join(i["facts"]), "source": i["source"],
               "priority": i["priority"]} for i in INSIGHTS])
