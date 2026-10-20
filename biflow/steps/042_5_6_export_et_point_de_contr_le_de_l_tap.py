STAR = {name: WH.query(f"SELECT * FROM {name}") for name in ETL_TEMPLATES if ETL_STATUS[name] == "testée"}
for name, df in STAR.items():
    df.to_csv(etl_dir / f"{name}.csv", index=False)
tests_view.to_csv(etl_dir / "etl_tests.csv")
ETL_RUN["trace"].to_csv(etl_dir / "etl_agent_trace.csv", index=False)

etl_ok = all(s == "testée" for s in ETL_STATUS.values())
manifest = {"run_id": RUN_ID, "engine": SQL_ENGINE, "quality_status": STATUS, "templates_sha256": TEMPLATES_SHA256,
            "tables": {n: {"rows": len(d), "columns": list(d.columns), "grain": ETL_TEMPLATES[n]["grain"],
                           "built_by": ETL_RESULTS[n]["decided_by"], "tests": ETL_RESULTS[n]["tests"]} for n, d in STAR.items()},
            "fanout_check": fanout.to_dict(orient="records")}
(etl_dir / "etl_manifest.json").write_text(canonical_json(manifest), encoding="utf-8")

checks5 = checkpoint_raw_integrity()
chain_ok, chain_msg = AUDIT.verify()
ok5 = etl_ok and bool(checks5["contenu_inchangé"].all()) and chain_ok
AUDIT.log("orchestrator", "checkpoint_step5",
          {"passed": ok5, "tables_built": len(STAR), "all_tests_passed": etl_ok, "audit_chain": chain_msg},
          level="INFO" if ok5 else "ERROR")
print(f"Tables construites et testées : {len(STAR)}/{len(ETL_TEMPLATES)}")
print(f"Données brutes inchangées     : {bool(checks5['contenu_inchangé'].all())}")
print(f"Journal d'audit               : {chain_msg}")
print("ÉTAPE 5 VALIDÉE" if ok5 else "ÉTAPE 5 EN ÉCHEC")
pd.DataFrame({n: {"type": ETL_TEMPLATES[n]["type"], "lignes": len(d), "colonnes": d.shape[1],
                  "construite_par": ETL_RESULTS[n]["decided_by"]} for n, d in STAR.items()}).T
