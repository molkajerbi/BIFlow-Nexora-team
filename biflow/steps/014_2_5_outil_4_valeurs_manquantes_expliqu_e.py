def cramers_v(category: pd.Series, flag: pd.Series) -> float:
    """Force d'association (0 à 1) entre une variable catégorielle et un indicateur binaire."""
    observed = pd.crosstab(category, flag).to_numpy(dtype=float)
    if observed.shape[0] < 2 or observed.shape[1] < 2:
        return 0.0
    expected = observed.sum(1, keepdims=True) * observed.sum(0, keepdims=True) / observed.sum()
    chi2 = ((observed - expected) ** 2 / expected).sum()
    return float(np.sqrt(chi2 / (observed.sum() * (min(observed.shape) - 1))))


@audited(agent="profiler",
         description="Explique les valeurs manquantes : colonne catégorielle qui les explique (V de Cramér) et groupes de colonnes manquantes ensemble.")
def analyze_missingness(table: str, max_categories: int = 30, v_threshold: float = 0.3) -> ToolResult:
    df = RAW.get(table)
    spec = DATA_CONTRACT[table]["columns"]
    masks = {c: df[c].isna() for c in spec if df[c].isna().any()}
    explainers = [c for c, sem in spec.items()
                  if sem in {"category", "integer"} and 2 <= df[c].nunique() <= max_categories]

    rows, breakdowns = [], []
    for col, miss in masks.items():
        # a) colonnes manquantes en même temps (similarité de Jaccard entre masques)
        together = [o for o, m in masks.items()
                    if o != col and (miss & m).sum() / max((miss | m).sum(), 1) >= 0.95]
        # b) meilleure variable explicative
        best, best_v = None, 0.0
        for e in explainers:
            if e == col:
                continue
            known = df[e].notna()               # on n'explique pas un manque par un autre manque
            v = cramers_v(df.loc[known, e], miss[known])
            if v > best_v:
                best, best_v = e, v
        if best_v >= v_threshold:
            hypothesis = f"structurelle : dépend de {best}"
        elif together:
            hypothesis = "manquante en bloc avec " + ", ".join(together)
        else:
            hypothesis = "non expliquée (aléatoire apparent)"
        rows.append({"column": col, "missing": int(miss.sum()), "missing_pct": round(100 * miss.mean(), 2),
                     "best_explainer": best, "cramers_v": round(best_v, 3),
                     "missing_together_with": together, "hypothesis": hypothesis})
        if best and best_v >= v_threshold:
            b = (pd.DataFrame({"category": df[best], "missing": miss}).dropna(subset=["category"])
                 .groupby("category")["missing"].agg(rows="size", missing="sum"))
            b["missing_pct"] = (100 * b["missing"] / b["rows"]).round(2)
            b = b.reset_index().assign(column=col, explainer=best)
            breakdowns.append(b)

    details = pd.DataFrame(rows)
    summary = {"table": table,
               "columns": {r["column"]: {"missing_pct": r["missing_pct"], "hypothesis": r["hypothesis"]} for r in rows}}
    result = ToolResult(summary, details)
    result.breakdown = pd.concat(breakdowns, ignore_index=True) if breakdowns else pd.DataFrame()
    return result


miss = analyze_missingness(DEMO["missing"])
display(miss.details)
if len(miss.breakdown):        # détail de la colonne la mieux expliquée
    shown = DEMO["missing_column"] or miss.details.sort_values("cramers_v").iloc[-1]["column"]
    display(miss.breakdown.query("column == @shown").sort_values("rows", ascending=False))
