ANALYSIS = {"run_id": RUN_ID, "domain": BI_INPUT["domain"], "sectors": BI_SECTORS, "window_months": WINDOW,
            "reliable_periods": {f: [p[0], p[-1]] if p else [] for f, p in RELIABLE.items()},
            "series": {k: {"label": o["label"], "unit": o["unit"], "periods": [int(p) for p in o["s"].index],
                           "values": [float(v) for v in o["s"].to_numpy()]} for k, o in SERIES.items()},
            "facts": list(FACTS.values()), "insights": INSIGHTS,
            "investigations": [{**i, "axe": list(i["axe"])} for i in INVESTIGATIONS], "breakdown_checks": BREAKDOWN_CHECKS}
(BI_DIR / "analysis.json").write_text(canonical_json(ANALYSIS), encoding="utf-8")
(BI_DIR / "insights.json").write_text(canonical_json(INSIGHTS), encoding="utf-8")
pd.DataFrame(FACTS.values()).drop(columns=["segments"], errors="ignore").to_csv(BI_DIR / "analysis_facts.csv", index=False)
ANALYSIS_SHA256 = sha256_text(canonical_json({"facts": ANALYSIS["facts"], "insights": INSIGHTS}))

chain_ok, chain_msg = AUDIT.verify()
checks9 = {
    "insights produits (ou aucun signal à signaler)": len(INSIGHTS) >= 1 or not any(f["priority"] > 0 for f in FACTS.values()),
    "chaque insight cite au moins un fait": all(i["faits"] for i in INSIGHTS),
    "tous les chiffres des insights vérifiés": all(i["vérifié"] for i in INSIGHTS),
    "faits de segment issus de découpages réconciliés": all(BREAKDOWN_CHECKS.get(f"{f['kpi']} × {f['by'][1]}") == "réconcilié"
                                                            for f in FACTS.values() if f["type"] == "segment"),
    "analyse exportée": (BI_DIR / "insights.json").exists(),
    "journal d'audit intègre": chain_ok,
}
ok9 = all(checks9.values())
AUDIT.log("orchestrator", "checkpoint_step9", {"passed": ok9, **checks9, "analysis_sha256": ANALYSIS_SHA256, "audit_chain": chain_msg},
          level="INFO" if ok9 else "ERROR")
for k, v in checks9.items():
    print(f"{k:50s}: {v}")
print(f"{'Journal d’audit':50s}: {chain_msg}")
print("ÉTAPE 9 VALIDÉE" if ok9 else "ÉTAPE 9 EN ÉCHEC")
pd.DataFrame([{"id": i["id"], "type": i["type"], "titre": i["titre"], "faits": ", ".join(i["faits"]), "source": i["source"],
               "priorité": i["priorité"]} for i in INSIGHTS])
