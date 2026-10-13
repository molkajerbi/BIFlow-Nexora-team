from sklearn.ensemble import IsolationForest


@audited(agent="profiler",
         description="Détecte les valeurs anormales : règle IQR par colonne et Isolation Forest multivarié, avec la variable responsable de chaque anomalie.")
def detect_anomalies(table: str, contamination: float = 0.01, top_n: int = 10) -> ToolResult:
    df = RAW.get(table)
    spec, grain = DATA_CONTRACT[table]["columns"], DATA_CONTRACT[table]["grain"] or []
    num_cols = [c for c, sem in spec.items() if sem in {"numeric", "integer"} and c not in grain]
    if not num_cols:
        return ToolResult({"table": table, "numeric_columns": [], "note": "aucune mesure numérique"})

    X = pd.DataFrame({c: _to_float(df[c]) for c in num_cols})

    # a) Règle IQR, colonne par colonne
    iqr_rows = []
    for c in num_cols:
        x = X[c].dropna()
        q1, q3 = x.quantile([.25, .75])
        iqr = q3 - q1
        iqr_rows.append({"column": c, "q1": q1, "median": x.median(), "q3": q3,
                         "outliers_1.5iqr": int(((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)).sum()),
                         "extremes_3iqr": int(((x < q1 - 3 * iqr) | (x > q3 + 3 * iqr)).sum()),
                         "zeros": int((x == 0).sum()), "negatives": int((x < 0).sum()),
                         "min": x.min(), "max": x.max()})
    iqr_df = pd.DataFrame(iqr_rows).set_index("column")
    summary = {"table": table, "numeric_columns": num_cols,
               "iqr_extremes": iqr_df["extremes_3iqr"].to_dict(),
               "zeros": iqr_df.loc[iqr_df["zeros"] > 0, "zeros"].to_dict(),
               "negatives": iqr_df.loc[iqr_df["negatives"] > 0, "negatives"].to_dict()}

    # b) Isolation Forest multivarié (au moins 2 mesures) + fusion avec la règle IQR
    lo = iqr_df["q1"] - 3 * (iqr_df["q3"] - iqr_df["q1"])
    hi = iqr_df["q3"] + 3 * (iqr_df["q3"] - iqr_df["q1"])
    iqr_flag = ((X < lo) | (X > hi)).any(axis=1)

    Z = np.sign(X) * np.log1p(X.abs())              # log : réduit l'asymétrie des montants
    Z = Z.fillna(Z.median())
    # explication : variable la plus éloignée de sa médiane (z-score robuste)
    mad = (Z - Z.median()).abs().median().replace(0, np.nan) * 1.4826
    robust_z = ((Z - Z.median()) / mad).abs().fillna(0)
    reason = robust_z.idxmax(axis=1)

    if len(num_cols) >= 2:
        model = IsolationForest(n_estimators=200, contamination=contamination, random_state=CONFIG.random_seed)
        if_flag = pd.Series(model.fit_predict(Z) == -1, index=df.index)
        score = pd.Series(-model.score_samples(Z), index=df.index)     # plus grand = plus anormal
    else:
        if_flag = pd.Series(False, index=df.index)
        score = robust_z.max(axis=1)

    method = np.select([if_flag & iqr_flag, if_flag, iqr_flag], ["IF + IQR", "Isolation Forest", "IQR extrême"], "")
    flagged = if_flag | iqr_flag
    details = (df.loc[flagged, ["_source_row_id"]]
               .assign(method=method[flagged], score=score[flagged].round(3),
                       robust_z=robust_z.max(axis=1)[flagged].round(1), main_reason=reason[flagged])
               .join(X.loc[flagged])
               .sort_values(["robust_z", "score"], ascending=False)
               .head(top_n))
    summary.update({"isolation_forest_anomalies": int(if_flag.sum()),
                    "iqr_extreme_rows": int(iqr_flag.sum()),
                    "flagged_by_both": int((if_flag & iqr_flag).sum()),
                    "anomaly_main_reasons": reason[flagged].value_counts().to_dict()})
    result = ToolResult(summary, details)
    result.iqr = iqr_df
    return result


ano = detect_anomalies(DEMO["anomalies"])
if hasattr(ano, "iqr"):
    display(ano.iqr)
else:
    print("Aucune mesure numérique dans ce dataset : pas d'anomalie numérique à rechercher.")
ano.details
