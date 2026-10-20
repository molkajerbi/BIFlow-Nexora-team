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


def chart_notes(kid: str) -> list[dict]:
    notes = []
    for f in FACTS.values():
        if f["kpi"] != kid:
            continue
        if f["type"] == "anomalie":
            notes.append({"type": "anomalie", "periods": f.get("periods", []), "texte": f["texte"], "valence": f["valence"]})
        elif f["type"] == "rupture":
            notes.append({"type": "rupture", "start": f["windows"][1][0], "texte": f["texte"], "valence": f["valence"]})
    return notes


shown = {LAYOUT["hero"], *LAYOUT["tuiles"], *LAYOUT["graphiques"]} - {None}
period = next((p for p in RELIABLE.values() if p), [])
DASHBOARD = {
    "title": LAYOUT["titre"], "subtitle": LAYOUT["sous_titre"],
    "meta": " · ".join(x for x in [f"Domaine : {BI_INPUT['domain']}", f"Secteur : {', '.join(BI_SECTORS) or 'générique'}",
                                   f"Période fiable : {plabel(period[0])} → {plabel(period[-1])}" if period else "",
                                   f"Run {RUN_ID}"] if x),
    "hero": LAYOUT["hero"], "tiles": LAYOUT["tuiles"], "charts": LAYOUT["graphiques"],
    "kpis": {k: {key: DASH_CANDIDATES[k][key] for key in ("name", "display", "unit", "status", "definition", "formula", "series", "delta")}
             for k in shown},
    "notes": {k: chart_notes(k) for k in LAYOUT["graphiques"]},
    "segments": [segment_payload(f) for f in LAYOUT["decoupages"]],
    "insights": [{k: i[k] for k in ("id", "titre", "texte", "recommandation", "type", "faits", "source")} for i in INSIGHTS],
    "facts": {f: {"texte": FACTS[f]["texte"]} for i in INSIGHTS for f in i["faits"]},
    "catalog": [{"name": r["name"], "display": fmt_value(r["value"], r["unit"]), "status": r["status"], "binding": r["binding"],
                 "reliability": r["reliability"], "formula": r["formula"], "sql": r["sql"],
                 "reason": BINDINGS[r["id"]].get("reason") or ""} for _, r in KPI_CATALOG.iterrows()],
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
