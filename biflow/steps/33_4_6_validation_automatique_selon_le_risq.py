MAX_ROWS_REMOVED_PCT = 50.0      # au-delà, une suppression est jugée risquée : elle n'est pas appliquée


def assess_risk(c: dict) -> list[str]:
    """Raisons pour lesquelles une correction ne doit PAS être appliquée (liste vide = risque faible)."""
    sim, reasons = c["simulation"], []
    if sim["information_loss"]:
        reasons.append("perte d'information")
    if sim["new_violations"] or not sim["target_fixed"]:
        reasons.append("la simulation ne valide pas la correction")
    if sim["rows_removed_pct"] > MAX_ROWS_REMOVED_PCT:
        reasons.append(f"{sim['rows_removed_pct']} % des lignes supprimées")
    return reasons


def review_plan() -> dict:
    """Validation 100 % automatique : les corrections sans risque sont approuvées, les autres mises de côté
    (la donnée reste signalée). Une règle BLOQUANTE est levée si une correction sans risque le permet."""
    by_candidate = {c["id"]: c for c in CANDIDATES}
    risks = {p.id: assess_risk(by_candidate[p.candidat]) for p in CLEANING_PLAN.itertuples()}
    approved = [cid for cid, r in risks.items() if not r]
    blocking = set(RULES_BEFORE.query("severity == 'blocking' and violations > 0")["rule"])
    for c in CANDIDATES:
        if c["status"] == "écarté" and c["rule"] in blocking and c["simulation"] and not assess_risk(c):
            new_id = f"C{len(CLEANING_PLAN) + 1:02d}"
            CLEANING_PLAN.loc[len(CLEANING_PLAN)] = {
                "id": new_id, "correction": c["correction"], "table": c["table"], "colonne": c["column"], "candidat": c["id"],
                "règle": c["rule"], "findings": c["profiler_findings"], "effet_simulé": c["simulation"]["rules_changed"],
                "justification": "correction sans risque qui lève une règle bloquante", "décidé_par": "politique (déblocage)"}
            approved.append(new_id)
    review = {"mode": "automatique", "reviewer": "politique de risque BIFlow", "approved": approved,
              "set_aside": {cid: r for cid, r in risks.items() if r},
              "justification": "corrections validées par simulation, valeur d'origine journalisée"}
    AUDIT.log("review_policy", "cleaning_plan_reviewed", {**review, "agent_plan_sha256": PLAN_SHA256}, level="DECISION")
    return review


REVIEW = review_plan()
APPROVED = REVIEW["approved"]
print(f"Validation automatique · approuvées : {APPROVED} · mises de côté (risque) : {REVIEW['set_aside'] or 'aucune'}")
CLEANING_PLAN[CLEANING_PLAN["id"].isin(APPROVED)][["id", "correction", "table", "colonne", "candidat", "décidé_par"]]

