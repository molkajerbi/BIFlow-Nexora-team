parts = BIFLOW_RESULT.get("parts", {})
display(pd.DataFrame([
    ("Input check", ", ".join(f"{k}: {v}" for k, v in parts.get("preflight", {}).items())),
    ("Data Preparation Agent", ", ".join(f"{k}: {v}" for k, v in parts.get("data_preparation", {}).items()) or "not executed"),
    ("BI & Insight Agent", ", ".join(f"{k}: {v}" for k, v in parts.get("bi_insight", {}).items()) or "not executed"),
    ("XAI Agent", ", ".join(f"{k}: {v}" for k, v in parts.get("explainability", {}).items())),
], columns=["part", "result"]))
display(pd.DataFrame([{"deliverable": k, "file": Path(v).name} for k, v in BIFLOW_RESULT.get("outputs", {}).items()]))

chain_ok, chain_msg = AUDIT.verify()
run_report = json.loads((RUN_DIR / "biflow_run_report.json").read_text(encoding="utf-8"))
executed = [h["node"] for h in BIFLOW_RESULT["history"]]
checks13 = {
    "full pipeline: status success": BIFLOW_RESULT["status"] == "success",
    "the parts executed in order": executed == ["preflight", "data_preparation", "bi_insight", "explainability", "deliver"],
    "checkpoints of the sub-orchestrators": DATA_PREP_RESULT["status"] == "success" and BI_RESULT["status"] == "success",
    "explainability built on the full run": len(LEDGER) > 0 and any(r["step"] == 13 for r in LEDGER),
    "deliverables present (warehouse, KPIs, insights, dashboard, XAI)": {"warehouse (star schema)", "KPI catalog", "dashboard",
                                                                        "decision ledger (XAI)"} <= set(BIFLOW_RESULT.get("outputs", {})),
    "run report written": run_report["status"] == BIFLOW_RESULT["status"],
    "raw data unchanged": bool(checkpoint_raw_integrity()["content_unchanged"].all()),
    "audit log intact": chain_ok,
}
ok13 = all(checks13.values())
AUDIT.log("orchestrator", "checkpoint_step13", {"passed": ok13, **checks13, "reproducibility": REPRO_GLOBAL, "audit_chain": chain_msg},
          level="INFO" if ok13 else "ERROR")
for k, v in checks13.items():
    print(f"{k:60s}: {v}")
print(f"{'Reproducibility (catalog / analysis / insights)':60s}: {' / '.join('yes' if v else 'no' for v in REPRO_GLOBAL.values())}")
print(f"{'Audit log':60s}: {chain_msg}")
print("STEP 13 PASSED · BIFLOW COMPLETED FROM A TO Z" if ok13 else "STEP 13 FAILED")
