chain_ok, chain_msg = AUDIT.verify()
raw_ok = bool(checkpoint_raw_integrity()["content_unchanged"].all()) if "checkpoint_raw_integrity" in globals() and "RAW" in globals() else None
checks7 = {
    "handoff file loaded": bool(BI_INPUT["tables"]) and bool(BI_FACTS),
    "warehouse readable": all(len(BI_WH.query(f"SELECT * FROM {qi(t)} LIMIT 1").columns) > 0 for t in BI_INPUT["tables"]),
    "valid knowledge base": not kb_errors and not duplicate_ids,
    "at least 3 computable KPIs": int(references_df["feasible"].sum()) >= 3,
    "sector decision traced": sector_source in {"LLM", "fallback"},
    "audit log intact": chain_ok,
}
if raw_ok is not None:
    checks7["raw data unchanged"] = raw_ok
ok7 = all(checks7.values())
AUDIT.log("orchestrator", "checkpoint_step7", {"passed": ok7, **checks7, "audit_chain": chain_msg, "handoff_sha256": HANDOFF_SHA256,
                                               "kb_sha256": KB_SHA256, "search_mode": SEARCH.mode}, level="INFO" if ok7 else "ERROR")
for k, v in checks7.items():
    print(f"{k:34s}: {v}")
print(f"Audit log                         : {chain_msg}")
print("STEP 7 PASSED" if ok7 else "STEP 7 FAILED")
