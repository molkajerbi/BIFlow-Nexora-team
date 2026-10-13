ISSUES_AFTER, RULES_AFTER = run_rules(SILVER, RULES)
SCORES_AFTER = dq_scores(SILVER, RULES_AFTER, ISSUES_AFTER)

# « Signaler » : chaque ligne reçoit la liste des règles qu'elle viole (aucune valeur n'est modifiée)
flags = ISSUES_AFTER.groupby(["table", "_source_row_id"])["rule"].agg(lambda r: "|".join(sorted(set(r))))
for t in SILVER:
    table_flags = flags.xs(t, level="table") if t in flags.index.get_level_values("table") else pd.Series(dtype="string")
    SILVER[t]["_dq_flags"] = SILVER[t]["_source_row_id"].map(table_flags).astype("string")
mark_estimated_values()                                  # lignes dont une valeur a été estimée (4.1 bis)

comparison = pd.DataFrame({"avant": SCORES_BEFORE, "après": SCORES_AFTER})
comparison["gain"] = (comparison["après"] - comparison["avant"]).round(2)
rules_cmp = (RULES_BEFORE[["rule", "table", "dimension", "severity", "violations"]]
             .merge(RULES_AFTER[["rule", "violations"]], on="rule", suffixes=("_avant", "_après"))
             .query("violations_avant > 0 or violations_après > 0"))

blocking_left = int(RULES_AFTER.query("severity == 'blocking'")["violations"].sum())
STATUS = "blocked" if blocking_left else ("ready_with_warnings" if RULES_AFTER["violations"].sum() else "ready")

dq_dir = RUN_DIR / "quality"
dq_dir.mkdir(exist_ok=True)
for name, frame in {"type_report": TYPE_REPORT, "type_failures": TYPE_FAILURES, "rules_before": RULES_BEFORE,
                    "rules_after": RULES_AFTER, "issues_after": ISSUES_AFTER, "cleaning_plan": CLEANING_PLAN,
                    "other_treatments": OTHER_TREATMENTS, "cell_changes": CHANGES, "row_changes": ROW_CHANGES,
                    "dq_scores": comparison}.items():
    frame.to_csv(dq_dir / f"{name}.csv", index=name == "dq_scores")

AUDIT.log("quality_agent", "quality_completed",
          {"status": STATUS, "blocking_left": blocking_left, "scores_before": SCORES_BEFORE.to_dict(),
           "scores_after": SCORES_AFTER.to_dict(), "cells_changed": len(CHANGES), "rows_changed": len(ROW_CHANGES)})
print(f"Statut qualité : {STATUS} · violations bloquantes restantes : {blocking_left}")
display(comparison)
rules_cmp.sort_values("violations_avant", ascending=False)
