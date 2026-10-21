def build_findings() -> pd.DataFrame:
    """Turns tool results into readable findings, classified by quality dimension (DAMA)."""
    rows = []
    for t in DATA_CONTRACT:
        p = TOOL_RESULTS[f"profile_columns:{t}"].summary
        g = TOOL_RESULTS[f"check_grain:{t}"].summary
        for col, n in p["columns_with_invalid"].items():
            rows.append((t, col, "validity", f"{n} value(s) not compliant with type {DATA_CONTRACT[t]['columns'][col]}"))
        for col, n in p["columns_with_whitespace"].items():
            rows.append((t, col, "format", f"{n} value(s) with stray whitespace"))
        if g["grain_is_unique"] is False:
            rows.append((t, "+".join(g["grain"]), "uniqueness", f"non-unique grain: {g['duplicate_key_rows']} rows affected"))
        if g["exact_duplicate_rows"]:
            rows.append((t, "*", "uniqueness", f"{g['exact_duplicate_rows']} exactly duplicated row(s)"))
        if f"analyze_missingness:{t}" in TOOL_RESULTS:
            for col, info in TOOL_RESULTS[f"analyze_missingness:{t}"].summary["columns"].items():
                rows.append((t, col, "completeness", f"{info['missing_pct']}% missing — {info['hypothesis']}"))
        if f"detect_anomalies:{t}" in TOOL_RESULTS:
            a = TOOL_RESULTS[f"detect_anomalies:{t}"].summary
            for col, n in a.get("negatives", {}).items():
                rows.append((t, col, "plausibility", f"{n} negative value(s)"))
            for col, n in a.get("zeros", {}).items():
                rows.append((t, col, "plausibility", f"{n} zero value(s)"))
            for col, n in a.get("iqr_extremes", {}).items():
                if n:
                    rows.append((t, col, "plausibility", f"{n} extreme value(s) (> 3 IQR)"))
    rel = TOOL_RESULTS["discover_relationships:all"].summary
    for name, info in rel["violated"].items():
        rows.append((name.split(".")[0], name, "integrity",
                     f"{info['orphan_rows']} orphan row(s) ({info['orphan_distinct']} distinct values)"))
    for d in rel["discovered"]:
        rows.append((d["relation"].split(".")[0], d["relation"], "structure", f"undeclared relationship discovered: {d['status']}"))
    df = pd.DataFrame(rows, columns=["table", "column", "dimension", "finding"])
    df.insert(0, "id", [f"F{i:02d}" for i in range(1, len(df) + 1)])
    return df


FINDINGS = build_findings()
AUDIT.log("profiler_agent", "findings_built",
          {"findings": len(FINDINGS), "by_dimension": FINDINGS["dimension"].value_counts().to_dict()})
print(f"{len(FINDINGS)} findings · " + ", ".join(f"{k}: {v}" for k, v in FINDINGS["dimension"].value_counts().items()))
FINDINGS
