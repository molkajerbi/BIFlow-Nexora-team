import html as html_lib

MAX_TILES, MAX_CHARTS, MAX_SEGMENTS = 7, 6, 4


def reliable_series(kid: str) -> pd.Series | None:
    """Série mensuelle d'un KPI restreinte aux mois fiables (9.1), même si 9.1 l'a jugée redondante pour l'analyse.
    Un KPI d'évolution (« growth ») n'a pas de courbe propre : sa série en 9.1 est celle du volume sous-jacent."""
    if KB_BY_ID[kid]["formula"]["kind"] == "growth":
        return None
    if kid in SERIES:
        return SERIES[kid]["s"]
    if kid not in KPI_SERIES:
        return None
    keep = set(RELIABLE.get(BINDINGS[kid]["fact"], []))
    s = KPI_SERIES[kid].assign(period=lambda d: d["period"].astype(int))
    s = s[s["period"].isin(keep)].dropna(subset=["v"]).set_index("period")["v"].astype(float).sort_index()
    return s if len(s) >= MIN_POINTS else None


def recent_change(kid: str, s: pd.Series | None) -> dict | None:
    if s is None or len(s) < 2 * WINDOW:
        return None
    card, unit = KB_BY_ID[kid], KB_BY_ID[kid]["unit"]
    a, b = float(s.iloc[-2 * WINDOW:-WINDOW].mean()), float(s.iloc[-WINDOW:].mean())
    if not a and unit != "percent":
        return None
    text = fmt_pp(b - a) if unit == "percent" else fmt_rel((b - a) / abs(a))
    good = None if card["direction"] == "neutral" or a == b else (b > a) == (card["direction"] == "up")
    return {"text": text, "up": b > a, "good": good,
            "label": f"{plabel(int(s.index[-WINDOW]))} – {plabel(int(s.index[-1]))} vs 3 mois précédents"}


def signal_score(kid: str) -> float:
    return max([f["priority"] for f in FACTS.values() if f["kpi"] == kid and f["type"] != "valeur"] or [0.0])


DASH_CANDIDATES = {}
for _, row in KPI_CATALOG.iterrows():
    kid = row["id"]
    if is_quality_kpi(kid):
        continue
    s = reliable_series(kid)
    DASH_CANDIDATES[kid] = {
        "id": kid, "name": row["name"], "value": float(row["value"]), "display": fmt_value(row["value"], row["unit"]),
        "unit": row["unit"], "direction": row["direction"], "status": row["status"], "weight": round(float(kpi_weight(row)), 3),
        "signal": round(signal_score(kid), 3), "definition": row["definition"], "formula": row["formula"],
        "series": None if s is None else {"periods": [int(p) for p in s.index], "values": [float(v) for v in s.to_numpy()]},
        "delta": recent_change(kid, s)}

SEGMENT_CANDIDATES = {f["id"]: f for f in FACTS.values()
                      if f["type"] == "segment" and f.get("segments") and not is_quality_kpi(f["kpi"])}
CHART_CANDIDATES = [k for k, c in DASH_CANDIDATES.items() if c["series"]]
print(f"{len(DASH_CANDIDATES)} KPI candidats · {len(CHART_CANDIDATES)} avec une série mensuelle · "
      f"{len(SEGMENT_CANDIDATES)} découpages · {len(INSIGHTS)} insights")
pd.DataFrame([{"id": c["id"], "KPI": c["name"], "valeur": c["display"], "évolution récente": (c["delta"] or {}).get("text", "—"),
               "poids": c["weight"], "signal": c["signal"], "série": "oui" if c["series"] else "non"}
              for c in sorted(DASH_CANDIDATES.values(), key=lambda c: -(c["weight"] + c["signal"]))])
