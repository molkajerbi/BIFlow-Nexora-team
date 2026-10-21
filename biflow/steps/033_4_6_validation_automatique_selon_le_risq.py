MAX_ROWS_REMOVED_PCT = 50.0      # au-delà, une suppression est jugée risquée : elle n'est pas appliquée


def assess_risk(c: dict) -> list[str]:
    """Reasons why a fix must NOT be applied (empty list = low risk)."""
    sim, reasons = c["simulation"], []
    if sim["information_loss"]:
        reasons.append("information loss")
    if sim["new_violations"] or not sim["target_fixed"]:
        reasons.append("the simulation does not validate the fix")
    if sim["rows_removed_pct"] > MAX_ROWS_REMOVED_PCT:
        reasons.append(f"{sim['rows_removed_pct']}% of the rows removed")
    return reasons


def review_plan() -> dict:
    """100% automatic validation: risk-free fixes are approved, the others are set aside
    (the data stays flagged). A BLOCKING rule is lifted if a risk-free fix allows it."""
    by_candidate = {c["id"]: c for c in CANDIDATES}
    risks = {p.id: assess_risk(by_candidate[p.candidate]) for p in CLEANING_PLAN.itertuples()}
    approved = [cid for cid, r in risks.items() if not r]
    blocking = set(RULES_BEFORE.query("severity == 'blocking' and violations > 0")["rule"])
    for c in CANDIDATES:
        if c["status"] == "dismissed" and c["rule"] in blocking and c["simulation"] and not assess_risk(c):
            new_id = f"C{len(CLEANING_PLAN) + 1:02d}"
            CLEANING_PLAN.loc[len(CLEANING_PLAN)] = {
                "id": new_id, "correction": c["correction"], "table": c["table"], "column": c["column"], "candidate": c["id"],
                "rule": c["rule"], "findings": c["profiler_findings"], "simulated_effect": c["simulation"]["rules_changed"],
                "justification": "risk-free fix that lifts a blocking rule", "decided_by": "policy (unblocking)"}
            approved.append(new_id)
    review = {"mode": "automatic", "reviewer": "BIFlow risk policy", "approved": approved,
              "set_aside": {cid: r for cid, r in risks.items() if r},
              "justification": "fixes validated by simulation, original value logged"}
    AUDIT.log("review_policy", "cleaning_plan_reviewed", {**review, "agent_plan_sha256": PLAN_SHA256}, level="DECISION")
    return review


REVIEW = review_plan()
APPROVED = REVIEW["approved"]
print(f"Automatic validation · approved: {APPROVED} · set aside (risk): {REVIEW['set_aside'] or 'none'}")
CLEANING_PLAN[CLEANING_PLAN["id"].isin(APPROVED)][["id", "correction", "table", "column", "candidate", "decided_by"]]
