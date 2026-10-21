@audited(agent="profiler",
         description="Profile of each column: missing values, cardinality, compliance with the declared type, statistics, frequent values.")
def profile_columns(table: str) -> ToolResult:
    df = RAW.get(table)
    spec = DATA_CONTRACT[table]["columns"]
    n = len(df)
    rows = []
    for col, sem in spec.items():
        s = df[col]
        non_null = s.dropna()
        valid = (_valid_datetime(non_null, dt_format(table, col)) if sem == "datetime"
                 else SEMANTIC_VALIDATORS[sem](non_null))
        invalid_values = non_null[~valid]
        row = {
            "column": col, "semantic_type": sem,
            "missing": int(s.isna().sum()), "missing_pct": round(100 * s.isna().mean(), 2),
            "distinct": int(non_null.nunique()),
            "distinct_pct": round(100 * non_null.nunique() / max(len(non_null), 1), 2),
            "validity_pct": round(100 * valid.mean(), 2) if len(non_null) else None,
            "invalid": int((~valid).sum()),
            "invalid_examples": invalid_values.unique()[:3].tolist(),
            "whitespace_issues": int((non_null != non_null.str.strip()).sum()),
            "top_values": non_null.value_counts().head(3).to_dict(),
            "min": None, "max": None, "mean": None, "median": None,
        }
        if sem in {"numeric", "integer", "geo"}:
            x = _to_float(non_null)
            row.update(min=float(x.min()), max=float(x.max()), mean=round(float(x.mean()), 3), median=float(x.median()))
        elif sem == "datetime":
            d = pd.to_datetime(non_null, format=dt_format(table, col), errors="coerce")
            row.update(min=str(d.min()), max=str(d.max()))
        rows.append(row)

    details = pd.DataFrame(rows).set_index("column")
    summary = {
        "table": table, "rows": n, "columns": len(spec),
        "missing_cells_pct": round(100 * df[list(spec)].isna().to_numpy().mean(), 2),
        "columns_with_missing": details.loc[details["missing"] > 0, "missing_pct"].to_dict(),
        "columns_with_invalid": details.loc[details["invalid"] > 0, "invalid"].to_dict(),
        "columns_with_whitespace": details.loc[details["whitespace_issues"] > 0, "whitespace_issues"].to_dict(),
        "constant_columns": details.index[details["distinct"] <= 1].tolist(),
    }
    return ToolResult(summary, details)


res = profile_columns(DEMO["profile"])
print(json.dumps(res.summary, indent=2, ensure_ascii=False, default=_json_default))
res.details
