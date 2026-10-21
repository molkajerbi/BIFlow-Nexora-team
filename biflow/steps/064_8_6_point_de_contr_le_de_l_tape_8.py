chain_ok, chain_msg = AUDIT.verify()
checks8 = {
    "at least 3 validated KPIs": int(KPI_CATALOG["status"].str.startswith("validated").sum()) >= 3,
    "all catalog KPIs tested": bool(len(KPI_CATALOG)) and all(all(t.values()) for t in KPI_CATALOG["tests"]),
    "double calculation SQL = pandas": all(t.get("double calculation", False) for t in KPI_CATALOG["tests"]),
    "each value comes from a SQL query": all(bool(r) for r in KPI_CATALOG["sql"]),
    "catalog exported": (BI_DIR / "kpi_catalog.json").exists(),
    "audit log intact": chain_ok,
}
if "checkpoint_raw_integrity" in globals() and "RAW" in globals():
    checks8["raw data unchanged"] = bool(checkpoint_raw_integrity()["content_unchanged"].all())
ok8 = all(checks8.values())
AUDIT.log("orchestrator", "checkpoint_step8", {"passed": ok8, **checks8, "catalog_sha256": CATALOG_SHA256, "audit_chain": chain_msg},
          level="INFO" if ok8 else "ERROR")
for k, v in checks8.items():
    print(f"{k:36s}: {v}")
print(f"Audit log                           : {chain_msg}")
print("STEP 8 PASSED" if ok8 else "STEP 8 FAILED")
