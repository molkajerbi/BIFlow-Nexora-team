import copy

SEMANTIC_TYPES = {"id", "category", "datetime", "numeric", "integer", "text", "zip", "geo"}


def validate_contract(contract: dict, relationships: list[dict]) -> None:
    """The contract itself is checked: an inconsistency is detected before any data is read."""
    for name, spec in contract.items():
        unknown = set(spec["columns"].values()) - SEMANTIC_TYPES
        assert not unknown, f"{name}: unknown semantic types {unknown}"
        if spec["grain"]:
            missing = set(spec["grain"]) - set(spec["columns"])
            assert not missing, f"{name}: grain columns missing from the contract {missing}"
    for r in relationships:
        assert r["fk"] in contract[r["child"]]["columns"], f"Unknown FK: {r}"
        assert r["pk"] in contract[r["parent"]]["columns"], f"Unknown PK: {r}"


INFERRED = infer_contract(CONFIG.data_dir)
AUDIT.log("contract_agent", "contract_inferred",
          {"tables": len(INFERRED["contract"]), "relationships": INFERRED["relationship_details"],
           "roles": INFERRED["roles"], "confidence_pct": INFERRED["confidence"], "points_to_check": INFERRED["checks"],
           "contract_sha256": sha256_text(canonical_json(INFERRED["contract"]))})

DATA_CONTRACT = copy.deepcopy(INFERRED["contract"])            # le contrat inféré, relu ensuite par l'agent Domaine
RELATIONSHIPS = list(INFERRED["relationships"])
TABLE_ROLES = dict(INFERRED["roles"])
DATETIME_FORMATS = {k: f for k, f in INFERRED["formats"].items()
                    if DATA_CONTRACT[k.split(".", 1)[0]]["columns"].get(k.split(".", 1)[1]) == "datetime"}
NUMBER_FORMATS = INFERRED["number_formats"]                    # écriture des nombres : « 1 234,5 », « 12 € », « 15 % »…
DATETIME_FORMAT = pd.Series(list(DATETIME_FORMATS.values()) or ["%Y-%m-%d %H:%M:%S"]).mode()[0]
ID_PATTERN, ZIP_PATTERN = r"\S+", r"[0-9A-Za-z\- ]{2,12}"
DOMAIN = "tabular data (domain identified in step 3)"   # déduit ensuite par l'agent Domaine
_stats = INFERRED["stats"]
FACT_TABLES = sorted([t for t, r in TABLE_ROLES.items() if r == "fact"], key=lambda t: -_stats[t]["rows"])
CORE_TABLES = (FACT_TABLES or sorted(DATA_CONTRACT, key=lambda t: -_stats[t]["rows"]))[:3]
DEMO = {"profile": CORE_TABLES[0], "grain": list(DATA_CONTRACT)[:3], "missing_column": None,
        "missing": max(_stats, key=lambda t: _stats[t]["missing_columns"]),
        "anomalies": max(_stats, key=lambda t: _stats[t]["numeric_columns"])}

validate_contract(DATA_CONTRACT, RELATIONSHIPS)
(RUN_DIR / "data_contract.json").write_text(canonical_json(
    {"tables": DATA_CONTRACT, "relationships": RELATIONSHIPS, "roles": TABLE_ROLES, "datetime_formats": DATETIME_FORMATS,
     "number_formats": NUMBER_FORMATS, "confidence_pct": INFERRED["confidence"], "points_to_check": INFERRED["checks"]}),
    encoding="utf-8")
AUDIT.log("orchestrator", "contract_registered",
          {"tables": len(DATA_CONTRACT), "relationships": len(RELATIONSHIPS),
           "contract_sha256": sha256_text(canonical_json(DATA_CONTRACT))})

print(f"{len(DATA_CONTRACT)} tables · {len(RELATIONSHIPS)} relationships · inference confidence: {INFERRED['confidence']}%")
print("Points to check:", INFERRED["checks"] or "none")
if INFERRED["relationship_details"]:
    display(pd.DataFrame(INFERRED["relationship_details"]))
pd.DataFrame([
    {"table": t, "file": s["file"], "grain": " + ".join(s["grain"]) if s["grain"] else "— (none)",
     "columns": len(s["columns"]), "role": TABLE_ROLES[t],
     "types": ", ".join(f"{k}:{v}" for k, v in pd.Series(s["columns"]).value_counts().items())}
    for t, s in DATA_CONTRACT.items()
])
