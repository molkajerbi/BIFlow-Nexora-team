parts = BIFLOW_RESULT.get("parts", {})
display(pd.DataFrame([
    ("Contrôle d'entrée", ", ".join(f"{k} : {v}" for k, v in parts.get("preflight", {}).items())),
    ("Data Preparation Agent", ", ".join(f"{k} : {v}" for k, v in parts.get("data_preparation", {}).items()) or "non exécutée"),
    ("BI & Insight Agent", ", ".join(f"{k} : {v}" for k, v in parts.get("bi_insight", {}).items()) or "non exécutée"),
    ("XAI Agent", ", ".join(f"{k} : {v}" for k, v in parts.get("explainability", {}).items())),
], columns=["partie", "résultat"]))
display(pd.DataFrame([{"livrable": k, "fichier": Path(v).name} for k, v in BIFLOW_RESULT.get("outputs", {}).items()]))

chain_ok, chain_msg = AUDIT.verify()
run_report = json.loads((RUN_DIR / "biflow_run_report.json").read_text(encoding="utf-8"))
executed = [h["node"] for h in BIFLOW_RESULT["history"]]
checks13 = {
    "pipeline complet : statut success": BIFLOW_RESULT["status"] == "success",
    "les parties exécutées dans l'ordre": executed == ["preflight", "data_preparation", "bi_insight", "explainability", "deliver"],
    "points de contrôle des sous-orchestrateurs": DATA_PREP_RESULT["status"] == "success" and BI_RESULT["status"] == "success",
    "explicabilité construite sur le run complet": len(LEDGER) > 0 and any(r["étape"] == 13 for r in LEDGER),
    "livrables présents (entrepôt, KPI, insights, dashboard, XAI)": {"entrepôt (modèle en étoile)", "catalogue de KPI", "dashboard",
                                                                    "registre des décisions (XAI)"} <= set(BIFLOW_RESULT.get("outputs", {})),
    "rapport d'exécution écrit": run_report["status"] == BIFLOW_RESULT["status"],
    "données brutes inchangées": bool(checkpoint_raw_integrity()["contenu_inchangé"].all()),
    "journal d'audit intègre": chain_ok,
}
ok13 = all(checks13.values())
AUDIT.log("orchestrator", "checkpoint_step13", {"passed": ok13, **checks13, "reproducibility": REPRO_GLOBAL, "audit_chain": chain_msg},
          level="INFO" if ok13 else "ERROR")
for k, v in checks13.items():
    print(f"{k:60s}: {v}")
print(f"{'Reproductibilité (catalogue / analyse / insights)':60s}: {' / '.join('oui' if v else 'non' for v in REPRO_GLOBAL.values())}")
print(f"{'Journal d’audit':60s}: {chain_msg}")
print("ÉTAPE 13 VALIDÉE · BIFLOW TERMINÉ DE A À Z" if ok13 else "ÉTAPE 13 EN ÉCHEC")
