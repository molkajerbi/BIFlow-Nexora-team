def retrieval_precision(max_cases: int = 200) -> tuple[float, int]:
    """Precision@1: does "Why <object>?" find the right decision? A decision whose object is shared by
    others (same name) counts as correct if the decision found has the same object."""
    cases = LEDGER[:: max(1, len(LEDGER) // max_cases)][:max_cases]
    ok = 0
    for r in cases:
        hits = xai_search(f"Why {r['object']}?", k=1)
        ok += bool(hits) and norm(hits[0][0]["object"]) == norm(r["object"])
    return (ok / len(cases) if cases else 1.0), len(cases)


XAI_PRECISION, XAI_CASES = retrieval_precision()
steps_run = {1, 2, 3, 4, 5, 6} | ({7, 8, 9, 10} if globals().get("ok10") else set())
covered = set(DECISIONS["step"])
chat = pd.DataFrame(XAI_CHAT.history)
XAI_REPORT = {
    "decisions": len(LEDGER), "rules": len(METHODS), "by_step": {int(k): int(v) for k, v in DECISIONS["step"].value_counts().items()},
    "decided_by": DECISIONS["decided_by"].value_counts().to_dict(), "retrieval_precision_at_1": round(XAI_PRECISION, 3),
    "retrieval_cases": XAI_CASES, "chat_turns": len(chat), "chat_llm_verified": int((chat["mode"] == "LLM (verified)").sum()) if len(chat) else 0,
    "chat_llm_refused": int(chat["llm_rejections"].map(len).sum()) if len(chat) else 0, "ledger_errors": LEDGER_ERRORS}
(XAI_DIR / "decision_ledger.json").write_text(canonical_json(LEDGER), encoding="utf-8")
DECISIONS.assign(evidence=DECISIONS["evidence"].map(canonical_json), terms=DECISIONS["terms"].map(", ".join)).to_csv(
    XAI_DIR / "decision_ledger.csv", index=False)
(XAI_DIR / "rules.json").write_text(canonical_json(METHODS), encoding="utf-8")
(XAI_DIR / "xai_report.json").write_text(canonical_json(XAI_REPORT), encoding="utf-8")

chain_ok, chain_msg = AUDIT.verify()
checks12 = {
    "ledger built (each executed step covered)": steps_run <= covered,
    "each decision has a reason and an author": all(r["why"] and r["decided_by"] for r in LEDGER),
    "system rules read from the code": sum(bool(m["why"]) for m in METHODS) >= len(METHODS) - 1,
    "retrievability: precision@1 ≥ 80%": XAI_PRECISION >= 0.8,
    "each chat answer cites a source": len(chat) > 0 and bool(((chat["sources"].map(len) > 0)
                                                               | chat["intent"].isin(["summary", "list"])).all()),
    "ledger and conversation exported": (XAI_DIR / "decision_ledger.json").exists() and (XAI_DIR / "chat.jsonl").exists(),
    "audit log intact": chain_ok,
}
ok12 = all(checks12.values())
AUDIT.log("orchestrator", "checkpoint_step12", {"passed": ok12, **checks12, "report": XAI_REPORT, "audit_chain": chain_msg},
          level="INFO" if ok12 else "ERROR")
for k, v in checks12.items():
    print(f"{k:55s}: {v}")
print(f"{'Precision@1 (finding the right decision)':55s}: {XAI_PRECISION:.0%} over {XAI_CASES} questions")
print(f"{'Chat answers rephrased by the LLM and verified':55s}: {XAI_REPORT['chat_llm_verified']} / {len(chat)} "
      f"(supervisor rejections: {XAI_REPORT['chat_llm_refused']})")
print(f"{'Audit log':55s}: {chain_msg}")
print("STEP 12 PASSED" if ok12 else "STEP 12 FAILED")
