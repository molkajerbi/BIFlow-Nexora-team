def segment_payload(fid: str) -> dict:
    f = FACTS[fid]
    card = KB_BY_ID[f["kpi"]]
    mode = decompose(card)[3]
    unit = series_meta(f["kpi"])["unit"] if card["formula"]["kind"] == "growth" else card["unit"]
    segs = [{"g": str(s["g"]), **({"share": float(s["share"])} if "share" in s else {}),
             **({"value": float(s["value"])} if "value" in s else {}), **({"n": int(s["n"])} if "n" in s else {})} for s in f["segments"]]
    overall = DASH_CANDIDATES.get(f["kpi"], {}).get("value")
    return {"id": fid, "label": f["label"], "by": f["by"][1], "mode": mode, "unit": unit, "segments": segs,
            "overall": overall if mode == "level" else None, "text": f["text"]}


shown = {LAYOUT["hero"], *LAYOUT["tiles"], *LAYOUT["charts"]} - {None}
period = next((p for p in RELIABLE.values() if p), [])
TIME_TYPES_DASH = ["trend", "recent change", "year over year", "anomaly", "level shift"]
SECTOR_ACCENT = {"commerce": "commerce", "telecom": "telecom", "banking": "banking", "transport": "transport"}


def trend_notes(kid: str) -> list[dict]:
    """Annotations of a curve: all the KPI's statistical signals (trend, level shift, anomaly, recent change, year over year)."""
    out = []
    for f in FACTS.values():
        if f["kpi"] != kid or f["type"] not in TIME_TYPES_DASH:
            continue
        note = {"id": f["id"], "type": f["type"], "text": f["text"], "valence": f["valence"], "direction": f.get("direction"),
                "windows": f.get("windows"), "periods": f.get("periods", [])}
        if f["type"] == "level shift":
            note["start"] = f["windows"][1][0]
        out.append(note)
    return out


def signal_list() -> list[dict]:
    """Signal timeline: one marker per statistical signal, on the axis of the reliable months."""
    rows = []
    for f in sorted(FACTS.values(), key=lambda f: -f["priority"]):
        if f["type"] in TIME_TYPES_DASH and f["kpi"] in DASH_CANDIDATES and f.get("windows"):
            rows.append({"id": f["id"], "kpi": f["kpi"], "name": DASH_CANDIDATES[f["kpi"]]["name"], "type": f["type"],
                         "valence": f["valence"], "direction": f.get("direction"), "windows": f["windows"], "periods": f.get("periods", []),
                         "text": f["text"]})
    return rows[:24]


def heatmap_payload() -> dict | None:
    """Seasonality (years × months) of the first volume or amount KPI covering at least 13 months over 2 years."""
    order = [LAYOUT["hero"], *LAYOUT["charts"], *LAYOUT["tiles"]]
    for kid in dict.fromkeys(k for k in order if k):
        c = DASH_CANDIDATES.get(kid)
        if c and c["series"] and c["unit"] in {"count", "currency", "number"} and len(c["series"]["periods"]) >= 13 \
                and len({p // 100 for p in c["series"]["periods"]}) >= 2:
            return {"kpi": kid, "name": c["name"], "unit": c["unit"], **c["series"]}
    return None


def bridge_payload() -> list[dict]:
    """Waterfalls: decomposition of a change by segment (contribution facts), starting with those of the insights."""
    cited = [f for i in INSIGHTS for f in i["facts"]]
    facts = sorted((f for f in FACTS.values() if f["type"] == "contribution" and f.get("bridge") and not is_quality_kpi(f["kpi"])),
                   key=lambda f: (f["id"] not in cited, -f["priority"]))
    span = lambda w: plabel(w[0]) if w[0] == w[1] else f"{plabel(w[0])} – {plabel(w[1])}"
    return [{"id": f["id"], "label": f["label"], "by": f["by"][1], "text": f["text"], "unit": f["bridge"]["unit"],
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
    return list(dict.fromkeys(FACTS[f]["kpi"] for f in ins["facts"] if f in FACTS))


DASHBOARD = {
    "title": LAYOUT["title"], "subtitle": LAYOUT["subtitle"], "domain": BI_INPUT["domain"],
    "sector": ", ".join(BI_SECTORS) or "generic", "accent": SECTOR_ACCENT.get((BI_SECTORS or ["generic"])[0], "generic"),
    "period": [plabel(period[0]), plabel(period[-1])] if period else None, "months": len(period), "run": RUN_ID,
    "meta": " · ".join(x for x in [f"Domain: {BI_INPUT['domain']}", f"Sector: {', '.join(BI_SECTORS) or 'generic'}",
                                   f"Reliable period: {plabel(period[0])} → {plabel(period[-1])}" if period else "",
                                   f"Run {RUN_ID}"] if x),
    "hero": LAYOUT["hero"], "tiles": LAYOUT["tiles"], "charts": LAYOUT["charts"],
    "kpis": {k: {**{key: DASH_CANDIDATES[k][key] for key in ("name", "display", "unit", "status", "definition", "formula", "series",
                                                             "delta", "direction", "value")},
                 "kind": KB_BY_ID[k]["formula"]["kind"]}
             for k in DASH_CANDIDATES},
    "notes": {k: trend_notes(k) for k in DASH_CANDIDATES if DASH_CANDIDATES[k]["series"]},
    "signals": signal_list(),
    "heatmap": heatmap_payload(),
    "segments": [segment_payload(f) for f in LAYOUT["breakdowns"]],
    "bridges": bridge_payload(),
    "quality": quality_payload(),
    "stats": {"kpis": len(KPI_CATALOG), "validated": int(KPI_CATALOG["status"].str.startswith("validated").sum()),
              "facts": sum(f["type"] != "value" for f in FACTS.values()), "insights": len(INSIGHTS),
              "insights_llm": sum(i["source"] == "LLM" for i in INSIGHTS), "series": len(SERIES)},
    "insights": [{**{k: i[k] for k in ("id", "title", "text", "recommendation", "type", "facts", "source")},
                  "priority": float(i.get("priority", 0)), "kpis": insight_kpis(i)} for i in INSIGHTS],
    "facts": {f: {"text": FACTS[f]["text"]} for i in INSIGHTS for f in i["facts"]},
    "catalog": [{"id": r["id"], "name": r["name"], "display": fmt_value(r["value"], r["unit"]), "status": r["status"],
                 "binding": r["binding"], "reliability": r["reliability"], "formula": r["formula"], "sql": r["sql"],
                 "definition": r["definition"], "reason": BINDINGS[r["id"]].get("reason") or ""} for _, r in KPI_CATALOG.iterrows()],
    "footer": [f"Generated by BIFlow (Nexora team) on {utc_now()[:16].replace('T', ' ')} UTC · layout: {layout_source}.",
               "Each value comes from an SQL query verified by a second independent calculation (step 8); each insight cites "
               "the statistical facts whose figures it uses (step 9).",
               f"Fingerprints: catalog {CATALOG_SHA256[:12]} · analysis {ANALYSIS_SHA256[:12]} · audit log "
               f"{AUDIT.events[-1]['hash'][:12]}."]}

payload = json.dumps(DASHBOARD, ensure_ascii=False, default=_json_default).replace("</", "<\\/")
DASHBOARD_HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_lib.escape(LAYOUT['title'])}</title><style>{DASHBOARD_CSS}</style></head>
<body><main id="app"></main>
<script type="application/json" id="dashboard-data">{payload}</script>
<script>{DASHBOARD_JS}</script></body></html>"""
DASHBOARD_PATH = BI_DIR / "dashboard.html"
DASHBOARD_PATH.write_text(DASHBOARD_HTML, encoding="utf-8")
DASHBOARD_SHA256 = sha256_text(DASHBOARD_HTML)
AUDIT.log("dashboard_agent", "dashboard_written", {"path": DASHBOARD_PATH, "bytes": len(DASHBOARD_HTML.encode()), "sha256": DASHBOARD_SHA256,
                                                   "tiles": len(LAYOUT["tiles"]) + 1, "charts": len(LAYOUT["charts"]),
                                                   "segments": len(LAYOUT["breakdowns"]), "insights": len(INSIGHTS)})
print(f"Dashboard written: {DASHBOARD_PATH} ({len(DASHBOARD_HTML.encode()) / 1024:.0f} KB) · download it from the Output tab")
try:
    raise ImportError("aperçu HTML désactivé en déploiement")
    display(HTML(f'<iframe srcdoc="{html_lib.escape(DASHBOARD_HTML)}" style="width:100%;height:1000px;border:1px solid #ddd;'
                 f'border-radius:8px"></iframe>'))
except ImportError:
    pass
