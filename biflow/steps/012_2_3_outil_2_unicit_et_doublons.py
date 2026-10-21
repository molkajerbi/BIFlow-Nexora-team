@audited(agent="profiler",
         description="Checks that the declared grain is unique, counts exact duplicates and discovers candidate keys.")
def check_grain(table: str) -> ToolResult:
    df = RAW.get(table)
    cols = list(DATA_CONTRACT[table]["columns"])
    grain = DATA_CONTRACT[table]["grain"]

    exact_dup = df.duplicated(subset=cols, keep="first")          # lignes identiques hors _source_row_id
    key_like = [c for c in cols if DATA_CONTRACT[table]["columns"][c] in {"id", "zip", "category"}]
    candidate_keys = [c for c in key_like if df[c].notna().all() and df[c].is_unique]

    summary = {"table": table, "grain": grain, "rows": len(df),
               "exact_duplicate_rows": int(exact_dup.sum()), "candidate_keys": candidate_keys}
    details = None
    if grain:
        null_key = df[grain].isna().any(axis=1)
        dup_key = df.duplicated(subset=grain, keep=False) & ~null_key
        summary.update({
            "null_key_rows": int(null_key.sum()),
            "duplicate_key_rows": int(dup_key.sum()),
            "duplicated_keys": int(df.loc[dup_key, grain].drop_duplicates().shape[0]),
            "grain_is_unique": bool(not null_key.any() and not dup_key.any()),
        })
        details = df.loc[dup_key, ["_source_row_id", *cols]].sort_values(grain).head(20)
    else:
        summary["grain_is_unique"] = None    # pas de grain déclaré
        details = df.loc[exact_dup, ["_source_row_id", *cols]].head(20)
    return ToolResult(summary, details)


for t in DEMO["grain"]:
    print(json.dumps(check_grain(t).summary, ensure_ascii=False, default=_json_default))
