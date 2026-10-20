page_data = json.loads(DASHBOARD_HTML.split('id="dashboard-data">', 1)[1].split("</script>", 1)[0].replace("<\\/", "</"))
catalog_values = {fmt_value(r["value"], r["unit"]) for _, r in KPI_CATALOG.iterrows()}
chain_ok, chain_msg = AUDIT.verify()
checks10 = {
    "un chiffre principal et au moins 3 tuiles (ou tous les KPI)": bool(page_data["hero"])
        and len(page_data["tiles"]) >= min(3, len(DASH_CANDIDATES) - 1),
    "valeurs des tuiles = valeurs du catalogue": all(page_data["kpis"][k]["display"] in catalog_values
                                                     for k in [page_data["hero"], *page_data["tiles"]]),
    "chaque graphique a une série et une vue tableau": all(page_data["kpis"][k]["series"] for k in page_data["charts"]),
    "insights repris tels que vérifiés (étape 9)": [i["texte"] for i in page_data["insights"]] == [i["texte"] for i in INSIGHTS],
    "titre et sous-titre sans chiffre": not re.search(r"\d", page_data["title"] + page_data["subtitle"]),
    "fichier autonome (aucune ressource externe)": not re.search(r"<(script|link)[^>]+(src|href)=", DASHBOARD_HTML),
    "journal d'audit intègre": chain_ok,
}
ok10 = all(checks10.values())
AUDIT.log("orchestrator", "checkpoint_step10", {"passed": ok10, **checks10, "dashboard_sha256": DASHBOARD_SHA256, "audit_chain": chain_msg},
          level="INFO" if ok10 else "ERROR")
for k, v in checks10.items():
    print(f"{k:50s}: {v}")
print(f"{'Journal d’audit':50s}: {chain_msg}")
print("ÉTAPE 10 VALIDÉE" if ok10 else "ÉTAPE 10 EN ÉCHEC")
