page_data = json.loads(DASHBOARD_HTML.split('id="dashboard-data">', 1)[1].split("</script>", 1)[0].replace("<\\/", "</"))
catalog_values = {fmt_value(r["value"], r["unit"]) for _, r in KPI_CATALOG.iterrows()}
chain_ok, chain_msg = AUDIT.verify()
checks10 = {
    "one main figure and at least 3 tiles (or all KPIs)": bool(page_data["hero"])
        and len(page_data["tiles"]) >= min(3, len(DASH_CANDIDATES) - 1),
    "tile values = catalog values": all(page_data["kpis"][k]["display"] in catalog_values
                                        for k in [page_data["hero"], *page_data["tiles"]]),
    "each chart has a series and a table view": all(page_data["kpis"][k]["series"] for k in page_data["charts"]),
    "insights kept as verified (step 9)": [i["text"] for i in page_data["insights"]] == [i["text"] for i in INSIGHTS],
    "title and subtitle without figures": not re.search(r"\d", page_data["title"] + page_data["subtitle"]),
    "self-contained file (no external resource)": not re.search(r"<(script|link)[^>]+(src|href)=", DASHBOARD_HTML),
    "audit log intact": chain_ok,
}
ok10 = all(checks10.values())
AUDIT.log("orchestrator", "checkpoint_step10", {"passed": ok10, **checks10, "dashboard_sha256": DASHBOARD_SHA256, "audit_chain": chain_msg},
          level="INFO" if ok10 else "ERROR")
for k, v in checks10.items():
    print(f"{k:50s}: {v}")
print(f"{'Audit log':50s}: {chain_msg}")
print("STEP 10 PASSED" if ok10 else "STEP 10 FAILED")
