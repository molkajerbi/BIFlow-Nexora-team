health = []
for t in DATA_CONTRACT:
    p = profile_columns(t).summary
    g = check_grain(t).summary
    m = analyze_missingness(t).summary
    a = detect_anomalies(t).summary
    health.append({
        "table": t, "lignes": p["rows"], "colonnes": p["columns"],
        "cellules_manquantes_%": p["missing_cells_pct"],
        "colonnes_avec_manquants": len(p["columns_with_missing"]),
        "valeurs_non_conformes": sum(p["columns_with_invalid"].values()),
        "grain_unique": g["grain_is_unique"],
        "doublons_exacts": g["exact_duplicate_rows"],
        "anomalies_IF": a.get("isolation_forest_anomalies", 0),
        "extrêmes_IQR": sum(a.get("iqr_extremes", {}).values()) if a.get("iqr_extremes") else 0,
    })
REL = discover_relationships()

HEALTH = pd.DataFrame(health).set_index("table")
HEALTH
