def dq_scores(S: dict, rules_summary: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    """Score 0-100 par dimension = moyenne, sur les tables, de la part de lignes sans violation."""
    rows = []
    for t, spec in DATA_CONTRACT.items():
        n = len(S[t])
        rows.append({"table": t, "dimension": "complétude",
                     "score": 100 * float(S[t][list(spec["columns"])].notna().to_numpy().mean())})
        for dim in rules_summary.loc[rules_summary["table"] == t, "dimension"].unique():
            bad = issues.loc[(issues["table"] == t) & (issues["dimension"] == dim), "_source_row_id"].nunique()
            rows.append({"table": t, "dimension": dim, "score": 100 * (1 - bad / n) if n else 100.0})
    per_table = pd.DataFrame(rows)
    return per_table.groupby("dimension")["score"].mean().round(2)


SCORES_BEFORE = dq_scores(SILVER, RULES_BEFORE, ISSUES_BEFORE)
AUDIT.log("quality_agent", "dq_score_before", SCORES_BEFORE.to_dict())
SCORES_BEFORE.to_frame("score_avant")
