def checkpoint_raw_integrity() -> pd.DataFrame:
    checks = []
    for name in RAW.names:
        df = RAW._tables[name]
        checks.append({
            "table": name,
            "content_unchanged": RAW.fingerprint(name) == RAW_FINGERPRINTS[name],
            "lineage_unique": df["_source_row_id"].is_unique,
            "lineage_complete": df["_source_row_id"].notna().all(),
            "all_text": all(str(t) == "string" for t in df.dtypes),
        })
    return pd.DataFrame(checks).set_index("table")


checks = checkpoint_raw_integrity()
chain_ok, chain_msg = AUDIT.verify()
all_ok = bool(checks.all().all()) and chain_ok

AUDIT.log("orchestrator", "checkpoint_step1",
          {"passed": all_ok, "checks": checks.to_dict(orient="index"), "audit_chain": chain_msg},
          level="INFO" if all_ok else "ERROR")
print(f"Audit log: {chain_msg}")
print("STEP 1 PASSED" if all_ok else "STEP 1 FAILED")
checks
