def retrieval_precision(max_cases: int = 200) -> tuple[float, int]:
    """Précision@1 : « Pourquoi <objet> ? » retrouve-t-elle la bonne décision ? Une décision dont l'objet est partagé par
    d'autres (même nom) est comptée juste si la décision trouvée porte le même objet."""
    cases = LEDGER[:: max(1, len(LEDGER) // max_cases)][:max_cases]
    ok = 0
    for r in cases:
        hits = xai_search(f"Pourquoi {r['objet']} ?", k=1)
        ok += bool(hits) and norm(hits[0][0]["objet"]) == norm(r["objet"])
    return (ok / len(cases) if cases else 1.0), len(cases)


XAI_PRECISION, XAI_CASES = retrieval_precision()
steps_run = {1, 2, 3, 4, 5, 6} | ({7, 8, 9, 10} if globals().get("ok10") else set())
covered = set(DECISIONS["étape"])
chat = pd.DataFrame(XAI_CHAT.history)
XAI_REPORT = {
    "decisions": len(LEDGER), "rules": len(METHODS), "by_step": {int(k): int(v) for k, v in DECISIONS["étape"].value_counts().items()},
    "decided_by": DECISIONS["décidé_par"].value_counts().to_dict(), "retrieval_precision_at_1": round(XAI_PRECISION, 3),
    "retrieval_cases": XAI_CASES, "chat_turns": len(chat), "chat_llm_verified": int((chat["mode"] == "LLM (vérifié)").sum()) if len(chat) else 0,
    "chat_llm_refused": int(chat["refus_llm"].map(len).sum()) if len(chat) else 0, "ledger_errors": LEDGER_ERRORS}
(XAI_DIR / "decision_ledger.json").write_text(canonical_json(LEDGER), encoding="utf-8")
DECISIONS.assign(preuves=DECISIONS["preuves"].map(canonical_json), termes=DECISIONS["termes"].map(", ".join)).to_csv(
    XAI_DIR / "decision_ledger.csv", index=False)
(XAI_DIR / "rules.json").write_text(canonical_json(METHODS), encoding="utf-8")
(XAI_DIR / "xai_report.json").write_text(canonical_json(XAI_REPORT), encoding="utf-8")

chain_ok, chain_msg = AUDIT.verify()
checks12 = {
    "registre construit (chaque étape exécutée couverte)": steps_run <= covered,
    "chaque décision a une raison et un auteur": all(r["pourquoi"] and r["décidé_par"] for r in LEDGER),
    "règles du système lues dans le code": sum(bool(m["pourquoi"]) for m in METHODS) >= len(METHODS) - 1,
    "retrouvabilité : précision@1 ≥ 80 %": XAI_PRECISION >= 0.8,
    "chaque réponse du chat cite une source": len(chat) > 0 and bool(((chat["sources"].map(len) > 0)
                                                                      | chat["intention"].isin(["résumé", "liste"])).all()),
    "registre et conversation exportés": (XAI_DIR / "decision_ledger.json").exists() and (XAI_DIR / "chat.jsonl").exists(),
    "journal d'audit intègre": chain_ok,
}
ok12 = all(checks12.values())
AUDIT.log("orchestrator", "checkpoint_step12", {"passed": ok12, **checks12, "report": XAI_REPORT, "audit_chain": chain_msg},
          level="INFO" if ok12 else "ERROR")
for k, v in checks12.items():
    print(f"{k:55s}: {v}")
print(f"{'Précision@1 (retrouver la bonne décision)':55s}: {XAI_PRECISION:.0%} sur {XAI_CASES} questions")
print(f"{'Réponses du chat reformulées par le LLM et vérifiées':55s}: {XAI_REPORT['chat_llm_verified']} / {len(chat)} "
      f"(refus du superviseur : {XAI_REPORT['chat_llm_refused']})")
print(f"{'Journal d’audit':55s}: {chain_msg}")
print("ÉTAPE 12 VALIDÉE" if ok12 else "ÉTAPE 12 EN ÉCHEC")
