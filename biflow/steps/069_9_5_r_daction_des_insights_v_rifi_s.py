MAX_LLM_INSIGHTS = 5        # insights rédigés par le LLM
MAX_INSIGHTS = 7            # total, avec les signaux importants non couverts que le code ajoute
# Sens d'une variation (début de mot : « baissé » compte, « décroissance » n'est pas une « croissance », « montant » n'est pas
# « monte »). Pas « amélioration » : un délai qui baisse s'améliore.
UP_RE = re.compile(r"\b(?:hausse|augment\w*|progress\w*|croissance|croît|croiss\w*|mont[eé]\w*)")
DOWN_RE = re.compile(r"\b(?:baiss\w*|diminu\w*|recul\w*|chut\w*|décroiss\w*|repli\w*)")
NUM_RE = re.compile(r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?")
EXAMPLES = [
    {"titre": "Le churn progresse, porté par les contrats mensuels",
     "texte": "Le taux de résiliation passe de 4,1 % à 5,3 % en trois mois (+1,2 pt). Les contrats sans engagement expliquent "
              "l'essentiel de la hausse, alors que les contrats annuels restent stables.",
     "recommandation": "Proposer une offre de fidélisation ciblée aux clients sans engagement de plus de 6 mois.",
     "type": "alerte"},
    {"titre": "Une région concentre la moitié du chiffre d'affaires",
     "texte": "La région Nord réalise 48,2 % des ventes ; les trois premières régions dépassent 80 %.",
     "recommandation": "Sécuriser la logistique de la région Nord et tester des actions commerciales dans les régions sous-représentées.",
     "type": "constat"}]
SYSTEM_INSIGHTS = f"""Tu es le BI Analyst Agent du système BIFlow ({BI_INPUT['domain']}). Rédige au plus {MAX_LLM_INSIGHTS} insights en français
pour un décideur, à partir des FAITS fournis (numérotés F..). Chaque insight relie si possible un signal à son explication
(un fait de contribution ou de segment) et propose une action concrète.
Règles strictes :
- n'utilise QUE les nombres présents dans les faits que tu cites ; n'invente, n'arrondis autrement ni ne recalcule aucun chiffre ;
- cite dans "faits" tous les faits dont tu reprends un nombre ;
- respecte le sens des faits (hausse / baisse) et leur valence (favorable / défavorable) ;
- utilise chaque nombre pour ce qu'il représente, d'après son étiquette dans "chiffres" : une « part de la variation expliquée »
  n'est jamais une hausse du KPI, et un écart en points (pt) n'est pas une variation en % ;
- un seul insight par KPI : regroupe dans le même insight le signal et son explication ;
- les exemples ci-dessous sont FICTIFS : imite leur style, jamais leurs chiffres ni leurs noms.
Exemples : {json.dumps(EXAMPLES, ensure_ascii=False)}

Réponds UNIQUEMENT avec un tableau JSON :
[{{"titre": "...", "texte": "...", "recommandation": "...", "type": "alerte" | "opportunité" | "constat", "faits": ["F..", ...]}}]"""


def parse_num(tok: str) -> float:
    return float(re.sub(r"[ \u00a0\u202f]", "", tok).replace(",", "."))


def allowed_numbers(fids: list[str]) -> tuple[list[float], set[int]]:
    """Nombres citables : tous ceux des faits cités (texte écrit par le code, valeurs et chiffres étiquetés, dont les valeurs
    des segments intermédiaires), aussi exprimés en milliers / millions."""
    vals, years = [], set()
    for f in fids:
        labelled = " ".join(str(v) for v in FACTS[f].get("chiffres", {}).values())
        for tok in NUM_RE.findall(" ".join(FACTS[f]["nombres"]) + " " + FACTS[f]["texte"] + " " + labelled):
            v = parse_num(tok)
            vals += [v, v / 1e3, v / 1e6]
        for w in FACTS[f].get("windows", []) + [FACTS[f].get("periods", [])]:
            years |= {p // 100 for p in w}
    return vals, years


def number_ok(tok: str, vals: list[float], years: set[int]) -> bool:
    x = parse_num(tok)
    if x.is_integer() and (int(x) in years or x <= 12):
        return True
    m = re.search(r"[.,](\d+)$", re.sub(r"[ \u00a0\u202f]", "", tok))
    dec = len(m.group(1)) if m else 0
    return any(round(abs(a), dec) == round(x, dec) or abs(abs(a) - x) <= 0.005 * max(abs(a), 1e-9) for a in vals)


def cited_text(fid: str) -> str:
    """Tout ce qu'un fait permet de nommer : son texte, ses chiffres étiquetés, ses segments, le nom et la formule de son KPI."""
    f, kid = FACTS[fid], FACTS[fid]["kpi"]
    parts = [f["texte"], " ".join(f.get("chiffres", {})), " ".join(str(s.get("g")) for s in f.get("segments", [])),
             str(f.get("segment", "")), KB_BY_ID[kid]["name"] if kid in KB_BY_ID else "",
             readable(KB_BY_ID[kid], BINDINGS[kid]) if kid in BINDINGS else ""]
    return " ".join(parts)


def segment_values() -> set[str]:
    """Noms des segments de toutes les colonnes de découpage (ex. « Illinois », « Month-to-month ») : un insight ne peut en
    nommer un que s'il figure dans les faits qu'il cite. Les valeurs trop courtes ou purement numériques sont ignorées."""
    out = set()
    for t, c in sorted({d for dims in DIMS.values() for d in dims}):
        out |= {v for v in observed_values(t, c) if len(v) >= 3 and re.search(r"[A-Za-zÀ-ÿ]", v)}
    return out


KNOWN_SEGMENTS = segment_values()


def repair_citations(ins: dict, ctx_ids: set[str]) -> dict:
    """Un nombre absent des faits cités mais présent, à l'identique, dans un autre fait du MÊME KPI montré au LLM :
    ce fait est ajouté aux citations (oubli de citation), au lieu de refuser l'insight. Un nombre introuvable reste refusé."""
    if not isinstance(ins, dict) or not isinstance(ins.get("faits"), list) or not all(f in FACTS for f in ins["faits"]):
        return ins
    kpis = {FACTS[f]["kpi"] for f in ins["faits"]}
    text = f"{ins.get('titre', '')} {ins.get('texte', '')} {ins.get('recommandation', '')}"
    vals, years = allowed_numbers(ins["faits"])
    extra = []
    for tok in NUM_RE.findall(text):
        if number_ok(tok, vals, years):
            continue
        for g in sorted(ctx_ids - set(ins["faits"]) - set(extra)):
            if FACTS[g]["kpi"] in kpis and number_ok(tok, *allowed_numbers([g])):
                extra.append(g)
                break
    return {**ins, "faits": ins["faits"] + extra} if extra else ins


def check_insight(ins) -> str | None:
    """Superviseur des insights du LLM : faits cités existants ; chaque nombre présent dans ces faits ; sens (hausse/baisse)
    du titre et du texte conforme aux faits ; une part de variation jamais présentée comme une hausse ; segments nommés
    présents dans les faits. Renvoie la raison du refus, ou None si l'insight est accepté."""
    if not isinstance(ins, dict):
        return "objet attendu"
    for k in ("titre", "texte", "recommandation", "type", "faits"):
        if not ins.get(k):
            return f"champ « {k} » manquant"
    if ins["type"] not in {"alerte", "opportunité", "constat"}:
        return "type : alerte, opportunité ou constat"
    fids = ins["faits"] if isinstance(ins["faits"], list) else []
    unknown = [f for f in fids if f not in FACTS]
    if unknown or not fids:
        return f"faits inexistants : {unknown}" if unknown else "aucun fait cité"
    text = f"{ins['titre']} {ins['texte']} {ins['recommandation']}"
    vals, years = allowed_numbers(fids)
    bad = [t for t in NUM_RE.findall(text) if not number_ok(t, vals, years)]
    if bad:
        return f"nombres absents des faits cités : {bad[:5]}"
    low = text.lower()
    for f in fids:                                       # rôle des nombres : une part de variation expliquée n'est pas une hausse
        share = next((v for k, v in FACTS[f].get("chiffres", {}).items() if k.startswith("part de la variation")), None)
        if share is None:
            continue
        sv = parse_num(NUM_RE.findall(share)[0])
        for m in re.finditer(r"(augment\w*|hausse|progress\w*|croissance|baiss\w*|diminu\w*|recul\w*|chut\w*)\W+(?:\w+\W+){0,3}?("
                             + NUM_RE.pattern + ")", low):
            if abs(parse_num(m.group(2)) - sv) < 0.05:
                return (f"le nombre {share} est la part de la variation expliquée par un segment, pas une "
                        f"{'hausse' if m.group(1)[0] in 'ahpc' else 'baisse'} du KPI")
    senses = {FACTS[f].get("sens") for f in fids} - {None}
    if len(senses) == 1:                                 # le titre et le constat, chacun, doivent aller dans le sens des faits
        sens = senses.pop()
        for part in ("titre", "texte"):
            words_ = str(ins[part]).lower()
            up, down = len(UP_RE.findall(words_)), len(DOWN_RE.findall(words_))
            if (sens == "hausse" and down > up) or (sens == "baisse" and up > down):
                return f"sens contraire aux faits cités dans le {part} (les faits indiquent une {sens})"
    named = sorted(v for v in KNOWN_SEGMENTS if re.search(rf"(?<![\w-]){re.escape(v)}(?![\w-])", text))
    support = " ".join(cited_text(f) for f in fids)
    foreign = [v for v in named if v not in support]
    if foreign:
        return f"segment(s) {foreign[:3]} absent(s) des faits cités : ne nomme que les segments de ces faits"
    return None


def code_insight(fid: str) -> dict:
    """Rédaction de secours par le code : le fait, son explication éventuelle, une recommandation prudente."""
    f = FACTS[fid]
    expl = next((g for g in FACTS.values() if g.get("parent") == fid), None)
    kind = "alerte" if f["valence"] == "défavorable" else "opportunité" if f["valence"] == "favorable" else "constat"
    lab, sens = f["label"], f.get("sens") or ""
    title = {"tendance": f"{lab} : {sens} continue", "variation récente": f"{lab} : {sens} récente inhabituelle",
             "sur un an": f"{lab} : {sens} sur un an", "rupture": f"{lab} : changement de niveau",
             "anomalie": f"{lab} : mois atypique ({plabel(f['periods'][0])})" if f.get("periods") else f"{lab} : mois atypique",
             "segment": f"{lab} : fortes différences par {f['by'][1]}" if f.get("worst_segment") else f"{lab} : répartition par {f['by'][1]}"
             if f.get("by") else lab}.get(f["type"], lab)
    target = (f" Cibler en priorité {expl['by'][1]} = « {expl['segment']} »." if expl else
              f" Cibler en priorité {f['by'][1]} = « {f['worst_segment']} »." if f.get("worst_segment") else "")
    reco = {"alerte": (f"Analyser pourquoi « {f['worst_segment']} » s'écarte autant de la moyenne et suivre « {lab} » par {f['by'][1]}."
                       if f["type"] == "segment" and f.get("worst_segment") else
                       f"Analyser les causes de l'évolution de « {lab} » et la suivre chaque mois.{target}"),
            "opportunité": f"Identifier ce qui porte l'amélioration de « {lab} » pour la consolider.{target}",
            "constat": f"Tenir compte de cette répartition dans le pilotage de « {lab} »."}[kind]
    return {"titre": title[0].upper() + title[1:], "texte": f["texte"] + (" " + expl["texte"] if expl else ""), "recommandation": reco,
            "type": kind, "faits": [fid] + ([expl["id"]] if expl else []), "source": "code"}


MAX_CONTEXT_CHARS = 6000    # contexte compact : un prompt trop long sature la mémoire du GPU (T4) et dilue l'attention du LLM


def insight_context() -> list[dict]:
    """Faits transmis au LLM : les signaux les plus prioritaires (hors qualité des données), leurs explications et
    quelques valeurs globales ; les chiffres étiquetés ne sont joints qu'aux contributions et segments (risque de confusion)."""
    ranked = sorted((f for f in FACTS.values() if f["type"] not in {"valeur", "contribution"} and not is_quality_kpi(f["kpi"])),
                    key=lambda f: -f["priority"])
    top_kpis = KPI_CATALOG.assign(_w=KPI_CATALOG.apply(kpi_weight, axis=1)).nlargest(4, "_w")["id"]
    chosen = []
    for f in ranked + [g for g in FACTS.values() if g["type"] == "valeur" and g["kpi"] in set(top_kpis)]:
        for g in [f] + [c for c in FACTS.values() if c.get("parent") == f["id"]]:
            item = {"fait": g["id"], "type": g["type"], "constat": g["texte"][:320], "valence": g["valence"]}
            if g["type"] in {"contribution", "segment"}:
                item["chiffres"] = g.get("chiffres", {})
            if g.get("parent"):
                item["explique_le_fait"] = g["parent"]
            if len(canonical_json(chosen + [item])) > MAX_CONTEXT_CHARS:
                return chosen
            chosen.append(item)
    return chosen


INSIGHTS, insight_errors = [], []
facts_ctx = insight_context()
if any(f["type"] != "valeur" for f in facts_ctx):
    feedback = None
    for attempt in range(2):
        payload = {"faits": facts_ctx, **({"insights_refusés": feedback} if feedback else {})}
        raw = llm_call("bi_analyst", [{"role": "system", "content": SYSTEM_INSIGHTS},
                                      {"role": "user", "content": canonical_json(payload)}], max_new_tokens=1400)
        try:
            proposed = extract_json(raw, list)[:MAX_LLM_INSIGHTS - len(INSIGHTS)]
        except ValueError as e:
            insight_errors.append(f"essai {attempt + 1} : réponse illisible ({e})")
            feedback = [f"réponse illisible : {e}"]
            continue
        feedback = []
        ctx_ids = {f["fait"] for f in facts_ctx}
        for ins in proposed:
            ins = repair_citations(ins, ctx_ids)
            err = check_insight(ins)
            if not err:
                kpis = {FACTS[f]["kpi"] for f in ins["faits"]}
                twin = next((i for i in INSIGHTS if kpis <= {FACTS[f]["kpi"] for f in i["faits"]}), None)
                if twin:
                    err = f"redite : ce KPI est déjà traité par l'insight « {twin['titre'][:50]} »"
            if err:
                insight_errors.append(f"essai {attempt + 1} · {str((ins or {}).get('titre', '?'))[:60]} : {err}")
                feedback.append({"insight": ins, "refus": err})
            else:
                INSIGHTS.append({**{k: ins[k] for k in ("titre", "texte", "recommandation", "type", "faits")}, "source": "LLM"})
        if not feedback or len(INSIGHTS) >= MAX_LLM_INSIGHTS:
            break

covered = {f for i in INSIGHTS for f in i["faits"]}
covered_kpis = {FACTS[f]["kpi"] for f in covered}
covered_sig = {tuple(FACTS[f]["nombres"][1:]) for f in covered if FACTS[f]["type"] == "segment"}
target = 3 if INSIGHTS else 5                            # le code complète jusqu'à 3 insights (5 si le LLM n'en a produit aucun)
IMPORTANT = 0.25                                         # au-delà, un signal non couvert est ajouté même si l'objectif est atteint
for f in sorted((f for f in FACTS.values() if f["type"] not in {"valeur", "contribution"} and f["priority"] > 0),
                key=lambda f: -f["priority"]):
    if len(INSIGHTS) >= MAX_INSIGHTS or (len(INSIGHTS) >= target and f["priority"] < IMPORTANT):
        break
    signature = tuple(f["nombres"][1:]) if f["type"] == "segment" else None      # deux KPI qui donnent le même découpage
    if f["id"] not in covered and f["kpi"] not in covered_kpis and not is_quality_kpi(f["kpi"]) \
            and (signature is None or signature not in covered_sig):
        INSIGHTS.append(code_insight(f["id"]))
        covered |= set(INSIGHTS[-1]["faits"])
        covered_kpis.add(f["kpi"])
        if signature is not None:
            covered_sig.add(signature)

for i, ins in enumerate(INSIGHTS, 1):
    ins["id"] = f"I{i:02d}"
    ins["priorité"] = round(max(FACTS[f]["priority"] for f in ins["faits"]), 4)
    ins["vérifié"] = check_insight(ins) is None
INSIGHTS.sort(key=lambda i: -i["priorité"])
AUDIT.log("bi_analyst", "insights_written", {"insights": [{k: i[k] for k in ("id", "titre", "type", "faits", "source", "vérifié")} for i in INSIGHTS],
                                             "rejected": insight_errors}, level="DECISION")
if not INSIGHTS:
    print("Aucun signal net : les KPI sont stables et homogènes entre segments. C'est aussi une information pour le décideur.")
print(f"{len(INSIGHTS)} insight(s) · {sum(i['source'] == 'LLM' for i in INSIGHTS)} rédigé(s) par le LLM, "
      f"{sum(i['source'] == 'code' for i in INSIGHTS)} par le code · {len(insight_errors)} refus du superviseur")
for e in insight_errors:
    print("  refus :", e)
for ins in INSIGHTS:
    print(f"\n[{ins['type'].upper()}] {ins['titre']}  ({ins['id']} · {ins['source']} · faits {', '.join(ins['faits'])})")
    print(f"  {ins['texte']}")
    print(f"  → {ins['recommandation']}")
