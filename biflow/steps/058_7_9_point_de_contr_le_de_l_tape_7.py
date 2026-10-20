chain_ok, chain_msg = AUDIT.verify()
raw_ok = bool(checkpoint_raw_integrity()["contenu_inchangé"].all()) if "checkpoint_raw_integrity" in globals() and "RAW" in globals() else None
checks7 = {
    "dossier de transmission chargé": bool(BI_INPUT["tables"]) and bool(BI_FACTS),
    "entrepôt lisible": all(len(BI_WH.query(f"SELECT * FROM {qi(t)} LIMIT 1").columns) > 0 for t in BI_INPUT["tables"]),
    "base de connaissances valide": not kb_errors and not duplicate_ids,
    "au moins 3 KPI calculables": int(references_df["feasible"].sum()) >= 3,
    "décision de secteur tracée": sector_source in {"LLM", "repli"},
    "journal d'audit intègre": chain_ok,
}
if raw_ok is not None:
    checks7["données brutes inchangées"] = raw_ok
ok7 = all(checks7.values())
AUDIT.log("orchestrator", "checkpoint_step7", {"passed": ok7, **checks7, "audit_chain": chain_msg, "handoff_sha256": HANDOFF_SHA256,
                                               "kb_sha256": KB_SHA256, "search_mode": SEARCH.mode}, level="INFO" if ok7 else "ERROR")
for k, v in checks7.items():
    print(f"{k:34s}: {v}")
print(f"Journal d'audit                   : {chain_msg}")
print("ÉTAPE 7 VALIDÉE" if ok7 else "ÉTAPE 7 EN ÉCHEC")
