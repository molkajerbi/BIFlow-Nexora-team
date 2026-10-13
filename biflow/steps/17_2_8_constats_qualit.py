findings = []
for t in DATA_CONTRACT:
    p, g = TOOL_RESULTS[f"profile_columns:{t}"].summary, TOOL_RESULTS[f"check_grain:{t}"].summary
    m, a = TOOL_RESULTS[f"analyze_missingness:{t}"].summary, TOOL_RESULTS[f"detect_anomalies:{t}"].summary
    for col, n in p["columns_with_invalid"].items():
        findings.append((t, col, "validité", f"{n} valeur(s) non conforme(s) au type {DATA_CONTRACT[t]['columns'][col]}"))
    for col, n in p["columns_with_whitespace"].items():
        findings.append((t, col, "format", f"{n} valeur(s) avec espaces parasites"))
    if g["grain_is_unique"] is False:
        findings.append((t, "+".join(g["grain"]), "unicité", f"grain non unique : {g['duplicate_key_rows']} lignes concernées"))
    if g["exact_duplicate_rows"]:
        findings.append((t, "*", "unicité", f"{g['exact_duplicate_rows']} ligne(s) dupliquée(s) à l'identique"))
    for col, info in m["columns"].items():
        findings.append((t, col, "complétude", f"{info['missing_pct']} % manquants — {info['hypothesis']}"))
    for col, n in a.get("negatives", {}).items():
        findings.append((t, col, "plausibilité", f"{n} valeur(s) négative(s)"))
    for col, n in a.get("zeros", {}).items():
        findings.append((t, col, "plausibilité", f"{n} valeur(s) à zéro"))
    for col, n in a.get("iqr_extremes", {}).items():
        if n:
            findings.append((t, col, "plausibilité", f"{n} valeur(s) extrême(s) (> 3 IQR)"))
for rel_name, info in REL.summary["violated"].items():
    findings.append((rel_name.split(".")[0], rel_name, "intégrité", f"{info['orphan_rows']} ligne(s) orpheline(s) ({info['orphan_distinct']} valeurs distinctes)"))

FINDINGS = pd.DataFrame(findings, columns=["table", "colonne", "dimension", "constat"])

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
print(f"{len(FINDINGS)} constats · " + ", ".join(f"{k}: {v}" for k, v in FINDINGS["dimension"].value_counts().items()))
FINDINGS
