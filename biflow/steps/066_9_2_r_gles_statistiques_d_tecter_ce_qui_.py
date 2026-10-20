FACTS: dict[str, dict] = {}


CHANGE_LABELS = {"tendance": ("moyenne des 3 premiers mois", "moyenne des 3 derniers mois"),
                 "variation récente": ("moyenne des 3 mois précédents", "moyenne des 3 derniers mois"),
                 "sur un an": ("mêmes mois un an plus tôt", "moyenne des 3 derniers mois"),
                 "anomalie": ("valeur attendue", "valeur observée"), "rupture": ("niveau avant", "niveau après")}


def add_fact(kid: str, kind: str, text: str, numbers: list[str], priority: float, **extra) -> str:
    """Un fait : phrase écrite par le code + chiffres étiquetés (le LLM sait ce que chaque nombre représente)."""
    fid = f"F{len(FACTS) + 1:02d}"
    label = extra.pop("label", None) or (SERIES[kid]["label"] if kid in SERIES else KB_BY_ID[kid]["name"])
    if "chiffres" not in extra and kind in CHANGE_LABELS:
        names = list(CHANGE_LABELS[kind]) + ["variation relative du KPI", "écart en points du KPI"]
        extra["chiffres"] = dict(zip(names, numbers))
    if "chiffres" not in extra and kind == "valeur":
        extra["chiffres"] = {"valeur globale": numbers[0]}
    FACTS[fid] = {"id": fid, "kpi": kid, "label": label, "type": kind, "texte": text, "nombres": numbers,
                  "priority": round(float(priority), 4), "sens": None, "valence": "neutre", **extra}
    return fid


def valence(direction: str, delta: float) -> str:
    if direction == "neutral" or delta == 0:
        return "neutre"
    return "favorable" if (delta > 0) == (direction == "up") else "défavorable"


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def mann_kendall(y: np.ndarray) -> tuple[float, float]:
    """Test de tendance de Mann-Kendall : compte les paires de mois qui montent et qui descendent ; renvoie (z, p-valeur).
    Une tendance est significative si p < 0,05. Il ne suppose aucune forme de courbe et résiste aux valeurs extrêmes."""
    n = len(y)
    s = sum(np.sign(y[i + 1:] - y[i]).sum() for i in range(n - 1))
    var = n * (n - 1) * (2 * n + 5) / 18
    z = (s - np.sign(s)) / math.sqrt(var) if s else 0.0
    return float(z), float(2 * (1 - phi(abs(z))))


def theil_sen(y: np.ndarray) -> float:
    """Pente de Theil-Sen : médiane des pentes entre toutes les paires de mois (robuste aux valeurs extrêmes) ; donne le sens."""
    n = len(y)
    return float(np.median([(y[j] - y[i]) / (j - i) for i in range(n) for j in range(i + 1, n)]))


def robust_z(x: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Écart robuste : (valeur − médiane) / dispersion (MAD) des valeurs de référence ; insensible aux valeurs extrêmes."""
    med = np.median(ref)
    mad = np.median(np.abs(ref - med))
    scale = 1.4826 * mad if mad > 0 else (np.std(ref) or 1.0)
    return (x - med) / scale


def describe_change(meta: dict, a: float, b: float) -> tuple[float, list[str], str]:
    """Variation relative de a vers b, et nombres à citer (valeurs, variation, écart en points pour un pourcentage)."""
    rel = (b - a) / abs(a) if a else 0.0
    nums = [fmt_value(a, meta["unit"]), fmt_value(b, meta["unit"]), fmt_rel(rel)]
    extra = ""
    if meta["unit"] == "percent":
        nums.append(fmt_pp(b - a))
        extra = f", soit {fmt_pp(b - a)}"
    return rel, nums, extra


def analyse_series(kid: str, o: dict) -> list[str]:
    """Cinq tests déterministes sur une série mensuelle : tendance (Mann-Kendall, p < 0,05 et variation ≥ 5 %), variation
    récente (z robuste ≥ 2,5 et ≥ 5 %), comparaison sur un an (≥ 10 %), anomalie (z ≥ 3,5 face aux 4 mois voisins et ≥ 10 %),
    rupture de niveau (Welch t ≥ 4 et ≥ 10 %, retenue plutôt qu'une tendance si deux niveaux expliquent bien mieux la série).
    Chaque signal retenu devient un fait numéroté, avec sa preuve statistique."""
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
        sens = "hausse" if theil_sen(y) > 0 else "baisse"
        found.append(add_fact(kid, "tendance", f"{lab} : tendance à la {sens} sur {n} mois ({plabel(per[0])} → {plabel(per[-1])}) : "
                              f"{nums[0]} en moyenne sur les {WINDOW} premiers mois, {nums[1]} sur les {WINDOW} derniers ({nums[2]}{extra}).",
                              nums, min(abs(rel), 1) * (1 - p) * w, sens=sens, valence=valence(o["direction"], last - first),
                              test={"méthode": "Mann-Kendall (significativité) + pente de Theil-Sen", "p": round(float(p), 4),
                                    "z": round(float(z), 2), "variation": round(float(rel), 4),
                                    "seuils": "p < 0,05 et variation d'au moins 5 %, sans marche plus nette (rupture)"},
                              windows=[[int(per[0]), int(per[WINDOW - 1])], [int(per[-WINDOW]), int(per[-1])]]))
    # 2) variation récente
    if n >= 2 * WINDOW + 3:
        roll = pd.Series(y).rolling(WINDOW).mean().to_numpy()
        diffs = roll[2 * WINDOW - 1:] - roll[WINDOW - 1:-WINDOW]
        prev, recent = float(y[-2 * WINDOW:-WINDOW].mean()), float(y[-WINDOW:].mean())
        rel, nums, extra = describe_change(meta, prev, recent)
        zc = float(robust_z(np.array([diffs[-1]]), diffs[:-1])[0]) if len(diffs) > 3 else 0.0
        if abs(rel) >= 0.05 and abs(zc) >= 2.5:
            sens = "hausse" if recent > prev else "baisse"
            found.append(add_fact(kid, "variation récente", f"{lab} : {nums[1]} en moyenne de {plabel(per[-WINDOW])} à {plabel(per[-1])}, "
                                  f"contre {nums[0]} sur les {WINDOW} mois précédents ({nums[2]}{extra}) ; une variation inhabituelle "
                                  f"au regard des mois passés.", nums, min(abs(rel), 1) * min(abs(zc) / 4, 1) * w * 1.2, sens=sens,
                                  valence=valence(o["direction"], recent - prev),
                                  test={"méthode": "3 derniers mois contre les 3 précédents, comparé aux variations passées (z robuste)",
                                        "z": round(float(zc), 2), "variation": round(float(rel), 4),
                                        "seuils": "z robuste d'au moins 2,5 et variation d'au moins 5 %"},
                                  windows=[[int(per[-2 * WINDOW]), int(per[-WINDOW - 1])], [int(per[-WINDOW]), int(per[-1])]]))
    # 3) sur un an
    last_p = [int(x) for x in per[-WINDOW:]]
    year_ago = [p_ - 100 for p_ in last_p]
    if all(p_ in s.index for p_ in year_ago):
        a, b = float(s.loc[year_ago].mean()), float(s.loc[last_p].mean())
        rel, nums, extra = describe_change(meta, a, b)
        if abs(rel) >= 0.10:
            sens = "hausse" if b > a else "baisse"
            found.append(add_fact(kid, "sur un an", f"{lab} : {nums[1]} de {plabel(last_p[0])} à {plabel(last_p[-1])}, contre {nums[0]} "
                                  f"sur les mêmes mois un an plus tôt ({nums[2]}{extra}).", nums, min(abs(rel), 1) * 0.8 * w, sens=sens,
                                  valence=valence(o["direction"], b - a), windows=[[year_ago[0], year_ago[-1]], [last_p[0], last_p[-1]]],
                                  test={"méthode": "3 derniers mois contre les mêmes mois un an plus tôt", "variation": round(float(rel), 4),
                                        "seuils": "variation d'au moins 10 %"}))
    # 4) anomalies (au plus 2 par série) : écart à la médiane des 4 mois VOISINS (le mois testé exclu), rapporté à la
    #    dispersion des AUTRES écarts. Calibré sur séries de pur bruit : l'ancienne version (médiane mobile incluant le mois,
    #    échelle MAD) déclenchait une fausse alerte sur un tiers des séries de pur bruit.
    med = np.array([np.median(np.delete(y[max(0, i - 2):i + 3], i - max(0, i - 2))) for i in range(n)])
    res = y - med
    za = np.array([(res[i] - np.median(res)) / (np.std(np.delete(res, i), ddof=1) or 1.0) for i in range(n)])
    cand = [i for i in np.argsort(-np.abs(za)) if abs(za[i]) >= 3.5 and med[i] and abs(res[i] / med[i]) >= 0.10][:2]
    for i in cand:
        rel, nums, extra = describe_change(meta, float(med[i]), float(y[i]))
        sens = "hausse" if res[i] > 0 else "baisse"
        found.append(add_fact(kid, "anomalie", f"{lab} : valeur atypique en {plabel(per[i])} : {nums[1]} contre {nums[0]} attendu "
                              f"d'après les mois voisins ({nums[2]}{extra}).", nums, min(abs(rel), 1) * min(abs(za[i]) / 7, 1) * w,
                              sens=sens, valence=valence(o["direction"], float(res[i])), periods=[int(per[i])],
                              test={"méthode": "écart à la médiane des 4 mois voisins, rapporté à la dispersion des autres écarts",
                                    "z": round(float(za[i]), 2), "variation": round(float(rel), 4),
                                    "seuils": "z d'au moins 3,5 et écart d'au moins 10 %"},
                              windows=[[int(per[max(0, i - WINDOW)]), int(per[i - 1])] if i else [int(per[1]), int(per[min(n - 1, WINDOW)])],
                                       [int(per[i]), int(per[i])]]))
    # 5) rupture de niveau (calculée en 0)
    if best and best[0] >= 4:
        k = best[1]
        a, b = float(y[:k].mean()), float(y[k:].mean())
        rel, nums, extra = describe_change(meta, a, b)
        trend_fact = any(FACTS[f]["type"] == "tendance" for f in found)
        if abs(rel) >= 0.10 and not trend_fact:          # une tendance régulière n'est pas une rupture
            sens = "hausse" if b > a else "baisse"
            found.append(add_fact(kid, "rupture", f"{lab} : changement de niveau à partir de {plabel(per[k])} : {nums[0]} en moyenne avant, "
                                  f"{nums[1]} ensuite ({nums[2]}{extra}).", nums, min(abs(rel), 1) * min(best[0] / 8, 1) * w, sens=sens,
                                  valence=valence(o["direction"], b - a),
                                  test={"méthode": "meilleur point de coupure en deux niveaux (statistique de Welch)",
                                        "t": round(float(best[0]), 2), "variation": round(float(rel), 4),
                                        "seuils": "t d'au moins 4 et écart d'au moins 10 %, sans tendance régulière"},
                                  windows=[[int(per[max(0, k - WINDOW)]), int(per[k - 1])], [int(per[k]), int(per[min(n - 1, k + WINDOW - 1)])]]))
    return found


for _, row in KPI_CATALOG.iterrows():                    # valeur globale de chaque KPI : citable, non prioritaire
    add_fact(row["id"], "valeur", f"{row['name']} : {fmt_value(row['value'], row['unit'])} sur l'ensemble des données.",
             [fmt_value(row["value"], row["unit"])], 0.0)
SIGNALS = {kid: analyse_series(kid, o) for kid, o in SERIES.items()}
signal_ids = [f for fs in SIGNALS.values() for f in fs]
AUDIT.log("bi_analyst", "statistical_signals", {"signals": {f: {k: FACTS[f][k] for k in ("kpi", "type", "priority")} for f in signal_ids},
                                                "series": len(SERIES)})
print(f"{len(signal_ids)} signal(aux) statistique(s) sur {len(SERIES)} séries · "
      + ", ".join(f"{t} : {n}" for t, n in pd.Series([FACTS[f]["type"] for f in signal_ids]).value_counts().items()) if signal_ids else
      "aucun signal statistique net (séries trop courtes ou stables)")
pd.DataFrame([{"fait": f, "type": FACTS[f]["type"], "valence": FACTS[f]["valence"], "priorité": FACTS[f]["priority"], "constat": FACTS[f]["texte"]}
              for f in sorted(signal_ids, key=lambda f: -FACTS[f]["priority"])])
