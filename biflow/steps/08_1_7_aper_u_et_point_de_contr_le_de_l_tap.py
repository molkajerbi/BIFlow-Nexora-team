def checkpoint_raw_integrity() -> pd.DataFrame:
    checks = []
    for name in RAW.names:
        df = RAW._tables[name]
        checks.append({
            "table": name,
            "contenu_inchangé": RAW.fingerprint(name) == RAW_FINGERPRINTS[name],
            "lignage_unique": df["_source_row_id"].is_unique,
            "lignage_complet": df["_source_row_id"].notna().all(),
            "tout_en_texte": all(str(t) == "string" for t in df.dtypes),
        })
    return pd.DataFrame(checks).set_index("table")


checks = checkpoint_raw_integrity()
chain_ok, chain_msg = AUDIT.verify()
all_ok = bool(checks.all().all()) and chain_ok

AUDIT.log("orchestrator", "checkpoint_step1",
          {"passed": all_ok, "checks": checks.to_dict(orient="index"), "audit_chain": chain_msg},
          level="INFO" if all_ok else "ERROR")
print(f"Journal d'audit : {chain_msg}")
print("ÉTAPE 1 VALIDÉE" if all_ok else "ÉTAPE 1 EN ÉCHEC")
checks
