def screening() -> dict:
    """Quick, exhaustive pass done by the code: profile + grain of each table, relationships."""
    tables = {}
    for t, spec in DATA_CONTRACT.items():
        p, g = profile_columns(t).summary, check_grain(t).summary
        grain = spec["grain"] or []
        tables[t] = {
            "rows": p["rows"],
            "columns_with_missing": p["columns_with_missing"],
            "invalid_values": p["columns_with_invalid"],
            "grain_unique": g["grain_is_unique"],
            "exact_duplicates": g["exact_duplicate_rows"],
            "numeric_measures": [c for c, sem in spec["columns"].items() if sem in {"numeric", "integer"} and c not in grain],
        }
    rel = discover_relationships().summary
    return {"tables": tables,
            "relationships": {"violated": list(rel["violated"]), "discovered": [d["relation"] for d in rel["discovered"]]}}


TOOL_RESULTS.clear()            # les constats de l'étape 3 ne proviendront que de ce que l'agent exécute
SCREENING = screening()
REQUIRED = ({("analyze_missingness", t) for t, s in SCREENING["tables"].items() if s["columns_with_missing"]}
            | {("detect_anomalies", t) for t, s in SCREENING["tables"].items() if s["numeric_measures"]})
AUDIT.log("profiler_agent", "screening_completed",
          {"tables": len(SCREENING["tables"]), "required_investigations": sorted(f"{a}:{t}" for a, t in REQUIRED)})

print(f"Required investigations ({len(REQUIRED)}):")
for a, t in sorted(REQUIRED, key=lambda x: (x[1], x[0])):
    print(f"  - {a}({t})")
pd.DataFrame(SCREENING["tables"]).T
