PROFILING_REPORT = FINDINGS.merge(INTERPRETATIONS.drop(columns="attempt"), on="id", how="left")

prof_dir = RUN_DIR / "profiling"
prof_dir.mkdir(exist_ok=True)
PROFILING_REPORT.to_csv(prof_dir / "profiling_report.csv", index=False)
AGENT_RUN["trace"].to_csv(prof_dir / "profiler_agent_trace.csv", index=False)

checks3 = checkpoint_raw_integrity()
chain_ok, chain_msg = AUDIT.verify()
metrics3 = {
    "investigations_obligatoires": len(REQUIRED),
    "réalisées_par_agent": len(AGENT_RUN["done"]),
    "fallback_superviseur": len(AGENT_RUN["fallback"]),
    "décisions_rejetées": int((AGENT_RUN["trace"]["status"] == "rejetée").sum()),
    "constats": len(PROFILING_REPORT),
    "interprétés_par_LLM": int((PROFILING_REPORT["source"] == "LLM").sum()),
    "fallback_interprétation": int((PROFILING_REPORT["source"] == "fallback").sum()),
}
ok3 = bool(checks3["contenu_inchangé"].all()) and chain_ok and PROFILING_REPORT["action"].notna().all()
AUDIT.log("orchestrator", "checkpoint_step3", {"passed": ok3, **metrics3, "audit_chain": chain_msg},
          level="INFO" if ok3 else "ERROR")

for k, v in metrics3.items():
    print(f"{k:30s}: {v}")
print(f"Données brutes inchangées       : {bool(checks3['contenu_inchangé'].all())}")
print(f"Journal d'audit                 : {chain_msg}")
print("ÉTAPE 3 VALIDÉE" if ok3 else "ÉTAPE 3 EN ÉCHEC")
display(PROFILING_REPORT.groupby(["action", "severity"]).size().unstack(fill_value=0))
PROFILING_REPORT[["id", "table", "colonne", "constat", "interpretation", "action", "severity", "source"]]
