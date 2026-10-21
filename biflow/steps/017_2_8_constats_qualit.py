findings = []
for t in DATA_CONTRACT:
    p, g = TOOL_RESULTS[f"profile_columns:{t}"].summary, TOOL_RESULTS[f"check_grain:{t}"].summary
    m, a = TOOL_RESULTS[f"analyze_missingness:{t}"].summary, TOOL_RESULTS[f"detect_anomalies:{t}"].summary
    for col, n in p["columns_with_invalid"].items():
        findings.append((t, col, "validity", f"{n} value(s) not compliant with type {DATA_CONTRACT[t]['columns'][col]}"))
    for col, n in p["columns_with_whitespace"].items():
        findings.append((t, col, "format", f"{n} value(s) with stray whitespace"))
    if g["grain_is_unique"] is False:
        findings.append((t, "+".join(g["grain"]), "uniqueness", f"non-unique grain: {g['duplicate_key_rows']} rows affected"))
    if g["exact_duplicate_rows"]:
        findings.append((t, "*", "uniqueness", f"{g['exact_duplicate_rows']} exactly duplicated row(s)"))
    for col, info in m["columns"].items():
        findings.append((t, col, "completeness", f"{info['missing_pct']}% missing — {info['hypothesis']}"))
    for col, n in a.get("negatives", {}).items():
        findings.append((t, col, "plausibility", f"{n} negative value(s)"))
    for col, n in a.get("zeros", {}).items():
        findings.append((t, col, "plausibility", f"{n} zero value(s)"))
    for col, n in a.get("iqr_extremes", {}).items():
        if n:
            findings.append((t, col, "plausibility", f"{n} extreme value(s) (> 3 IQR)"))
for rel_name, info in REL.summary["violated"].items():
    findings.append((rel_name.split(".")[0], rel_name, "integrity", f"{info['orphan_rows']} orphan row(s) ({info['orphan_distinct']} distinct values)"))

FINDINGS = pd.DataFrame(findings, columns=["table", "column", "dimension", "finding"])

prof_dir = RUN_DIR / "profiling"
prof_dir.mkdir(exist_ok=True)
for key, r in TOOL_RESULTS.items():
    if r.details is not None and len(r.details):
        r.details.to_csv(prof_dir / f"{key.replace(':', '__')}.csv")
HEALTH.to_csv(prof_dir / "health_map.csv")
FINDINGS.to_csv(prof_dir / "findings.csv", index=False)
(prof_dir / "profile_summary.json").write_text(
    canonical_json({k: r.summary for k, r in TOOL_RESULTS.items()}), encoding="utf-8")

AUDIT.log("profiler", "profiling_completed",
          {"findings": len(FINDINGS), "by_dimension": FINDINGS["dimension"].value_counts().to_dict()})
print(f"{len(FINDINGS)} findings · " + ", ".join(f"{k}: {v}" for k, v in FINDINGS["dimension"].value_counts().items()))
FINDINGS
