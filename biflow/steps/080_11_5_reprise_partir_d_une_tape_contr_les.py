RESUME_RESULT = run_bi_insight(start_from="dashboard")
display(bi_history_table(RESUME_RESULT))

run_report = json.loads((RUN_DIR / "bi_insight_run.json").read_text(encoding="utf-8"))
executed = [h["node"] for h in BI_RESULT["history"]]
chain_ok, chain_msg = AUDIT.verify()
checks11 = {
    "full run: status success": BI_RESULT["status"] == "success",
    "the 4 agents executed in order": [n for n in executed if n in STAGE_NAMES] == STAGE_NAMES,
    "each step passed its checkpoint": all(globals().get(s["checkpoint"]) for s in STAGES),
    "files produced (dashboard, catalog, analysis)": {"dashboard", "catalog", "analysis"} <= set(BI_RESULT["outputs"]),
    "resume: only the dashboard is redone": RESUME_RESULT["status"] == "success"
        and [h["node"] for h in RESUME_RESULT["history"] if h["node"] in STAGE_NAMES] == ["dashboard_agent"],
    "run report written": run_report["status"] == "success",
    "audit log intact": chain_ok,
}
ok11 = all(checks11.values())
AUDIT.log("orchestrator", "checkpoint_step11", {"passed": ok11, **checks11, "reproducibility": REPRO, "audit_chain": chain_msg},
          level="INFO" if ok11 else "ERROR")
for k, v in checks11.items():
    print(f"{k:50s}: {v}")
print(f"{'Reproducibility (catalog / analysis / insights)':50s}: {' / '.join('yes' if v else 'no' for v in REPRO.values())}")
print(f"{'Audit log':50s}: {chain_msg}")
print("STEP 11 PASSED" if ok11 else "STEP 11 FAILED")
