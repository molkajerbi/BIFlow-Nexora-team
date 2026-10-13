MAX_ROWS_REMOVED_PCT = 50.0      # au-delà, une suppression est jugée risquée et remontée à un humain


def assess_risk(c: dict) -> list[str]:
    """Raisons pour lesquelles une correction ne doit PAS être appliquée sans un humain (liste vide = risque faible)."""
    sim, reasons = c["simulation"], []
    if sim["information_loss"]:
        reasons.append("perte d'information")
    if sim["new_violations"] or not sim["target_fixed"]:
        reasons.append("la simulation ne valide pas la correction")
    if sim["rows_removed_pct"] > MAX_ROWS_REMOVED_PCT:
        reasons.append(f"{sim['rows_removed_pct']} % des lignes supprimées")
    return reasons


def validate_human_decision(decision: dict, plan: pd.DataFrame) -> list[str]:
    """L'humain a le dernier mot : il peut refuser une correction de l'agent ou en imposer une que l'agent a écartée."""
    assert decision.get("reviewer", "").strip(), "Indiquez le nom du validateur."
    assert len(decision.get("justification", "").strip()) >= 20, "La justification doit faire au moins 20 caractères."
    unknown = set(decision.get("rejected", [])) - set(plan["id"])
    assert not unknown, f"Corrections inconnues : {unknown}"
    dismissed = {c["id"]: c for c in CANDIDATES if c["status"] == "écarté"}
    bad = set(decision.get("added", [])) - set(dismissed)
    assert not bad, f"Seuls les candidats écartés peuvent être ajoutés : {sorted(dismissed)} (reçu : {sorted(bad)})"
    for cid in decision.get("added", []):
        c = dismissed[cid]
        c["simulation"] = c["simulation"] or simulate_correction(c)
        assert c["simulation"]["target_fixed"] and not c["simulation"]["new_violations"], \
            f"{cid} : la simulation ne valide pas cette correction, elle ne peut pas être imposée"
    return [cid for cid in plan["id"] if cid not in decision.get("rejected", [])]


def review_plan(decision: dict | None, autonomy: str | None = None) -> dict:
    """Décision humaine si elle existe ; sinon politique selon le risque (mode risk_based) ; sinon attente (mode manual)."""
    autonomy = autonomy or CONFIG.autonomy
    if decision:
        approved = validate_human_decision(decision, CLEANING_PLAN)
        for cid in decision.get("added", []):
            c = next(c for c in CANDIDATES if c["id"] == cid)
            new_id = f"C{len(CLEANING_PLAN) + 1:02d}"
            CLEANING_PLAN.loc[len(CLEANING_PLAN)] = {
                "id": new_id, "correction": c["correction"], "table": c["table"], "colonne": c["column"], "candidat": cid,
                "règle": c["rule"], "findings": c["profiler_findings"], "effet_simulé": c["simulation"]["rules_changed"],
                "justification": decision["justification"], "décidé_par": "humain (contre l'avis de l'agent)"}
            approved.append(new_id)
        review = {"mode": "humain", "reviewer": decision["reviewer"], "approved": approved,
                  "rejected": decision.get("rejected", []), "added": decision.get("added", []),
                  "justification": decision["justification"]}
    elif autonomy == "risk_based":
        by_candidate = {c["id"]: c for c in CANDIDATES}
        risks = {p.id: assess_risk(by_candidate[p.candidat]) for p in CLEANING_PLAN.itertuples()}
        approved = [cid for cid, r in risks.items() if not r]
        # Sans humain, une règle BLOQUANTE ne doit pas rester sans solution : si l'agent a écarté une correction
        # sans risque qui la lève, la politique l'impose (et le trace).
        blocking = set(RULES_BEFORE.query("severity == 'blocking' and violations > 0")["rule"])
        for c in CANDIDATES:
            if c["status"] == "écarté" and c["rule"] in blocking and c["simulation"] and not assess_risk(c):
                new_id = f"C{len(CLEANING_PLAN) + 1:02d}"
                CLEANING_PLAN.loc[len(CLEANING_PLAN)] = {
                    "id": new_id, "correction": c["correction"], "table": c["table"], "colonne": c["column"], "candidat": c["id"],
                    "règle": c["rule"], "findings": c["profiler_findings"], "effet_simulé": c["simulation"]["rules_changed"],
                    "justification": "correction sans risque qui lève une règle bloquante", "décidé_par": "politique (déblocage)"}
                approved.append(new_id)
        review = {"mode": "automatique (risque faible)", "reviewer": "politique BIFlow", "approved": approved,
                  "escalated": {cid: r for cid, r in risks.items() if r},
                  "justification": "corrections du catalogue sans perte d'information, validées par simulation"}
    else:
        return {"mode": "attente humaine", "approved": None}
    AUDIT.log("human" if decision else "review_policy", "cleaning_plan_reviewed",
              {**review, "agent_plan_sha256": PLAN_SHA256}, level="DECISION")
    return review


HUMAN_DECISION = OVERRIDES.get("cleaning")          # facultatif : fichier biflow_overrides.json, clé "cleaning"
REVIEW = review_plan(HUMAN_DECISION)
assert REVIEW["approved"] is not None, "Mode manuel : ajoutez une décision humaine (biflow_overrides.json, clé 'cleaning')."
APPROVED = REVIEW["approved"]
print(f"Validation : {REVIEW['mode']} · approuvées : {APPROVED} · remontées à un humain : {REVIEW.get('escalated', {}) or 'aucune'}")
CLEANING_PLAN[CLEANING_PLAN["id"].isin(APPROVED)][["id", "correction", "table", "colonne", "candidat", "décidé_par"]]
