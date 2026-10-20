def segment_payload(fid: str) -> dict:
    f = FACTS[fid]
    card = KB_BY_ID[f["kpi"]]
    mode = decompose(card)[3]
    unit = series_meta(f["kpi"])["unit"] if card["formula"]["kind"] == "growth" else card["unit"]
    segs = [{"g": str(s["g"]), **({"share": float(s["share"])} if "share" in s else {}),
             **({"value": float(s["value"])} if "value" in s else {}), **({"n": int(s["n"])} if "n" in s else {})} for s in f["segments"]]
    overall = DASH_CANDIDATES.get(f["kpi"], {}).get("value")
    return {"id": fid, "label": f["label"], "by": f["by"][1], "mode": mode, "unit": unit, "segments": segs,
            "overall": overall if mode == "niveau" else None, "texte": f["texte"]}
 
 
shown = {LAYOUT["hero"], *LAYOUT["tuiles"], *LAYOUT["graphiques"]} - {None}
period = next((p for p in RELIABLE.values() if p), [])
TIME_TYPES_DASH = ["tendance", "variation récente", "sur un an", "anomalie", "rupture"]
SECTOR_ACCENT = {"commerce": "commerce", "télécom": "telecom", "banque": "banque", "transport": "transport"}
 
 
def trend_notes(kid: str) -> list[dict]:
    """Annotations d'une courbe : tous les signaux statistiques du KPI (tendance, rupture, anomalie, variation récente, sur un an)."""
    out = []
    for f in FACTS.values():
        if f["kpi"] != kid or f["type"] not in TIME_TYPES_DASH:
            continue
        note = {"id": f["id"], "type": f["type"], "texte": f["texte"], "valence": f["valence"], "sens": f.get("sens"),
                "windows": f.get("windows"), "periods": f.get("periods", [])}
        if f["type"] == "rupture":
            note["start"] = f["windows"][1][0]
        out.append(note)
    return out
 
 
def signal_list() -> list[dict]:
    """Chronologie des signaux : un repère par signal statistique, sur l'axe des mois fiables."""
    rows = []
    for f in sorted(FACTS.values(), key=lambda f: -f["priority"]):
        if f["type"] in TIME_TYPES_DASH and f["kpi"] in DASH_CANDIDATES and f.get("windows"):
            rows.append({"id": f["id"], "kpi": f["kpi"], "name": DASH_CANDIDATES[f["kpi"]]["name"], "type": f["type"],
                         "valence": f["valence"], "sens": f.get("sens"), "windows": f["windows"], "periods": f.get("periods", []),
                         "texte": f["texte"]})
    return rows[:24]
 
 
def heatmap_payload() -> dict | None:
    """Saisonnalité (années × mois) du premier KPI de volume ou de montant qui couvre au moins 13 mois sur 2 années."""
    order = [LAYOUT["hero"], *LAYOUT["graphiques"], *LAYOUT["tuiles"]]
    for kid in dict.fromkeys(k for k in order if k):
        c = DASH_CANDIDATES.get(kid)
        if c and c["series"] and c["unit"] in {"count", "currency", "number"} and len(c["series"]["periods"]) >= 13 \
                and len({p // 100 for p in c["series"]["periods"]}) >= 2:
            return {"kpi": kid, "name": c["name"], "unit": c["unit"], **c["series"]}
    return None
 
 
def bridge_payload() -> list[dict]:
    """Cascades : décomposition d'une variation par segment (faits de contribution), en commençant par ceux des insights."""
    cited = [f for i in INSIGHTS for f in i["faits"]]
    facts = sorted((f for f in FACTS.values() if f["type"] == "contribution" and f.get("bridge") and not is_quality_kpi(f["kpi"])),
                   key=lambda f: (f["id"] not in cited, -f["priority"]))
    span = lambda w: plabel(w[0]) if w[0] == w[1] else f"{plabel(w[0])} – {plabel(w[1])}"
    return [{"id": f["id"], "label": f["label"], "by": f["by"][1], "texte": f["texte"], "unit": f["bridge"]["unit"],
             "start": f["bridge"]["start"], "end": f["bridge"]["end"], "steps": f["bridge"]["steps"],
             "from": span(f["bridge"]["windows"][0]), "to": span(f["bridge"]["windows"][1])} for f in facts[:3]]
 
 
def quality_payload() -> dict:
    before, after = globals().get("SCORES_BEFORE"), globals().get("SCORES_AFTER")
    dims = {} if after is None else {d: {"before": float(before[d]) if before is not None and d in before else None,
                                         "after": float(after[d])} for d in after.index}
    return {"status": BI_INPUT["quality"]["status"], "dimensions": dims,
            "flagged": {f: round(100 * v, 1) for f, v in FLAGGED.items() if v is not None},
            "open_rules": len(BI_INPUT["quality"]["open_rules"])}
 
 
def insight_kpis(ins: dict) -> list[str]:
    return list(dict.fromkeys(FACTS[f]["kpi"] for f in ins["faits"] if f in FACTS))
 
 
DASHBOARD = {
    "title": LAYOUT["titre"], "subtitle": LAYOUT["sous_titre"], "domain": BI_INPUT["domain"],
    "sector": ", ".join(BI_SECTORS) or "générique", "accent": SECTOR_ACCENT.get((BI_SECTORS or ["générique"])[0], "generique"),
    "period": [plabel(period[0]), plabel(period[-1])] if period else None, "months": len(period), "run": RUN_ID,
    "meta": " · ".join(x for x in [f"Domaine : {BI_INPUT['domain']}", f"Secteur : {', '.join(BI_SECTORS) or 'générique'}",
                                   f"Période fiable : {plabel(period[0])} → {plabel(period[-1])}" if period else "",
                                   f"Run {RUN_ID}"] if x),
    "hero": LAYOUT["hero"], "tiles": LAYOUT["tuiles"], "charts": LAYOUT["graphiques"],
    "kpis": {k: {**{key: DASH_CANDIDATES[k][key] for key in ("name", "display", "unit", "status", "definition", "formula", "series",
                                                             "delta", "direction", "value")},
                 "kind": KB_BY_ID[k]["formula"]["kind"]}
             for k in DASH_CANDIDATES},
    "notes": {k: trend_notes(k) for k in DASH_CANDIDATES if DASH_CANDIDATES[k]["series"]},
    "signals": signal_list(),
    "heatmap": heatmap_payload(),
    "segments": [segment_payload(f) for f in LAYOUT["decoupages"]],
    "bridges": bridge_payload(),
    "quality": quality_payload(),
    "stats": {"kpis": len(KPI_CATALOG), "validated": int(KPI_CATALOG["status"].str.startswith("validé").sum()),
              "facts": sum(f["type"] != "valeur" for f in FACTS.values()), "insights": len(INSIGHTS),
              "insights_llm": sum(i["source"] == "LLM" for i in INSIGHTS), "series": len(SERIES)},
    "insights": [{**{k: i[k] for k in ("id", "titre", "texte", "recommandation", "type", "faits", "source")},
                  "priority": float(i.get("priorité", 0)), "kpis": insight_kpis(i)} for i in INSIGHTS],
    "facts": {f: {"texte": FACTS[f]["texte"]} for i in INSIGHTS for f in i["faits"]},
    "catalog": [{"id": r["id"], "name": r["name"], "display": fmt_value(r["value"], r["unit"]), "status": r["status"],
                 "binding": r["binding"], "reliability": r["reliability"], "formula": r["formula"], "sql": r["sql"],
                 "definition": r["definition"], "reason": BINDINGS[r["id"]].get("reason") or ""} for _, r in KPI_CATALOG.iterrows()],
    "footer": [f"Généré par BIFlow (équipe Nexora) le {utc_now()[:16].replace('T', ' ')} UTC · mise en page : {layout_source}.",
               "Chaque valeur provient d'une requête SQL vérifiée par un second calcul indépendant (étape 8) ; chaque insight cite "
               "les faits statistiques dont il reprend les chiffres (étape 9).",
               f"Empreintes : catalogue {CATALOG_SHA256[:12]} · analyse {ANALYSIS_SHA256[:12]} · journal d'audit "
               f"{AUDIT.events[-1]['hash'][:12]}."]}
 
payload = json.dumps(DASHBOARD, ensure_ascii=False, default=_json_default).replace("</", "<\\/")
DASHBOARD_HTML = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_lib.escape(LAYOUT['titre'])}</title><style>{DASHBOARD_CSS}</style></head>
<body><main id="app"></main>
<script type="application/json" id="dashboard-data">{payload}</script>
<script>{DASHBOARD_JS}</script></body></html>"""
DASHBOARD_PATH = BI_DIR / "dashboard.html"
DASHBOARD_PATH.write_text(DASHBOARD_HTML, encoding="utf-8")
DASHBOARD_SHA256 = sha256_text(DASHBOARD_HTML)
AUDIT.log("dashboard_agent", "dashboard_written", {"path": DASHBOARD_PATH, "bytes": len(DASHBOARD_HTML.encode()), "sha256": DASHBOARD_SHA256,
                                                   "tiles": len(LAYOUT["tuiles"]) + 1, "charts": len(LAYOUT["graphiques"]),
                                                   "segments": len(LAYOUT["decoupages"]), "insights": len(INSIGHTS)})
print(f"Dashboard écrit : {DASHBOARD_PATH} ({len(DASHBOARD_HTML.encode()) / 1024:.0f} Ko) · à télécharger depuis l'onglet Output")
try:
    raise ImportError("aperçu HTML désactivé en déploiement")
    display(HTML(f'<iframe srcdoc="{html_lib.escape(DASHBOARD_HTML)}" style="width:100%;height:1100px;border:1px solid #ddd;'
                 f'border-radius:8px"></iframe>'))
except ImportError:
    pass
