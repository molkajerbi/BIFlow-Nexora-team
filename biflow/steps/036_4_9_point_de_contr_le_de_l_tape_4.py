def lineage_ok_for(t: str) -> bool:
    """Each silver row comes from a raw row (no row is ever invented)."""
    ids = SILVER[t]["_source_row_id"]
    return bool((ids.str.startswith("added:") | ids.isin(RAW._tables[t]["_source_row_id"])).all())


def expected_rows(t: str) -> int:
    """Raw rows - removed rows + added rows (all logged)."""
    if ROW_CHANGES.empty:
        return len(RAW._tables[t])
    ops = ROW_CHANGES.loc[ROW_CHANGES["table"] == t, "operation"]
    return len(RAW._tables[t]) - int(ops.str.startswith("removed").sum()) + int(ops.str.startswith("added").sum())


checks4 = checkpoint_raw_integrity()
chain_ok, chain_msg = AUDIT.verify()
lineage_ok = all(lineage_ok_for(t) for t in SILVER)
rows_explained = all(expected_rows(t) == len(SILVER[t]) for t in SILVER)
ok4 = bool(checks4["content_unchanged"].all()) and chain_ok and lineage_ok and rows_explained and STATUS != "blocked"

AUDIT.log("orchestrator", "checkpoint_step4",
          {"passed": ok4, "status": STATUS, "raw_unchanged": bool(checks4["content_unchanged"].all()),
           "lineage_ok": lineage_ok, "row_counts_explained": rows_explained, "audit_chain": chain_msg},
          level="INFO" if ok4 else "ERROR")
print(f"Raw data unchanged                : {bool(checks4['content_unchanged'].all())}")
print(f"Lineage preserved                 : {lineage_ok}")
print(f"Row counts explained              : {rows_explained}")
print(f"Quality status                    : {STATUS}")
print(f"Audit log                         : {chain_msg}")
print("STEP 4 PASSED" if ok4 else "STEP 4 FAILED")
pd.DataFrame({t: {"raw_rows": len(RAW._tables[t]), "silver_rows": len(SILVER[t]),
                  "flagged_rows": int(SILVER[t]["_dq_flags"].notna().sum())} for t in SILVER}).T
