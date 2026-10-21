MAX_LLM_INSIGHTS = 5        # insights rédigés par le LLM
MAX_INSIGHTS = 7            # total, avec les signaux importants non couverts que le code ajoute
# Sens d'une variation (début de mot : « baissé » compte, « décroissance » n'est pas une « croissance », « montant » n'est pas
# « monte »). Pas « amélioration » : un délai qui baisse s'améliore.
UP_RE = re.compile(r"\b(?:increas\w*|rise[sn]?\b|rising|rose\b|grow\w*|grew\b|climb\w*|surg\w*|jump\w*)")
DOWN_RE = re.compile(r"\b(?:decreas\w*|declin\w*|drop\w*|fall(?:s|ing|en)?\b|fell\b|dip\w*|slump\w*|shr[iau]nk\w*|plung\w*)")
NUM_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
EXAMPLES = [
    {"title": "Churn is rising, driven by monthly contracts",
     "text": "The churn rate goes from 4.1% to 5.3% in three months (+1.2 pt). Contracts without commitment explain "
             "most of the increase, while annual contracts remain stable.",
     "recommendation": "Offer a targeted loyalty deal to customers without commitment for more than 6 months.",
     "type": "alert"},
    {"title": "One region concentrates half of the revenue",
     "text": "The North region makes 48.2% of sales; the top three regions exceed 80%.",
     "recommendation": "Secure the logistics of the North region and test sales actions in under-represented regions.",
     "type": "finding"}]
SYSTEM_INSIGHTS = f"""You are the BI Analyst Agent of the BIFlow system ({BI_INPUT['domain']}). Write at most {MAX_LLM_INSIGHTS} insights in English
for a decision-maker, from the FACTS provided (numbered F..). Each insight links, where possible, a signal to its explanation
(a contribution or segment fact) and proposes a concrete action.
Strict rules:
- use ONLY the numbers present in the facts you cite; do not invent, round differently or recompute any figure;
- cite in "facts" every fact from which you take a number;
- respect the direction of the facts (increase / decrease) and their valence (favorable / unfavorable);
- use each number for what it represents, according to its label in "figures": a "share of the change explained"
  is never an increase of the KPI, and a gap in points (pt) is not a change in %;
- a single insight per KPI: group the signal and its explanation in the same insight;
- the examples below are FICTIONAL: imitate their style, never their figures or their names.
Examples: {json.dumps(EXAMPLES, ensure_ascii=False)}

Answer ONLY with a JSON array:
[{{"title": "...", "text": "...", "recommendation": "...", "type": "alert" | "opportunity" | "finding", "facts": ["F..", ...]}}]"""


def parse_num(tok: str) -> float:
    return float(re.sub(r"[,   ]", "", tok))


def allowed_numbers(fids: list[str]) -> tuple[list[float], set[int]]:
    """Citable numbers: all those of the cited facts (text written by the code, values and labelled figures, including the values
    of intermediate segments), also expressed in thousands / millions."""
    vals, years = [], set()
    for f in fids:
        labelled = " ".join(str(v) for v in FACTS[f].get("figures", {}).values())
        for tok in NUM_RE.findall(" ".join(FACTS[f]["numbers"]) + " " + FACTS[f]["text"] + " " + labelled):
            v = parse_num(tok)
            vals += [v, v / 1e3, v / 1e6]
        for w in FACTS[f].get("windows", []) + [FACTS[f].get("periods", [])]:
            years |= {p // 100 for p in w}
    return vals, years


def number_ok(tok: str, vals: list[float], years: set[int]) -> bool:
    x = parse_num(tok)
    if x.is_integer() and (int(x) in years or x <= 12):
        return True
    m = re.search(r"\.(\d+)$", re.sub(r"[,   ]", "", tok))
    dec = len(m.group(1)) if m else 0
    return any(round(abs(a), dec) == round(x, dec) or abs(abs(a) - x) <= 0.005 * max(abs(a), 1e-9) for a in vals)


def cited_text(fid: str) -> str:
    """Everything a fact allows to name: its text, its labelled figures, its segments, the name and formula of its KPI."""
    f, kid = FACTS[fid], FACTS[fid]["kpi"]
    parts = [f["text"], " ".join(f.get("figures", {})), " ".join(str(s.get("g")) for s in f.get("segments", [])),
             str(f.get("segment", "")), KB_BY_ID[kid]["name"] if kid in KB_BY_ID else "",
             readable(KB_BY_ID[kid], BINDINGS[kid]) if kid in BINDINGS else ""]
    return " ".join(parts)


def segment_values() -> set[str]:
    """Segment names of all breakdown columns (e.g. "Illinois", "Month-to-month"): an insight can only
    name one if it appears in the facts it cites. Values that are too short or purely numeric are ignored."""
    out = set()
    for t, c in sorted({d for dims in DIMS.values() for d in dims}):
        out |= {v for v in observed_values(t, c) if len(v) >= 3 and re.search(r"[A-Za-zÀ-ÿ]", v)}
    return out


KNOWN_SEGMENTS = segment_values()


def repair_citations(ins: dict, ctx_ids: set[str]) -> dict:
    """A number missing from the cited facts but present, identically, in another fact of the SAME KPI shown to the LLM:
    that fact is added to the citations (missing citation), instead of rejecting the insight. A number that cannot be found is still rejected."""
    if not isinstance(ins, dict) or not isinstance(ins.get("facts"), list) or not all(f in FACTS for f in ins["facts"]):
        return ins
    kpis = {FACTS[f]["kpi"] for f in ins["facts"]}
    text = f"{ins.get('title', '')} {ins.get('text', '')} {ins.get('recommendation', '')}"
    vals, years = allowed_numbers(ins["facts"])
    extra = []
    for tok in NUM_RE.findall(text):
        if number_ok(tok, vals, years):
            continue
        for g in sorted(ctx_ids - set(ins["facts"]) - set(extra)):
            if FACTS[g]["kpi"] in kpis and number_ok(tok, *allowed_numbers([g])):
                extra.append(g)
                break
    return {**ins, "facts": ins["facts"] + extra} if extra else ins


def check_insight(ins) -> str | None:
    """Supervisor of the LLM's insights: cited facts exist; every number present in those facts; direction (increase/decrease)
    of the title and text consistent with the facts; a share of change never presented as an increase; named segments
    present in the facts. Returns the reason for rejection, or None if the insight is accepted."""
    if not isinstance(ins, dict):
        return "object expected"
    for k in ("title", "text", "recommendation", "type", "facts"):
        if not ins.get(k):
            return f"field “{k}” missing"
    if ins["type"] not in {"alert", "opportunity", "finding"}:
        return "type: alert, opportunity or finding"
    fids = ins["facts"] if isinstance(ins["facts"], list) else []
    unknown = [f for f in fids if f not in FACTS]
    if unknown or not fids:
        return f"non-existent facts: {unknown}" if unknown else "no fact cited"
    text = f"{ins['title']} {ins['text']} {ins['recommendation']}"
    vals, years = allowed_numbers(fids)
    bad = [t for t in NUM_RE.findall(text) if not number_ok(t, vals, years)]
    if bad:
        return f"numbers missing from the cited facts: {bad[:5]}"
    low = text.lower()
    for f in fids:                                       # rôle des nombres : une part de variation expliquée n'est pas une hausse
        share = next((v for k, v in FACTS[f].get("figures", {}).items() if k.startswith("share of the")), None)
        if share is None:
            continue
        sv = parse_num(NUM_RE.findall(share)[0])
        for m in re.finditer(r"(" + UP_RE.pattern[2:] + r"|" + DOWN_RE.pattern[2:] + r")\W+(?:\w+\W+){0,3}?("
                             + NUM_RE.pattern + ")", low):
            if abs(parse_num(m.group(2)) - sv) < 0.05:
                return (f"the number {share} is the share of the change explained by a segment, not an "
                        f"{'increase' if UP_RE.match(m.group(1)) else 'decrease'} of the KPI")
    senses = {FACTS[f].get("direction") for f in fids} - {None}
    if len(senses) == 1:                                 # le titre et le constat, chacun, doivent aller dans le sens des faits
        sens = senses.pop()
        for part in ("title", "text"):
            words_ = str(ins[part]).lower()
            up, down = len(UP_RE.findall(words_)), len(DOWN_RE.findall(words_))
            if (sens == "increase" and down > up) or (sens == "decrease" and up > down):
                return f"direction contrary to the cited facts in the {part} (the facts indicate an {sens})"
    named = sorted(v for v in KNOWN_SEGMENTS if re.search(rf"(?<![\w-]){re.escape(v)}(?![\w-])", text))
    support = " ".join(cited_text(f) for f in fids)
    foreign = [v for v in named if v not in support]
    if foreign:
        return f"segment(s) {foreign[:3]} missing from the cited facts: only name the segments of these facts"
    return None


def code_insight(fid: str) -> dict:
    """Fallback write-up by the code: the fact, its explanation if any, a cautious recommendation."""
    f = FACTS[fid]
    expl = next((g for g in FACTS.values() if g.get("parent") == fid), None)
    kind = "alert" if f["valence"] == "unfavorable" else "opportunity" if f["valence"] == "favorable" else "finding"
    lab, sens = f["label"], f.get("direction") or ""
    title = {"trend": f"{lab}: continuing {sens}", "recent change": f"{lab}: unusual recent {sens}",
             "year over year": f"{lab}: {sens} over one year", "level shift": f"{lab}: change of level",
             "anomaly": f"{lab}: atypical month ({plabel(f['periods'][0])})" if f.get("periods") else f"{lab}: atypical month",
             "segment": f"{lab}: strong differences by {f['by'][1]}" if f.get("worst_segment") else f"{lab}: distribution by {f['by'][1]}"
             if f.get("by") else lab}.get(f["type"], lab)
    target = (f" Target {expl['by'][1]} = “{expl['segment']}” first." if expl else
              f" Target {f['by'][1]} = “{f['worst_segment']}” first." if f.get("worst_segment") else "")
    reco = {"alert": (f"Analyse why “{f['worst_segment']}” deviates so much from the average and monitor “{lab}” by {f['by'][1]}."
                      if f["type"] == "segment" and f.get("worst_segment") else
                      f"Analyse the causes of the change in “{lab}” and monitor it every month.{target}"),
            "opportunity": f"Identify what drives the improvement of “{lab}” in order to consolidate it.{target}",
            "finding": f"Take this distribution into account when managing “{lab}”."}[kind]
    return {"title": title[0].upper() + title[1:], "text": f["text"] + (" " + expl["text"] if expl else ""), "recommendation": reco,
            "type": kind, "facts": [fid] + ([expl["id"]] if expl else []), "source": "code"}


MAX_CONTEXT_CHARS = 6000    # contexte compact : un prompt trop long sature la mémoire du GPU (T4) et dilue l'attention du LLM


def insight_context() -> list[dict]:
    """Facts sent to the LLM: the highest-priority signals (excluding data quality), their explanations and
    a few overall values; the labelled figures are only attached to contributions and segments (risk of confusion)."""
    ranked = sorted((f for f in FACTS.values() if f["type"] not in {"value", "contribution"} and not is_quality_kpi(f["kpi"])),
                    key=lambda f: -f["priority"])
    top_kpis = KPI_CATALOG.assign(_w=KPI_CATALOG.apply(kpi_weight, axis=1)).nlargest(4, "_w")["id"]
    chosen = []
    for f in ranked + [g for g in FACTS.values() if g["type"] == "value" and g["kpi"] in set(top_kpis)]:
        for g in [f] + [c for c in FACTS.values() if c.get("parent") == f["id"]]:
            item = {"fact": g["id"], "type": g["type"], "finding": g["text"][:320], "valence": g["valence"]}
            if g["type"] in {"contribution", "segment"}:
                item["figures"] = g.get("figures", {})
            if g.get("parent"):
                item["explains_fact"] = g["parent"]
            if len(canonical_json(chosen + [item])) > MAX_CONTEXT_CHARS:
                return chosen
            chosen.append(item)
    return chosen


INSIGHTS, insight_errors = [], []
facts_ctx = insight_context()
if any(f["type"] != "value" for f in facts_ctx):
    feedback = None
    for attempt in range(2):
        payload = {"facts": facts_ctx, **({"rejected_insights": feedback} if feedback else {})}
        raw = llm_call("bi_analyst", [{"role": "system", "content": SYSTEM_INSIGHTS},
                                      {"role": "user", "content": canonical_json(payload)}], max_new_tokens=1400)
        try:
            proposed = extract_json(raw, list)[:MAX_LLM_INSIGHTS - len(INSIGHTS)]
        except ValueError as e:
            insight_errors.append(f"attempt {attempt + 1}: unreadable answer ({e})")
            feedback = [f"unreadable answer: {e}"]
            continue
        feedback = []
        ctx_ids = {f["fact"] for f in facts_ctx}
        for ins in proposed:
            ins = repair_citations(ins, ctx_ids)
            err = check_insight(ins)
            if not err:
                kpis = {FACTS[f]["kpi"] for f in ins["facts"]}
                twin = next((i for i in INSIGHTS if kpis <= {FACTS[f]["kpi"] for f in i["facts"]}), None)
                if twin:
                    err = f"repetition: this KPI is already covered by the insight “{twin['title'][:50]}”"
            if err:
                insight_errors.append(f"attempt {attempt + 1} · {str((ins or {}).get('title', '?'))[:60]}: {err}")
                feedback.append({"insight": ins, "rejection": err})
            else:
                INSIGHTS.append({**{k: ins[k] for k in ("title", "text", "recommendation", "type", "facts")}, "source": "LLM"})
        if not feedback or len(INSIGHTS) >= MAX_LLM_INSIGHTS:
            break

covered = {f for i in INSIGHTS for f in i["facts"]}
covered_kpis = {FACTS[f]["kpi"] for f in covered}
covered_sig = {tuple(FACTS[f]["numbers"][1:]) for f in covered if FACTS[f]["type"] == "segment"}
target = 3 if INSIGHTS else 5                            # le code complète jusqu'à 3 insights (5 si le LLM n'en a produit aucun)
IMPORTANT = 0.25                                         # au-delà, un signal non couvert est ajouté même si l'objectif est atteint
for f in sorted((f for f in FACTS.values() if f["type"] not in {"value", "contribution"} and f["priority"] > 0),
                key=lambda f: -f["priority"]):
    if len(INSIGHTS) >= MAX_INSIGHTS or (len(INSIGHTS) >= target and f["priority"] < IMPORTANT):
        break
    signature = tuple(f["numbers"][1:]) if f["type"] == "segment" else None      # deux KPI qui donnent le même découpage
    if f["id"] not in covered and f["kpi"] not in covered_kpis and not is_quality_kpi(f["kpi"]) \
            and (signature is None or signature not in covered_sig):
        INSIGHTS.append(code_insight(f["id"]))
        covered |= set(INSIGHTS[-1]["facts"])
        covered_kpis.add(f["kpi"])
        if signature is not None:
            covered_sig.add(signature)

for i, ins in enumerate(INSIGHTS, 1):
    ins["id"] = f"I{i:02d}"
    ins["priority"] = round(max(FACTS[f]["priority"] for f in ins["facts"]), 4)
    ins["verified"] = check_insight(ins) is None
INSIGHTS.sort(key=lambda i: -i["priority"])
AUDIT.log("bi_analyst", "insights_written", {"insights": [{k: i[k] for k in ("id", "title", "type", "facts", "source", "verified")} for i in INSIGHTS],
                                             "rejected": insight_errors}, level="DECISION")
if not INSIGHTS:
    print("No clear signal: the KPIs are stable and homogeneous across segments. This is also information for the decision-maker.")
print(f"{len(INSIGHTS)} insight(s) · {sum(i['source'] == 'LLM' for i in INSIGHTS)} written by the LLM, "
      f"{sum(i['source'] == 'code' for i in INSIGHTS)} by the code · {len(insight_errors)} rejection(s) by the supervisor")
for e in insight_errors:
    print("  rejected:", e)
for ins in INSIGHTS:
    print(f"\n[{ins['type'].upper()}] {ins['title']}  ({ins['id']} · {ins['source']} · facts {', '.join(ins['facts'])})")
    print(f"  {ins['text']}")
    print(f"  → {ins['recommendation']}")
