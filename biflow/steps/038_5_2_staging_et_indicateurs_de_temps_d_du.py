def date_key(s: pd.Series) -> pd.Series:
    """Integer date key YYYYMMDD (join key towards dim_date)."""
    return (s.dt.year * 10000 + s.dt.month * 100 + s.dt.day).astype("Int64")


def make_calendar(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Calendar dimension: generated (not extracted from the data) to cover the whole period, without gaps."""
    dates = pd.date_range(start.normalize(), end.normalize(), freq="D")
    return pd.DataFrame({
        "date_key": date_key(pd.Series(dates)), "date": dates, "year": dates.year, "quarter": dates.quarter,
        "month": dates.month, "month_name": dates.strftime("%B"), "year_month": dates.strftime("%Y-%m"),
        "week": dates.isocalendar().week.to_numpy(), "day_of_week": dates.dayofweek + 1,
        "is_weekend": (dates.dayofweek >= 5).astype(int)})


def share_before(df: pd.DataFrame, a: str, b: str) -> tuple[float, int]:
    """Share of rows where date a precedes (or equals) date b, and number of comparable rows."""
    both = df[a].notna() & df[b].notna()
    return (float((df.loc[both, a] <= df.loc[both, b]).mean()) if both.any() else 0.0), int(both.sum())


def derive_time_indicators(t: str, df: pd.DataFrame, min_rows: int = 30) -> tuple[pd.DataFrame, list[dict]]:
    """Business indicators derived from the dates, for any dataset:
    - the REFERENCE DATE is the one that precedes the others (e.g. order date);
    - a DURATION is computed from the reference date towards each date that follows it (e.g. delivery time);
    - an OVERRUN indicator is created when one date sometimes exceeds another (e.g. delivered after the expected date)."""
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
            info.append({"table": t, "column": name, "type": "duration (days)", "calculation": f"{d} - {ref}"})
    others = [d for d in dates if d != ref]
    for x, y in itertools.permutations(others, 2):
        share, n = share_before(df, x, y)
        if n >= min_rows and 0.5 <= share < 0.99:
            midnight = (df[y].dropna().dt.normalize() == df[y].dropna()).all()   # date sans heure : comparer les jours
            late = (df[x].dt.normalize() > df[y]) if midnight else (df[x] > df[y])
            name = f"{x}_after_{y}"
            df[name] = late.astype("Int64").where(df[x].notna() & df[y].notna())
            info.append({"table": t, "column": name, "type": "overrun (0/1)",
                         "calculation": f"{x} > {y} ({100 * (1 - share):.1f}% of the rows)"})
    return df, info


def build_staging() -> tuple[dict, pd.DataFrame]:
    """Generic staging: one stg_ table per cleaned table + date keys + time indicators + calendar."""
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
    return staging, pd.DataFrame(derived, columns=["table", "column", "type", "calculation"])


STAGING, DERIVED = build_staging()
for name, df in STAGING.items():
    WH.load(name, df)
AUDIT.log("etl_agent", "staging_loaded", {"tables": {name: len(df) for name, df in STAGING.items()},
                                          "derived_indicators": DERIVED.to_dict(orient="records")})
print(f"{len(STAGING)} staging tables · {len(DERIVED)} time indicator(s) derived from the data")
display(DERIVED)
pd.DataFrame({"rows": {n: len(d) for n, d in STAGING.items()}, "columns": {n: d.shape[1] for n, d in STAGING.items()}})
