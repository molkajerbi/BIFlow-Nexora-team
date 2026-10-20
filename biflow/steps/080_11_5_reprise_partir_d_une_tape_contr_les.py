RESUME_RESULT = run_bi_insight(start_from="dashboard")
display(bi_history_table(RESUME_RESULT))

run_report = json.loads((RUN_DIR / "bi_insight_run.json").read_text(encoding="utf-8"))
executed = [h["node"] for h in BI_RESULT["history"]]
chain_ok, chain_msg = AUDIT.verify()
checks11 = {
    "exécution complète : statut success": BI_RESULT["status"] == "success",
    "les 4 agents exécutés dans l'ordre": [n for n in executed if n in STAGE_NAMES] == STAGE_NAMES,
    "chaque étape a passé son point de contrôle": all(globals().get(s["checkpoint"]) for s in STAGES),
    "fichiers produits (dashboard, catalogue, analyse)": {"dashboard", "catalogue", "analyse"} <= set(BI_RESULT["outputs"]),
    "reprise : seul le dashboard est refait": RESUME_RESULT["status"] == "success"
        and [h["node"] for h in RESUME_RESULT["history"] if h["node"] in STAGE_NAMES] == ["dashboard_agent"],
    "rapport d'exécution écrit": run_report["status"] == "success",
    "journal d'audit intègre": chain_ok,
}
ok11 = all(checks11.values())
AUDIT.log("orchestrator", "checkpoint_step11", {"passed": ok11, **checks11, "reproducibility": REPRO, "audit_chain": chain_msg},
          level="INFO" if ok11 else "ERROR")
for k, v in checks11.items():
    print(f"{k:50s}: {v}")
print(f"{'Reproductibilité (catalogue / analyse / insights)':50s}: {' / '.join('oui' if v else 'non' for v in REPRO.values())}")
print(f"{'Journal d’audit':50s}: {chain_msg}")
print("ÉTAPE 11 VALIDÉE" if ok11 else "ÉTAPE 11 EN ÉCHEC")
