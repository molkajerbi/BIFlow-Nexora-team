MAX_IMPUTE_PCT = 30.0    # une MESURE vide à plus de 30 % n'est pas estimée : on inventerait l'essentiel de la colonne
MAX_OUTLIER_PCT = 5.0    # au-delà de 5 % de valeurs « extrêmes », c'est la forme normale de la colonne, pas des aberrations
OUTLIER_K = 3.0          # limites = Q1 − 3 × IQR et Q3 + 3 × IQR (valeurs extrêmes)
MEASURES = {"numeric", "integer"}
NOT_FILLED = "Non renseigné"   # libellé explicite d'une catégorie ou d'un texte absent (pratique standard en BI)
ESTIMATING = {"replace_impossible", "cap_outliers", "impute_missing"}    # corrections qui produisent une valeur estimée
VALUE_POLICY = {"imputable": {}, "fences": {}}                          # décidé une fois, à partir des données typées


def is_missing(s: pd.Series) -> pd.Series:
    """Vraie valeur vide, ou valeur vide déguisée (NA, null, -…)."""
    missing = s.isna()
    if s.dtype == object or pd.api.types.is_string_dtype(s):
        missing |= s.astype("string").str.strip().str.lower().isin(NULL_TOKENS).fillna(False)
    return missing.astype(bool)


def protected_columns(t: str) -> set:
    """Colonnes jamais remplies : identifiants, clés et liens entre tables (inventer une clé créerait un faux lien),
    dates (inventer une date fausserait les délais), codes postaux et coordonnées GPS."""
    spec = DATA_CONTRACT[t]
    keys = {r["fk"] for r in RELATIONSHIPS if r["child"] == t} | {r["pk"] for r in RELATIONSHIPS if r["parent"] == t}
    return set(spec["grain"] or []) | keys | {c for c, s in spec["columns"].items()
                                              if s not in MEASURES | {"category", "text"}}


def missing_method(sem: str, pct: float, hypothesis: str) -> str | None:
    """Comment l'agent remplit une colonne incomplète :
    - mesure : médiane des lignes semblables, sauf si le manque est STRUCTUREL (« non applicable », ex. pas de remise
      en magasin) ou si la colonne est vide à plus de 30 % ;
    - catégorie : déduite des autres colonnes quand le manque est aléatoire, sinon « Non renseigné » ;
    - texte libre : « Non renseigné »."""
    if sem in MEASURES:
        return None if pct > MAX_IMPUTE_PCT or hypothesis.startswith("structurelle") else "median"
    if sem == "category":
        return "infer" if pct <= MAX_IMPUTE_PCT and hypothesis.startswith("non expliquée") else "label"
    return "label" if sem == "text" else None


def missing_hypothesis(t: str, c: str) -> str:
    """Cause des manques trouvée par le Profiler (outil 4) : structurelle, en bloc, ou non expliquée."""
    res = TOOL_RESULTS.get(f"analyze_missingness:{t}") or analyze_missingness(t)
    return res.summary["columns"].get(c, {}).get("hypothesis", "non expliquée (aléatoire apparent)")


def eta_squared(groups: pd.Series, y: pd.Series) -> float:
    """Part (0 à 1) des écarts d'une mesure expliquée par un groupe (ex. le prix par catégorie de produit).
    Calculée sur les rangs : quelques valeurs extrêmes ne faussent pas le résultat."""
    d = pd.DataFrame({"g": groups, "y": pd.to_numeric(y, errors="coerce").rank()}).dropna()
    if len(d) < 30 or d["g"].nunique() < 2:
        return 0.0
    total = float(((d["y"] - d["y"].mean()) ** 2).sum())
    if total == 0:
        return 0.0
    group_means = d.groupby("g")["y"].transform("mean")
    return float(((group_means - d["y"].mean()) ** 2).sum()) / total


def best_group(df: pd.DataFrame, t: str, col: str) -> str | None:
    """Catégorie (2 à 50 valeurs) qui explique le mieux la mesure : on estime alors à partir des lignes semblables."""
    spec, grain = DATA_CONTRACT[t]["columns"], set(DATA_CONTRACT[t]["grain"] or [])
    scores = {g: eta_squared(df[g].where(~is_missing(df[g])), df[col]) for g, s in spec.items()
              if s == "category" and g != col and g not in grain and 2 <= df[g].nunique() <= 50}
    best = max(scores, key=scores.get, default=None)
    return best if best and scores[best] >= 0.3 else None


def fill_values(df: pd.DataFrame, t: str, col: str) -> pd.Series:
    """Valeur estimée pour chaque ligne : médiane des lignes semblables (mesure) ou valeur la plus fréquente (catégorie)."""
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
    """Nombre de décimales de la colonne : une valeur estimée s'écrit comme les autres (ex. 18.26, pas 18.2614…)."""
    if sem == "integer":
        return 0
    sample = pd.to_numeric(values, errors="coerce").dropna().astype("float64").head(1000)
    return next((k for k in range(5) if np.allclose(sample, sample.round(k))), 4)


def category_fill(df: pd.DataFrame, t: str, col: str) -> pd.Series:
    """Catégorie estimée : d'après une autre catégorie très liée, sinon d'après la mesure qu'elle explique
    (un article à 450 € est plus probablement de l'électronique qu'un livre), sinon « Non renseigné » :
    on ne devine jamais au hasard."""
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
    """Valeurs manquantes, impossibles ou extrêmes. Renvoie (nouvelle colonne, cellules modifiées)."""
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
    """Limites basse et haute d'une mesure. Montants positifs très asymétriques : limites calculées en échelle log."""
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
    """Limites de la colonne, et limites par groupe quand une catégorie explique la mesure
    (un prix « normal » pour un livre est extrême pour un livre, pas pour un ordinateur)."""
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
    """Limites basse et haute de chaque ligne (celles de son groupe, sinon celles de la colonne)."""
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
    """Règles « manques non expliqués » et « valeurs extrêmes », appelées par build_rules (4.2)."""
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
                how = {"median": "estimé par la médiane des lignes semblables", "infer": "déduit des autres colonnes",
                       "label": f"marqué « {NOT_FILLED} »"}[method]
                rules.append(Rule(f"MIS_{t}.{c}", t, "complétude", "warning",
                                  f"{c} renseigné ({pct:.2f} % de manques, {how})",
                                  lambda S, t=t, c=c: is_missing(S[t][c])))
            policy = outlier_policy(df, t, c) if sem in MEASURES else None
            if policy:
                share = 100 * float(is_extreme(df, c, policy).mean())
                if 0 < share <= MAX_OUTLIER_PCT:
                    VALUE_POLICY["fences"][(t, c)] = policy
                    lo, hi = policy["all"]
                    where = (f"limites calculées par {policy['group']}" if policy["group"]
                             else f"au plus {hi:.2f}" if lo == float("-inf") else f"entre {lo:.2f} et {hi:.2f}")
                    rules.append(Rule(f"OUT_{t}.{c}", t, "plausibilité", "warning", f"{c} sans valeur extrême ({where})",
                                      lambda S, t=t, c=c, p=policy: is_extreme(S[t], c, p)))
    return rules


def mark_estimated_values() -> None:
    """Chaque ligne dont une valeur a été estimée porte la mention « estimé:<colonne> » dans _dq_flags."""
    if not CHANGE_LOG:
        return
    changes = pd.concat(CHANGE_LOG, ignore_index=True)
    estimated_ids = set(CLEANING_PLAN.loc[CLEANING_PLAN["correction"].isin(ESTIMATING), "id"])
    est = changes[changes["correction"].isin(estimated_ids) & (changes["after"].astype("string") != NOT_FILLED)]
    if est.empty:
        return
    marks = est.groupby(["table", "_source_row_id"])["column"].agg(lambda c: "|".join(f"estimé:{x}" for x in sorted(set(c))))
    for t in SILVER:
        if t not in marks.index.get_level_values("table"):
            continue
        m = SILVER[t]["_source_row_id"].map(marks.xs(t, level="table"))
        old = SILVER[t]["_dq_flags"]
        SILVER[t]["_dq_flags"] = old.where(m.isna(), (old.fillna("") + "|" + m).str.strip("|")).astype("string")


print("Traitement des valeurs manquantes, impossibles et extrêmes : prêt "
      f"(mesures estimées si ≤ {MAX_IMPUTE_PCT:.0f} % de manques · catégories et textes déduits ou « {NOT_FILLED} » · "
      f"extrêmes hauts au-delà de {OUTLIER_K:.0f} IQR, si ≤ {MAX_OUTLIER_PCT:.0f} % des valeurs)")

