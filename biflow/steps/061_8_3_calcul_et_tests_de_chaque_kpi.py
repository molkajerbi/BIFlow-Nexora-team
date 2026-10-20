def check_bounds(card: dict, binding: dict, v: float) -> tuple[bool, str]:
    """Bornes de plausibilité selon l'unité : un taux, une part ou un pourcentage entre 0 et 1 (une marge entre -1 et 1) ;
    un comptage entier positif ; un délai et un montant positifs (sauf bénéfice) ; une note dans l'échelle observée ;
    un taux de 0 % ou 100 % est refusé (sa condition ne distingue rien), de même qu'une part des « premiers groupes » de 100 %."""
    f, unit = card["formula"], card["unit"]
    if f["kind"] in {"rate", "top_share", "repeat_rate"}:
        if not 0 <= v <= 1 + 1e-9:
            return False, "part entre 0 et 1"
        quality = any(w["op"] == "dq_flagged" for w in conditions_of(f))      # 0 % de lignes signalées est une information
        if f["kind"] == "rate" and not quality and (v < 1e-12 or v > 1 - 1e-12):
            return False, "taux trivial (0 % ou 100 %) : la condition ne distingue rien"
        if f["kind"] == "top_share" and v > 1 - 1e-12:
            return False, "part triviale (100 %) : il y a moins de groupes que de « premiers » retenus"
        return True, "part entre 0 et 1"
    if unit == "percent" and f["kind"] != "growth":     # un pourcentage (hors évolution) reste dans [0 ; 100 %], ou [-100 ; 100 %] pour une marge
        low = -1.0 if any("profit" in card["slots"][s]["roles"] for s in card["slots"]) else 0.0
        return low - 1e-9 <= v <= 1 + 1e-9, "pourcentage entre 0 et 100 %"
    if unit == "count":
        return v >= 0 and float(v).is_integer(), "comptage entier positif"
    if unit == "days":
        return v >= 0, "délai positif"
    if unit == "currency" and not any("profit" in card["slots"][s]["roles"] for s in card["slots"]):
        return v >= 0, "montant positif"
    if unit == "score":
        r = INV.loc[next(iter(binding["slots"].values()))]
        return float(r["min"]) - 1e-9 <= v <= float(r["max"]) + 1e-9, "note dans l'échelle observée"
    return True, "pas de borne"


def evaluate_kpi(card: dict, binding: dict) -> dict:
    t0 = time.perf_counter()
    res = {"id": card["id"], "tests": {}, "error": None}
    try:
        sql = run_sql(card, binding)
        res.update({k: sql.get(k) for k in ("sql", "series_sql", "series", "growth_detail")})
        v = sql["value"]
        v = None if v is None or pd.isna(v) else float(v)
        res["value"] = v
        res["tests"]["exécution"] = v is not None and math.isfinite(v)
        pv = run_pandas(card, binding)
        res["value_pandas"] = pv
        res["tests"]["double calcul"] = v is not None and pv is not None and abs(v - pv) <= 1e-6 * max(1.0, abs(v))
        ok, rule = check_bounds(card, binding, v) if v is not None else (False, "valeur manquante")
        res["tests"]["bornes"], res["bound_rule"] = bool(ok), rule
    except Exception as exc:                              # une erreur de calcul écarte le KPI, elle n'arrête pas le pipeline
        res["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        res["tests"]["exécution"] = False
    res["passed"] = all(res["tests"].values()) and res["error"] is None
    res["seconds"] = round(time.perf_counter() - t0, 2)
    return res


RESULTS = {}
for kid, b in BINDINGS.items():
    RESULTS[kid] = evaluate_kpi(KB_BY_ID[kid], b)
    AUDIT.log("kpi_agent", "kpi_computed", {"id": kid, "value": RESULTS[kid].get("value"), "tests": RESULTS[kid]["tests"],
                                            "error": RESULTS[kid]["error"], "sql_sha256": sha256_text(RESULTS[kid].get("sql") or "")},
              level="INFO" if RESULTS[kid]["passed"] else "WARNING")
_FRAMES.clear()
gc.collect()
passed = [k for k, r in RESULTS.items() if r["passed"]]
print(f"{len(passed)}/{len(RESULTS)} KPI réussissent tous les tests · "
      f"double calcul SQL = pandas : {sum(r['tests'].get('double calcul', False) for r in RESULTS.values())}/{len(RESULTS)}")
pd.DataFrame([{"id": k, "valeur SQL": r.get("value"), "valeur pandas": r.get("value_pandas"),
               **{t: ("✓" if ok else "✗") for t, ok in r["tests"].items()}, "règle de bornes": r.get("bound_rule", "—"),
               "erreur": r["error"] or "—"}
              for k, r in RESULTS.items()]).fillna("—")
