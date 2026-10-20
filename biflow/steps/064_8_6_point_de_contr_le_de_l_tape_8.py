chain_ok, chain_msg = AUDIT.verify()
checks8 = {
    "au moins 3 KPI validés": int(KPI_CATALOG["status"].str.startswith("validé").sum()) >= 3,
    "tous les KPI du catalogue testés": bool(len(KPI_CATALOG)) and all(all(t.values()) for t in KPI_CATALOG["tests"]),
    "double calcul SQL = pandas": all(t.get("double calcul", False) for t in KPI_CATALOG["tests"]),
    "chaque valeur vient d'une requête SQL": all(bool(r) for r in KPI_CATALOG["sql"]),
    "catalogue exporté": (BI_DIR / "kpi_catalog.json").exists(),
    "journal d'audit intègre": chain_ok,
}
if "checkpoint_raw_integrity" in globals() and "RAW" in globals():
    checks8["données brutes inchangées"] = bool(checkpoint_raw_integrity()["contenu_inchangé"].all())
ok8 = all(checks8.values())
AUDIT.log("orchestrator", "checkpoint_step8", {"passed": ok8, **checks8, "catalog_sha256": CATALOG_SHA256, "audit_chain": chain_msg},
          level="INFO" if ok8 else "ERROR")
for k, v in checks8.items():
    print(f"{k:36s}: {v}")
print(f"Journal d'audit                     : {chain_msg}")
print("ÉTAPE 8 VALIDÉE" if ok8 else "ÉTAPE 8 EN ÉCHEC")
