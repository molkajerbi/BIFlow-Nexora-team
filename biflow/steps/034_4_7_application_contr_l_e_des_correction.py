CHANGE_LOG, ROW_LOG = [], []


def frame_hash(df: pd.DataFrame, cols: list[str]) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(df[cols], index=True).values.tobytes()).hexdigest()


def apply_correction(cid: str, correction: str, table: str, column: str) -> dict:
    """Applies ONE approved fix, logs each touched cell / row and checks that there is no side effect."""
    df = SILVER[table]
    rows_before = len(df)
    new_df, changed, removed = transform(correction, df, table, column)
    if correction == "drop_exact_duplicates":
        ROW_LOG.append(df.loc[removed, ["_source_row_id"]].assign(correction=cid, table=table,
                                                                  operation="removed (exact duplicate)"))
        assert not new_df.duplicated(subset=list(DATA_CONTRACT[table]["columns"])).any(), "duplicates remain"
        effect = int(removed.sum())
    else:
        CHANGE_LOG.append(pd.DataFrame({"correction": cid, "table": table, "column": column,
                                        "_source_row_id": df.loc[changed, "_source_row_id"],
                                        "before": df.loc[changed, column], "after": new_df.loc[changed, column]}))
        untouched = [c for c in df.columns if c != column]
        assert frame_hash(new_df, untouched) == frame_hash(df, untouched), "side effect: another column has changed"
        effect = int(changed.sum())
    SILVER[table] = new_df
    ids = SILVER[table]["_source_row_id"]
    assert ids.is_unique and ids.notna().all(), "lineage broken"
    result = {"id": cid, "correction": correction, "table": table, "column": column,
              "rows_before": rows_before, "rows_after": len(SILVER[table]), "effect": effect}
    AUDIT.log("quality_agent", "correction_applied", result)
    return result


APPLY_ORDER = {"replace_impossible": 1, "impute_missing": 2, "cap_outliers": 3, "drop_exact_duplicates": 4}


def plan_in_order():
    """Formats first, then impossible values, missing values, extreme values (computed on complete
    data), and deduplication last (it also removes the copies revealed by the previous fixes)."""
    return sorted(CLEANING_PLAN.itertuples(), key=lambda p: (APPLY_ORDER.get(p.correction, 0), p.id))


EXECUTION = pd.DataFrame([apply_correction(p.id, p.correction, p.table, p.column)
                          for p in plan_in_order() if p.id in APPROVED],
                         columns=["id", "correction", "table", "column", "rows_before", "rows_after", "effect"])
CHANGES = pd.concat(CHANGE_LOG, ignore_index=True) if CHANGE_LOG else pd.DataFrame()
ROW_CHANGES = pd.concat(ROW_LOG, ignore_index=True) if ROW_LOG else pd.DataFrame()
print(f"{len(EXECUTION)} fix(es) applied · {len(CHANGES)} cell(s) changed · "
      f"{len(ROW_CHANGES)} row(s) removed")
EXECUTION
