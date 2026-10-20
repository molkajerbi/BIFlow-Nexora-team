def date_key(s: pd.Series) -> pd.Series:
    """Clé de date entière AAAAMMJJ (clé de jointure vers dim_date)."""
    return (s.dt.year * 10000 + s.dt.month * 100 + s.dt.day).astype("Int64")


def make_calendar(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Dimension calendrier : générée (pas extraite des données) pour couvrir toute la période, sans trou."""
    dates = pd.date_range(start.normalize(), end.normalize(), freq="D")
    return pd.DataFrame({
        "date_key": date_key(pd.Series(dates)), "date": dates, "year": dates.year, "quarter": dates.quarter,
        "month": dates.month, "month_name": dates.strftime("%B"), "year_month": dates.strftime("%Y-%m"),
        "week": dates.isocalendar().week.to_numpy(), "day_of_week": dates.dayofweek + 1,
        "is_weekend": (dates.dayofweek >= 5).astype(int)})


def share_before(df: pd.DataFrame, a: str, b: str) -> tuple[float, int]:
    """Part des lignes où la date a précède (ou égale) la date b, et nombre de lignes comparables."""
    both = df[a].notna() & df[b].notna()
    return (float((df.loc[both, a] <= df.loc[both, b]).mean()) if both.any() else 0.0), int(both.sum())


def derive_time_indicators(t: str, df: pd.DataFrame, min_rows: int = 30) -> tuple[pd.DataFrame, list[dict]]:
    """Indicateurs métier déduits des dates, pour n'importe quel dataset :
    - la DATE DE RÉFÉRENCE est celle qui précède les autres (ex. date de commande) ;
    - un DÉLAI est calculé de la date de référence vers chaque date qui la suit (ex. délai de livraison) ;
    - un indicateur de DÉPASSEMENT est créé quand une date dépasse parfois une autre (ex. livrée après la date prévue)."""
    dates = [c for c, s in DATA_CONTRACT[t]["columns"].items() if s == "datetime" and df[c].notna().mean() >= 0.5]
    info = []
    if len(dates) < 2:
        return df, info
    score = {d: sum(share_before(df, d, o)[0] >= 0.95 for o in dates if o != d) for d in dates}
    ref = max(dates, key=lambda d: (score[d], df[d].notna().mean()))
    if score[ref] == 0:
        return df, info
    for d in dates:
        share, n = share_before(df, ref, d)
        if d != ref and n >= min_rows and share >= 0.95:
            name = f"{ref}_to_{d}_days"
            df[name] = ((df[d] - df[ref]).dt.total_seconds() / 86400).round(2)
            info.append({"table": t, "colonne": name, "type": "délai (jours)", "calcul": f"{d} - {ref}"})
    others = [d for d in dates if d != ref]
    for x, y in itertools.permutations(others, 2):
        share, n = share_before(df, x, y)
        if n >= min_rows and 0.5 <= share < 0.99:
            midnight = (df[y].dropna().dt.normalize() == df[y].dropna()).all()   # date sans heure : comparer les jours
            late = (df[x].dt.normalize() > df[y]) if midnight else (df[x] > df[y])
            name = f"{x}_after_{y}"
            df[name] = late.astype("Int64").where(df[x].notna() & df[y].notna())
            info.append({"table": t, "colonne": name, "type": "dépassement (0/1)",
                         "calcul": f"{x} > {y} ({100 * (1 - share):.1f} % des lignes)"})
    return df, info


def build_staging() -> tuple[dict, pd.DataFrame]:
    """Staging générique : une table stg_ par table nettoyée + clés de date + indicateurs de temps + calendrier."""
    staging, derived, all_dates = {}, [], []
    for t, spec in DATA_CONTRACT.items():
        df = SILVER[t].copy()
        df, info = derive_time_indicators(t, df)
        derived += info
        for c, sem in spec["columns"].items():
            if sem == "datetime":
                df[f"{c}_date_key"] = date_key(df[c])
                all_dates.append(df[c].dropna())
        staging[f"stg_{t}"] = df
    dates = pd.concat(all_dates) if all_dates else pd.Series(dtype="datetime64[ns]")
    if len(dates):
        staging["stg_dim_date"] = make_calendar(dates.min(), dates.max())
    return staging, pd.DataFrame(derived, columns=["table", "colonne", "type", "calcul"])


STAGING, DERIVED = build_staging()
for name, df in STAGING.items():
    WH.load(name, df)
AUDIT.log("etl_agent", "staging_loaded", {"tables": {name: len(df) for name, df in STAGING.items()},
                                          "derived_indicators": DERIVED.to_dict(orient="records")})
print(f"{len(STAGING)} tables de staging · {len(DERIVED)} indicateur(s) de temps déduit(s) des données")
display(DERIVED)
pd.DataFrame({"lignes": {n: len(d) for n, d in STAGING.items()}, "colonnes": {n: d.shape[1] for n, d in STAGING.items()}})
