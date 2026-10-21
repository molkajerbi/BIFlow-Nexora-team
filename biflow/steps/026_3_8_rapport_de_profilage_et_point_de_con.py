PROFILING_REPORT = FINDINGS.merge(INTERPRETATIONS.drop(columns="attempt"), on="id", how="left")

prof_dir = RUN_DIR / "profiling"
prof_dir.mkdir(exist_ok=True)
PROFILING_REPORT.to_csv(prof_dir / "profiling_report.csv", index=False)
AGENT_RUN["trace"].to_csv(prof_dir / "profiler_agent_trace.csv", index=False)

checks3 = checkpoint_raw_integrity()
chain_ok, chain_msg = AUDIT.verify()
metrics3 = {
    "required_investigations": len(REQUIRED),
    "done_by_agent": len(AGENT_RUN["done"]),
    "supervisor_fallback": len(AGENT_RUN["fallback"]),
    "rejected_decisions": int((AGENT_RUN["trace"]["status"] == "rejected").sum()),
    "findings": len(PROFILING_REPORT),
    "interpreted_by_LLM": int((PROFILING_REPORT["source"] == "LLM").sum()),
    "interpretation_fallback": int((PROFILING_REPORT["source"] == "fallback").sum()),
}
ok3 = bool(checks3["content_unchanged"].all()) and chain_ok and PROFILING_REPORT["action"].notna().all()
AUDIT.log("orchestrator", "checkpoint_step3", {"passed": ok3, **metrics3, "audit_chain": chain_msg},
          level="INFO" if ok3 else "ERROR")

for k, v in metrics3.items():
    print(f"{k:30s}: {v}")
print(f"Raw data unchanged              : {bool(checks3['content_unchanged'].all())}")
print(f"Audit log                       : {chain_msg}")
print("STEP 3 PASSED" if ok3 else "STEP 3 FAILED")
display(PROFILING_REPORT.groupby(["action", "severity"]).size().unstack(fill_value=0))
PROFILING_REPORT[["id", "table", "column", "finding", "interpretation", "action", "severity", "source"]]
