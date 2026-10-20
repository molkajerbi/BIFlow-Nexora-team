def build_findings() -> pd.DataFrame:
    """Transforme les résultats d'outils en constats lisibles, classés par dimension de qualité (DAMA)."""
    rows = []
    for t in DATA_CONTRACT:
        p = TOOL_RESULTS[f"profile_columns:{t}"].summary
        g = TOOL_RESULTS[f"check_grain:{t}"].summary
        for col, n in p["columns_with_invalid"].items():
            rows.append((t, col, "validité", f"{n} valeur(s) non conforme(s) au type {DATA_CONTRACT[t]['columns'][col]}"))
        for col, n in p["columns_with_whitespace"].items():
            rows.append((t, col, "format", f"{n} valeur(s) avec espaces parasites"))
        if g["grain_is_unique"] is False:
            rows.append((t, "+".join(g["grain"]), "unicité", f"grain non unique : {g['duplicate_key_rows']} lignes concernées"))
        if g["exact_duplicate_rows"]:
            rows.append((t, "*", "unicité", f"{g['exact_duplicate_rows']} ligne(s) dupliquée(s) à l'identique"))
        if f"analyze_missingness:{t}" in TOOL_RESULTS:
            for col, info in TOOL_RESULTS[f"analyze_missingness:{t}"].summary["columns"].items():
                rows.append((t, col, "complétude", f"{info['missing_pct']} % manquants — {info['hypothesis']}"))
        if f"detect_anomalies:{t}" in TOOL_RESULTS:
            a = TOOL_RESULTS[f"detect_anomalies:{t}"].summary
            for col, n in a.get("negatives", {}).items():
                rows.append((t, col, "plausibilité", f"{n} valeur(s) négative(s)"))
            for col, n in a.get("zeros", {}).items():
                rows.append((t, col, "plausibilité", f"{n} valeur(s) à zéro"))
            for col, n in a.get("iqr_extremes", {}).items():
                if n:
                    rows.append((t, col, "plausibilité", f"{n} valeur(s) extrême(s) (> 3 IQR)"))
    rel = TOOL_RESULTS["discover_relationships:all"].summary
    for name, info in rel["violated"].items():
        rows.append((name.split(".")[0], name, "intégrité",
                     f"{info['orphan_rows']} ligne(s) orpheline(s) ({info['orphan_distinct']} valeurs distinctes)"))
    for d in rel["discovered"]:
        rows.append((d["relation"].split(".")[0], d["relation"], "structure", f"relation non déclarée découverte : {d['status']}"))
    df = pd.DataFrame(rows, columns=["table", "colonne", "dimension", "constat"])
    df.insert(0, "id", [f"F{i:02d}" for i in range(1, len(df) + 1)])
    return df


FINDINGS = build_findings()
AUDIT.log("profiler_agent", "findings_built",
          {"findings": len(FINDINGS), "by_dimension": FINDINGS["dimension"].value_counts().to_dict()})
print(f"{len(FINDINGS)} constats · " + ", ".join(f"{k}: {v}" for k, v in FINDINGS["dimension"].value_counts().items()))
FINDINGS
