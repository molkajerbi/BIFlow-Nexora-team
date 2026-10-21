MAX_IMPUTE_PCT = 30.0    # une MESURE vide à plus de 30 % n'est pas estimée : on inventerait l'essentiel de la colonne
MAX_OUTLIER_PCT = 5.0    # au-delà de 5 % de valeurs « extrêmes », c'est la forme normale de la colonne, pas des aberrations
OUTLIER_K = 3.0          # limites = Q1 − 3 × IQR et Q3 + 3 × IQR (valeurs extrêmes)
MEASURES = {"numeric", "integer"}
NOT_FILLED = "Not specified"   # libellé explicite d'une catégorie ou d'un texte absent (pratique standard en BI)
ESTIMATING = {"replace_impossible", "cap_outliers", "impute_missing"}    # corrections qui produisent une valeur estimée
VALUE_POLICY = {"imputable": {}, "fences": {}}                          # décidé une fois, à partir des données typées


def is_missing(s: pd.Series) -> pd.Series:
    """Truly empty value, or disguised empty value (NA, null, -…)."""
    missing = s.isna()
    if s.dtype == object or pd.api.types.is_string_dtype(s):
        missing |= s.astype("string").str.strip().str.lower().isin(NULL_TOKENS).fillna(False)
    return missing.astype(bool)


def protected_columns(t: str) -> set:
    """Columns never filled: identifiers, keys and links between tables (inventing a key would create a false link),
    dates (inventing a date would distort durations), zip codes and GPS coordinates."""
    spec = DATA_CONTRACT[t]
    keys = {r["fk"] for r in RELATIONSHIPS if r["child"] == t} | {r["pk"] for r in RELATIONSHIPS if r["parent"] == t}
    return set(spec["grain"] or []) | keys | {c for c, s in spec["columns"].items()
                                              if s not in MEASURES | {"category", "text"}}


def missing_method(sem: str, pct: float, hypothesis: str) -> str | None:
    """How the agent fills an incomplete column:
    - measure: median of similar rows, unless the gap is STRUCTURAL ("not applicable", e.g. no discount
      in store) or the column is more than 30% empty;
    - category: inferred from the other columns when the gap is random, otherwise "Not specified";
    - free text: "Not specified"."""
    if sem in MEASURES:
        return None if pct > MAX_IMPUTE_PCT or hypothesis.startswith("structural") else "median"
    if sem == "category":
        return "infer" if pct <= MAX_IMPUTE_PCT and hypothesis.startswith("unexplained") else "label"
    return "label" if sem == "text" else None


def missing_hypothesis(t: str, c: str) -> str:
    """Cause of the gaps found by the Profiler (tool 4): structural, as a block, or unexplained."""
    res = TOOL_RESULTS.get(f"analyze_missingness:{t}") or analyze_missingness(t)
    return res.summary["columns"].get(c, {}).get("hypothesis", "unexplained (apparently random)")


def eta_squared(groups: pd.Series, y: pd.Series) -> float:
    """Share (0 to 1) of the variation of a measure explained by a group (e.g. price by product category).
    Computed on ranks: a few extreme values do not distort the result."""
    d = pd.DataFrame({"g": groups, "y": pd.to_numeric(y, errors="coerce").rank()}).dropna()
    if len(d) < 30 or d["g"].nunique() < 2:
        return 0.0
    total = float(((d["y"] - d["y"].mean()) ** 2).sum())
    if total == 0:
        return 0.0
    group_means = d.groupby("g")["y"].transform("mean")
    return float(((group_means - d["y"].mean()) ** 2).sum()) / total


def best_group(df: pd.DataFrame, t: str, col: str) -> str | None:
    """Category (2 to 50 values) that best explains the measure: estimates are then made from similar rows."""
    spec, grain = DATA_CONTRACT[t]["columns"], set(DATA_CONTRACT[t]["grain"] or [])
    scores = {g: eta_squared(df[g].where(~is_missing(df[g])), df[col]) for g, s in spec.items()
              if s == "category" and g != col and g not in grain and 2 <= df[g].nunique() <= 50}
    best = max(scores, key=scores.get, default=None)
    return best if best and scores[best] >= 0.3 else None


def fill_values(df: pd.DataFrame, t: str, col: str) -> pd.Series:
    """Estimated value for each row: median of similar rows (measure) or most frequent value (category)."""
    s, sem = df[col], DATA_CONTRACT[t]["columns"][col]
    present = s[~is_missing(s)]
    if sem == "category":
        return category_fill(df, t, col)
    values = pd.to_numeric(present, errors="coerce").astype("float64")
    fill = pd.Series(float(values.median()), index=df.index)
    group = best_group(df, t, col)
    if group:
        by_group = pd.to_numeric(df[col].where(~is_missing(df[col])), errors="coerce").astype("float64") \
            .groupby(df[group]).transform("median")
        fill = by_group.fillna(fill)
    return fill.round(precision(values, sem))


def precision(values: pd.Series, sem: str) -> int:
    """Number of decimals of the column: an estimated value is written like the others (e.g. 18.26, not 18.2614…)."""
    if sem == "integer":
        return 0
    sample = pd.to_numeric(values, errors="coerce").dropna().astype("float64").head(1000)
    return next((k for k in range(5) if np.allclose(sample, sample.round(k))), 4)


def category_fill(df: pd.DataFrame, t: str, col: str) -> pd.Series:
    """Estimated category: from another strongly related category, otherwise from the measure it explains
    (a €450 item is more likely electronics than a book), otherwise "Not specified":
    we never guess at random."""
    spec, grain = DATA_CONTRACT[t]["columns"], set(DATA_CONTRACT[t]["grain"] or [])
    s = df[col]
    known = ~is_missing(s)
    fill = pd.Series(NOT_FILLED, index=df.index, dtype="object")
    # a) une autre catégorie très liée (V de Cramér ≥ 0,5) : valeur la plus fréquente de son groupe
    best, best_v = None, 0.0
    for g, sem in spec.items():
        if sem == "category" and g != col and g not in grain and 2 <= df[g].nunique() <= 50:
            both = known & ~is_missing(df[g])
            v = cramers_v(df.loc[both, g], s[both]) if both.sum() >= 30 else 0.0
            if v > best_v:
                best, best_v = g, v
    if best and best_v >= 0.5:
        modes = s[known].groupby(df.loc[known, best]).agg(lambda v: v.mode().iloc[0])
        return df[best].map(modes).astype("object").fillna(fill)
    # b) une mesure que cette catégorie explique : catégorie dont la valeur typique est la plus proche
    for m, sem in spec.items():
        if sem in MEASURES and m not in grain and eta_squared(s.where(known), df[m]) >= 0.3:
            x = pd.to_numeric(df[m], errors="coerce").astype("float64")
            z = np.log1p(x.clip(lower=0)) if bool((x.dropna() >= 0).all()) else x
            typical = z[known].groupby(s[known]).median().dropna()
            todo = ~known & z.notna()
            if len(typical) >= 2 and todo.any():
                nearest = np.abs(z[todo].to_numpy()[:, None] - typical.to_numpy()[None, :]).argmin(axis=1)
                fill = fill.copy()
                fill[todo] = typical.index.to_numpy()[nearest]
                return fill
    return fill


def as_type(s: pd.Series, t: str, col: str) -> pd.Series:
    sem = DATA_CONTRACT[t]["columns"][col]
    if sem == "integer":
        return pd.to_numeric(s, errors="coerce").round().astype("Int64")
    if sem == "numeric":
        return pd.to_numeric(s, errors="coerce").astype("Float64")
    return s


def treat_values(correction: str, df: pd.DataFrame, t: str, col: str) -> tuple[pd.Series, pd.Series]:
    """Missing, impossible or extreme values. Returns (new column, changed cells)."""
    old = df[col]
    if correction == "cap_outliers":                      # ramène la valeur extrême à la limite la plus proche
        lo, hi = bounds(df, VALUE_POLICY["fences"][(t, col)])
        x = pd.to_numeric(old, errors="coerce").astype("float64")
        target = ((x < lo) | (x > hi)).fillna(False).astype(bool)
        step = 10.0 ** -precision(x, DATA_CONTRACT[t]["columns"][col])     # arrondi vers l'intérieur des limites
        capped = x.clip(lower=np.ceil(lo / step) * step, upper=np.floor(hi / step) * step).round(10)
        return as_type(x.where(~target, capped), t, col), target
    if correction == "replace_impossible":                # valeur négative là où la règle apprise l'interdit
        target = (old < 0).fillna(False).astype(bool)
    else:                                                 # impute_missing
        target = is_missing(old)
        if VALUE_POLICY["imputable"][(t, col)]["method"] == "label":
            return old.astype("object").where(~target, NOT_FILLED).astype(old.dtype), target
    fill = fill_values(df.assign(**{col: old.mask(target)}), t, col)
    if DATA_CONTRACT[t]["columns"][col] == "category":
        return old.astype("object").where(~target, fill).astype(old.dtype), target
    return as_type(pd.to_numeric(old, errors="coerce").astype("float64").where(~target, fill), t, col), target


def fences(x: pd.Series) -> tuple[float, float] | None:
    """Lower and upper limits of a measure. Very skewed positive amounts: limits computed on a log scale."""
    x = pd.to_numeric(x, errors="coerce").dropna().astype("float64")
    if float((x >= 0).mean()) >= 0.99:
        x = x[x >= 0]                                     # les rares négatifs sont des valeurs impossibles, traitées à part
    if len(x) < 30:
        return None
    positive = bool((x >= 0).all())
    log = positive and float(x.skew()) > 1
    z = np.log1p(x) if log else x
    q1, q3 = z.quantile([.25, .75])
    if q3 - q1 == 0:
        return None
    lo, hi = q1 - OUTLIER_K * (q3 - q1), q3 + OUTLIER_K * (q3 - q1)
    if log:
        lo, hi = float(np.expm1(lo)), float(np.expm1(hi))
    # Mesure positive (prix, poids, longueur…) : une petite valeur est légitime (un article bon marché, un texte court),
    # seules les valeurs anormalement HAUTES sont des aberrations (erreur de saisie ×10, ×100…).
    return (float("-inf") if positive else float(lo)), float(hi)


def outlier_policy(df: pd.DataFrame, t: str, col: str) -> dict | None:
    """Limits of the column, and limits per group when a category explains the measure
    (a "normal" price for a computer is extreme for a book)."""
    overall = fences(df[col])
    if overall is None:
        return None
    group = best_group(df, t, col)
    by_group = {}
    if group:
        for value, part in df[col].groupby(df[group].where(~is_missing(df[group]))):
            f = fences(part)
            if f:
                by_group[value] = f
    x = pd.to_numeric(df[col], errors="coerce")
    return {"group": group if by_group else None, "by_group": by_group, "all": overall,
            "skip_negative": bool((x.dropna() >= 0).mean() >= 0.99)}    # négatifs rares = valeurs impossibles, pas extrêmes


def bounds(df: pd.DataFrame, policy: dict) -> tuple[pd.Series, pd.Series]:
    """Lower and upper limits of each row (those of its group, otherwise those of the column)."""
    lo = pd.Series(policy["all"][0], index=df.index, dtype="float64")
    hi = pd.Series(policy["all"][1], index=df.index, dtype="float64")
    if policy["group"]:
        keys = df[policy["group"]]
        lo = keys.map({k: v[0] for k, v in policy["by_group"].items()}).astype("float64").fillna(lo)
        hi = keys.map({k: v[1] for k, v in policy["by_group"].items()}).astype("float64").fillna(hi)
    return lo, hi


def is_extreme(df: pd.DataFrame, col: str, policy: dict) -> pd.Series:
    lo, hi = bounds(df, policy)
    x = pd.to_numeric(df[col], errors="coerce").astype("float64")
    extreme = (x < lo) | (x > hi)
    if policy["skip_negative"]:
        extreme &= ~(x < 0)
    return extreme.fillna(False).astype(bool)


def missing_and_outlier_rules() -> list[Rule]:
    """"Unexplained gaps" and "extreme values" rules, called by build_rules (4.2)."""
    VALUE_POLICY["imputable"].clear()
    VALUE_POLICY["fences"].clear()
    rules = []
    for t, spec in DATA_CONTRACT.items():
        df, protected = SILVER[t], protected_columns(t)
        for c, sem in spec["columns"].items():
            if c in protected:
                continue
            pct = 100 * float(is_missing(df[c]).mean())
            hypothesis = missing_hypothesis(t, c) if pct else ""
            method = missing_method(sem, pct, hypothesis) if pct else None
            if method:
                VALUE_POLICY["imputable"][(t, c)] = {"method": method, "missing_pct": round(pct, 2), "cause": hypothesis}
                how = {"median": "estimated with the median of similar rows", "infer": "inferred from the other columns",
                       "label": f'labeled "{NOT_FILLED}"'}[method]
                rules.append(Rule(f"MIS_{t}.{c}", t, "completeness", "warning",
                                  f"{c} filled in ({pct:.2f}% missing, {how})",
                                  lambda S, t=t, c=c: is_missing(S[t][c])))
            policy = outlier_policy(df, t, c) if sem in MEASURES else None
            if policy:
                share = 100 * float(is_extreme(df, c, policy).mean())
                if 0 < share <= MAX_OUTLIER_PCT:
                    VALUE_POLICY["fences"][(t, c)] = policy
                    lo, hi = policy["all"]
                    where = (f"limits computed by {policy['group']}" if policy["group"]
                             else f"at most {hi:.2f}" if lo == float("-inf") else f"between {lo:.2f} and {hi:.2f}")
                    rules.append(Rule(f"OUT_{t}.{c}", t, "plausibility", "warning", f"{c} without extreme value ({where})",
                                      lambda S, t=t, c=c, p=policy: is_extreme(S[t], c, p)))
    return rules


def mark_estimated_values() -> None:
    """Each row with an estimated value carries the mark "estimated:<column>" in _dq_flags."""
    if not CHANGE_LOG:
        return
    changes = pd.concat(CHANGE_LOG, ignore_index=True)
    estimated_ids = set(CLEANING_PLAN.loc[CLEANING_PLAN["correction"].isin(ESTIMATING), "id"])
    est = changes[changes["correction"].isin(estimated_ids) & (changes["after"].astype("string") != NOT_FILLED)]
    if est.empty:
        return
    marks = est.groupby(["table", "_source_row_id"])["column"].agg(lambda c: "|".join(f"estimated:{x}" for x in sorted(set(c))))
    for t in SILVER:
        if t not in marks.index.get_level_values("table"):
            continue
        m = SILVER[t]["_source_row_id"].map(marks.xs(t, level="table"))
        old = SILVER[t]["_dq_flags"]
        SILVER[t]["_dq_flags"] = old.where(m.isna(), (old.fillna("") + "|" + m).str.strip("|")).astype("string")


print("Treatment of missing, impossible and extreme values: ready "
      f'(measures estimated if ≤ {MAX_IMPUTE_PCT:.0f}% missing · categories and texts inferred or "{NOT_FILLED}" · '
      f"high extremes beyond {OUTLIER_K:.0f} IQR, if ≤ {MAX_OUTLIER_PCT:.0f}% of the values)")
