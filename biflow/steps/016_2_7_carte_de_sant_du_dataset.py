health = []
for t in DATA_CONTRACT:
    p = profile_columns(t).summary
    g = check_grain(t).summary
    m = analyze_missingness(t).summary
    a = detect_anomalies(t).summary
    health.append({
        "table": t, "rows": p["rows"], "columns": p["columns"],
        "missing_cells_%": p["missing_cells_pct"],
        "columns_with_missing": len(p["columns_with_missing"]),
        "invalid_values": sum(p["columns_with_invalid"].values()),
        "unique_grain": g["grain_is_unique"],
        "exact_duplicates": g["exact_duplicate_rows"],
        "IF_anomalies": a.get("isolation_forest_anomalies", 0),
        "IQR_extremes": sum(a.get("iqr_extremes", {}).values()) if a.get("iqr_extremes") else 0,
    })
REL = discover_relationships()

HEALTH = pd.DataFrame(health).set_index("table")
HEALTH
