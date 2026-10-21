FACTS: dict[str, dict] = {}


CHANGE_LABELS = {"trend": ("mean of the first 3 months", "mean of the last 3 months"),
                 "recent change": ("mean of the previous 3 months", "mean of the last 3 months"),
                 "year over year": ("same months one year earlier", "mean of the last 3 months"),
                 "anomaly": ("expected value", "observed value"), "level shift": ("level before", "level after")}


def add_fact(kid: str, kind: str, text: str, numbers: list[str], priority: float, **extra) -> str:
    """A fact: sentence written by the code + labelled figures (the LLM knows what each number represents)."""
    fid = f"F{len(FACTS) + 1:02d}"
    label = extra.pop("label", None) or (SERIES[kid]["label"] if kid in SERIES else KB_BY_ID[kid]["name"])
    if "figures" not in extra and kind in CHANGE_LABELS:
        names = list(CHANGE_LABELS[kind]) + ["relative change of the KPI", "gap in points of the KPI"]
        extra["figures"] = dict(zip(names, numbers))
    if "figures" not in extra and kind == "value":
        extra["figures"] = {"overall value": numbers[0]}
    FACTS[fid] = {"id": fid, "kpi": kid, "label": label, "type": kind, "text": text, "numbers": numbers,
                  "priority": round(float(priority), 4), "direction": None, "valence": "neutral", **extra}
    return fid


def valence(direction: str, delta: float) -> str:
    if direction == "neutral" or delta == 0:
        return "neutral"
    return "favorable" if (delta > 0) == (direction == "up") else "unfavorable"


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def mann_kendall(y: np.ndarray) -> tuple[float, float]:
    """Mann-Kendall trend test: counts the pairs of months going up and going down; returns (z, p-value).
    A trend is significant if p < 0.05. It assumes no curve shape and resists extreme values."""
    n = len(y)
    s = sum(np.sign(y[i + 1:] - y[i]).sum() for i in range(n - 1))
    var = n * (n - 1) * (2 * n + 5) / 18
    z = (s - np.sign(s)) / math.sqrt(var) if s else 0.0
    return float(z), float(2 * (1 - phi(abs(z))))


def theil_sen(y: np.ndarray) -> float:
    """Theil-Sen slope: median of the slopes between all pairs of months (robust to extreme values); gives the direction."""
    n = len(y)
    return float(np.median([(y[j] - y[i]) / (j - i) for i in range(n) for j in range(i + 1, n)]))


def robust_z(x: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Robust deviation: (value − median) / spread (MAD) of the reference values; insensitive to extreme values."""
    med = np.median(ref)
    mad = np.median(np.abs(ref - med))
    scale = 1.4826 * mad if mad > 0 else (np.std(ref) or 1.0)
    return (x - med) / scale


def describe_change(meta: dict, a: float, b: float) -> tuple[float, list[str], str]:
    """Relative change from a to b, and numbers to cite (values, change, gap in points for a percentage)."""
    rel = (b - a) / abs(a) if a else 0.0
    nums = [fmt_value(a, meta["unit"]), fmt_value(b, meta["unit"]), fmt_rel(rel)]
    extra = ""
    if meta["unit"] == "percent":
        nums.append(fmt_pp(b - a))
        extra = f", i.e. {fmt_pp(b - a)}"
    return rel, nums, extra


def analyse_series(kid: str, o: dict) -> list[str]:
    """Five deterministic tests on a monthly series: trend (Mann-Kendall, p < 0.05 and change ≥ 5%), recent
    change (robust z ≥ 2.5 and ≥ 5%), year-over-year comparison (≥ 10%), anomaly (z ≥ 3.5 against the 4 neighbouring months and ≥ 10%),
    level shift (Welch t ≥ 4 and ≥ 10%, preferred over a trend if two levels explain the series much better).
    Each kept signal becomes a numbered fact, with its statistical evidence."""
    s, meta, w, found = o["s"], o, o["weight"], []
    y, per = s.to_numpy(), s.index.to_numpy()
    n, lab, fmt = len(y), o["label"], (lambda v: fmt_value(v, o["unit"]))
    # 0) meilleur changement de niveau (test de Welch à chaque mois de coupure) et comparaison avec une droite :
    #    une marche nette est une RUPTURE, pas une tendance (le test de tendance réagit aussi à une marche)
    best = None
    for k in range(WINDOW, n - WINDOW + 1):
        a_, b_ = y[:k], y[k:]
        se = math.sqrt(a_.var(ddof=1) / len(a_) + b_.var(ddof=1) / len(b_)) or 1e-12
        best = max(best or (0, 0), (abs(b_.mean() - a_.mean()) / se, k))
    step_better = False
    if best and best[0] >= 4:
        k = best[1]
        sse_step = float(((y[:k] - y[:k].mean()) ** 2).sum() + ((y[k:] - y[k:].mean()) ** 2).sum())
        x = np.arange(n)
        sse_line = float(((y - np.polyval(np.polyfit(x, y, 1), x)) ** 2).sum())
        step_better = sse_step <= 0.5 * sse_line
    # 1) tendance
    z, p = mann_kendall(y)
    first, last = float(y[:WINDOW].mean()), float(y[-WINDOW:].mean())
    rel, nums, extra = describe_change(meta, first, last)
    if p < 0.05 and abs(rel) >= 0.05 and not step_better:
        sens = "increase" if theil_sen(y) > 0 else "decrease"
        found.append(add_fact(kid, "trend", f"{lab}: {'upward' if sens == 'increase' else 'downward'} trend over {n} months ({plabel(per[0])} → {plabel(per[-1])}): "
                              f"{nums[0]} on average over the first {WINDOW} months, {nums[1]} over the last {WINDOW} ({nums[2]}{extra}).",
                              nums, min(abs(rel), 1) * (1 - p) * w, direction=sens, valence=valence(o["direction"], last - first),
                              test={"method": "Mann-Kendall (significance) + Theil-Sen slope", "p": round(float(p), 4),
                                    "z": round(float(z), 2), "change": round(float(rel), 4),
                                    "thresholds": "p < 0.05 and a change of at least 5%, with no clearer step (level shift)"},
                              windows=[[int(per[0]), int(per[WINDOW - 1])], [int(per[-WINDOW]), int(per[-1])]]))
    # 2) variation récente
    if n >= 2 * WINDOW + 3:
        roll = pd.Series(y).rolling(WINDOW).mean().to_numpy()
        diffs = roll[2 * WINDOW - 1:] - roll[WINDOW - 1:-WINDOW]
        prev, recent = float(y[-2 * WINDOW:-WINDOW].mean()), float(y[-WINDOW:].mean())
        rel, nums, extra = describe_change(meta, prev, recent)
        zc = float(robust_z(np.array([diffs[-1]]), diffs[:-1])[0]) if len(diffs) > 3 else 0.0
        if abs(rel) >= 0.05 and abs(zc) >= 2.5:
            sens = "increase" if recent > prev else "decrease"
            found.append(add_fact(kid, "recent change", f"{lab}: {nums[1]} on average from {plabel(per[-WINDOW])} to {plabel(per[-1])}, "
                                  f"against {nums[0]} over the previous {WINDOW} months ({nums[2]}{extra}); an unusual change "
                                  f"compared with past months.", nums, min(abs(rel), 1) * min(abs(zc) / 4, 1) * w * 1.2, direction=sens,
                                  valence=valence(o["direction"], recent - prev),
                                  test={"method": "last 3 months against the previous 3, compared with past changes (robust z)",
                                        "z": round(float(zc), 2), "change": round(float(rel), 4),
                                        "thresholds": "robust z of at least 2.5 and a change of at least 5%"},
                                  windows=[[int(per[-2 * WINDOW]), int(per[-WINDOW - 1])], [int(per[-WINDOW]), int(per[-1])]]))
    # 3) sur un an
    last_p = [int(x) for x in per[-WINDOW:]]
    year_ago = [p_ - 100 for p_ in last_p]
    if all(p_ in s.index for p_ in year_ago):
        a, b = float(s.loc[year_ago].mean()), float(s.loc[last_p].mean())
        rel, nums, extra = describe_change(meta, a, b)
        if abs(rel) >= 0.10:
            sens = "increase" if b > a else "decrease"
            found.append(add_fact(kid, "year over year", f"{lab}: {nums[1]} from {plabel(last_p[0])} to {plabel(last_p[-1])}, against {nums[0]} "
                                  f"over the same months one year earlier ({nums[2]}{extra}).", nums, min(abs(rel), 1) * 0.8 * w, direction=sens,
                                  valence=valence(o["direction"], b - a), windows=[[year_ago[0], year_ago[-1]], [last_p[0], last_p[-1]]],
                                  test={"method": "last 3 months against the same months one year earlier", "change": round(float(rel), 4),
                                        "thresholds": "a change of at least 10%"}))
    # 4) anomalies (au plus 2 par série) : écart à la médiane des 4 mois VOISINS (le mois testé exclu), rapporté à la
    #    dispersion des AUTRES écarts. Calibré sur séries de pur bruit : l'ancienne version (médiane mobile incluant le mois,
    #    échelle MAD) déclenchait une fausse alerte sur un tiers des séries de pur bruit.
    med = np.array([np.median(np.delete(y[max(0, i - 2):i + 3], i - max(0, i - 2))) for i in range(n)])
    res = y - med
    za = np.array([(res[i] - np.median(res)) / (np.std(np.delete(res, i), ddof=1) or 1.0) for i in range(n)])
    cand = [i for i in np.argsort(-np.abs(za)) if abs(za[i]) >= 3.5 and med[i] and abs(res[i] / med[i]) >= 0.10][:2]
    for i in cand:
        rel, nums, extra = describe_change(meta, float(med[i]), float(y[i]))
        sens = "increase" if res[i] > 0 else "decrease"
        found.append(add_fact(kid, "anomaly", f"{lab}: atypical value in {plabel(per[i])}: {nums[1]} against {nums[0]} expected "
                              f"from the neighbouring months ({nums[2]}{extra}).", nums, min(abs(rel), 1) * min(abs(za[i]) / 7, 1) * w,
                              direction=sens, valence=valence(o["direction"], float(res[i])), periods=[int(per[i])],
                              test={"method": "gap to the median of the 4 neighbouring months, relative to the spread of the other gaps",
                                    "z": round(float(za[i]), 2), "change": round(float(rel), 4),
                                    "thresholds": "z of at least 3.5 and a gap of at least 10%"},
                              windows=[[int(per[max(0, i - WINDOW)]), int(per[i - 1])] if i else [int(per[1]), int(per[min(n - 1, WINDOW)])],
                                       [int(per[i]), int(per[i])]]))
    # 5) rupture de niveau (calculée en 0)
    if best and best[0] >= 4:
        k = best[1]
        a, b = float(y[:k].mean()), float(y[k:].mean())
        rel, nums, extra = describe_change(meta, a, b)
        trend_fact = any(FACTS[f]["type"] == "trend" for f in found)
        if abs(rel) >= 0.10 and not trend_fact:          # une tendance régulière n'est pas une rupture
            sens = "increase" if b > a else "decrease"
            found.append(add_fact(kid, "level shift", f"{lab}: change of level from {plabel(per[k])}: {nums[0]} on average before, "
                                  f"{nums[1]} afterwards ({nums[2]}{extra}).", nums, min(abs(rel), 1) * min(best[0] / 8, 1) * w, direction=sens,
                                  valence=valence(o["direction"], b - a),
                                  test={"method": "best cut point into two levels (Welch statistic)",
                                        "t": round(float(best[0]), 2), "change": round(float(rel), 4),
                                        "thresholds": "t of at least 4 and a gap of at least 10%, with no steady trend"},
                                  windows=[[int(per[max(0, k - WINDOW)]), int(per[k - 1])], [int(per[k]), int(per[min(n - 1, k + WINDOW - 1)])]]))
    return found


for _, row in KPI_CATALOG.iterrows():                    # valeur globale de chaque KPI : citable, non prioritaire
    add_fact(row["id"], "value", f"{row['name']}: {fmt_value(row['value'], row['unit'])} over the whole dataset.",
             [fmt_value(row["value"], row["unit"])], 0.0)
SIGNALS = {kid: analyse_series(kid, o) for kid, o in SERIES.items()}
signal_ids = [f for fs in SIGNALS.values() for f in fs]
AUDIT.log("bi_analyst", "statistical_signals", {"signals": {f: {k: FACTS[f][k] for k in ("kpi", "type", "priority")} for f in signal_ids},
                                                "series": len(SERIES)})
print(f"{len(signal_ids)} statistical signal(s) over {len(SERIES)} series · "
      + ", ".join(f"{t}: {n}" for t, n in pd.Series([FACTS[f]["type"] for f in signal_ids]).value_counts().items()) if signal_ids else
      "no clear statistical signal (series too short or stable)")
pd.DataFrame([{"fact": f, "type": FACTS[f]["type"], "valence": FACTS[f]["valence"], "priority": FACTS[f]["priority"], "finding": FACTS[f]["text"]}
              for f in sorted(signal_ids, key=lambda f: -FACTS[f]["priority"])])
