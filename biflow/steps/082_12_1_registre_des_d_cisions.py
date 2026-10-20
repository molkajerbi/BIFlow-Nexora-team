import inspect as _inspect
import unicodedata

XAI_DIR = RUN_DIR / "xai"
XAI_DIR.mkdir(exist_ok=True)
XAI_STEPS = {1: "Contrat et ingestion", 2: "Outils du Profiler", 3: "Domaine et diagnostic (LLM)", 4: "Qualité et nettoyage",
             5: "ETL : modèle en étoile", 6: "Orchestration de la préparation", 7: "Pont et base de connaissances",
             8: "Agent KPI", 9: "Agent analyste", 10: "Agent dashboard", 11: "Orchestration BI", 12: "Explicabilité (XAI)",
             13: "Orchestrateur global"}
DECIDED_BY = {
    "code": "règle du code", "règle": "règle du code", "évidente": "règle du code (liaison évidente)",
    "LLM": "LLM, vérifié par le superviseur", "agent": "LLM, vérifié par le superviseur",
    "fallback": "repli du superviseur (réponse du LLM absente ou refusée)", "repli": "repli du superviseur (réponse du LLM absente ou refusée)",
    "proposée par l'agent": "LLM (KPI proposé), vérifié par le superviseur — à confirmer par un humain",
    "politique": "politique de risque automatique", "humain": "validation humaine",
}
SEM_LABEL = {"id": "identifiant", "category": "catégorie", "datetime": "date", "numeric": "mesure décimale",
             "integer": "nombre entier", "text": "texte libre", "zip": "code postal", "geo": "coordonnée GPS"}


def decided_by(source) -> str:
    s = str(source or "code")
    if s.startswith("repli"):
        return DECIDED_BY["repli"]
    if s.startswith("politique"):
        return DECIDED_BY["politique"]
    return DECIDED_BY.get(s, s)


def xai_num(v) -> str:
    """Nombre lisible à la française (1 234 · 12,35)."""
    if isinstance(v, (bool, np.bool_)):
        return "oui" if v else "non"
    if isinstance(v, (int, np.integer)) or (isinstance(v, (float, np.floating)) and float(v).is_integer() and abs(v) < 1e15):
        return f"{int(v):,}".replace(",", " ")
    if isinstance(v, (float, np.floating)):
        return (f"{v:,.4f}" if abs(v) < 1 else f"{v:,.2f}").replace(",", " ").replace(".", ",").rstrip("0").rstrip(",")
    return str(v)


def doc(name: str) -> str:
    """Documentation d'une fonction du pipeline : l'explication globale vient du code lui-même (toujours à jour)."""
    fn = globals().get(name)
    text = _inspect.getdoc(fn) if callable(fn) else None
    return " ".join((text or "").split())


def audit_seq(action: str, agent: str | None = None, contains: str | None = None) -> list[int]:
    """Numéro du dernier événement du journal d'audit correspondant (traçabilité)."""
    for e in reversed(AUDIT.events):
        if e["action"] == action and (agent is None or e["agent"] == agent) and \
                (contains is None or contains in canonical_json(e["details"])):
            return [e["seq"]]
    return []


def refusals(action: str, agent: str | None = None, contains: str | None = None, limit: int = 3) -> list[str]:
    """Réponses du LLM refusées par le superviseur (dernière exécution), avec la raison du refus."""
    out = []
    for e in reversed(AUDIT.events):
        if e["action"] != action or (agent and e["agent"] != agent):
            continue
        errs = e["details"].get("errors") or [e["details"].get("error")]
        out += [str(x) for x in errs if x and (contains is None or contains in str(x))]
        if len(out) >= limit:
            break
    return list(dict.fromkeys(out))[:limit]


LEDGER: list[dict] = []
LEDGER_ERRORS: list[str] = []
NODE_STATUS = {"running": "terminé, on continue", "success": "terminé (succès)", "failed": "échec", "blocked": "bloqué"}


def node_history(result: dict) -> dict:
    """Historique d'un orchestrateur, lisible : « running » après un nœud veut dire « terminé, on passe au suivant »."""
    return {h["node"]: f"{NODE_STATUS.get(h['status'], h['status'])} · {xai_num(h['seconds'])} s" for h in result.get("history", [])}


def add_decision(step: int, agent: str, subject: str, obj: str, decision: str, why: str, evidence: dict | None = None,
                 by: str = "code", counterfactual: str | None = None, refused: list | None = None, terms=(),
                 audit: list | None = None) -> str:
    rid = f"D{len(LEDGER) + 1:03d}"
    LEDGER.append({"id": rid, "étape": step, "agent": agent, "sujet": subject, "objet": str(obj), "décision": decision,
                   "pourquoi": why, "preuves": {k: xai_num(v) if not isinstance(v, str) else v for k, v in (evidence or {}).items()
                                               if v is not None and v != ""},
                   "décidé_par": decided_by(by), "contrefactuel": counterfactual, "refus": list(refused or []),
                   "termes": sorted({str(t) for t in [obj, *terms] if t}), "audit": audit or []})
    return rid


def ledger_block(fn):
    """Chaque bloc du registre est indépendant : une partie absente (pipeline arrêté) n'empêche pas les autres."""
    def run():
        try:
            fn()
        except Exception as exc:
            LEDGER_ERRORS.append(f"{fn.__name__} : {type(exc).__name__} : {exc}")
    run.__name__ = fn.__name__
    return run


# ---------------------------------------------------------------- partie 1 · Data Preparation Agent
@ledger_block
def ledger_contract():
    stats, rels = INFERRED["stats"], INFERRED["relationship_details"]
    parents, children = {r["parent"] for r in rels}, {r["child"] for r in rels}
    for t, spec in DATA_CONTRACT.items():
        cols, role = spec["columns"], TABLE_ROLES.get(t)
        fks = {r["fk"] for r in rels if r["child"] == t}
        dates = [c for c, s in cols.items() if s == "datetime"]
        measures = [c for c, s in cols.items() if s in {"numeric", "integer"} and c not in (spec["grain"] or []) and c not in fks]
        where = (f"elle contient {len(dates)} date(s)" if dates else "elle ne contient aucune date") + \
                (f", {len(measures)} mesure(s)" if measures else ", aucune mesure propre") + \
                (", et d'autres tables y font référence" if t in parents else ", et aucune table n'y fait référence")
        cf = ("Elle aurait été une dimension si elle avait seulement été référencée par d'autres tables, sans dates ni mesures propres."
              if role == "fait" else "Elle aurait été une table de faits si elle avait contenu des dates d'événements ou des mesures "
                                     "sans être une simple référence pour d'autres tables.")
        add_decision(1, "Contract Agent", "rôle de table", t,
                     f"la table « {t} » est une table de {role}s" if role == "fait" else f"la table « {t} » est une dimension",
                     f"Règle : {doc('infer_roles')} Ici, {where}.",
                     {"fichier": spec.get("file"), "lignes": stats.get(t, {}).get("rows"), "colonnes": len(cols),
                      "identifiant (grain)": " + ".join(spec["grain"]) if spec["grain"] else "aucun (plusieurs lignes par valeur)",
                      "dates": ", ".join(dates[:6]) or "aucune", "mesures": ", ".join(measures[:6]) or "aucune"},
                     "code", cf, terms=[f"table {t}"], audit=audit_seq("contract_inferred"))
    types = TYPE_REPORT.set_index(["table", "column"]) if "TYPE_REPORT" in globals() else None
    for t, spec in DATA_CONTRACT.items():
        for c, sem in spec["columns"].items():
            ev = {"type retenu": SEM_LABEL.get(sem, sem)}
            fmt = INFERRED["formats"].get(f"{t}.{c}")
            if fmt:
                ev["format lu"] = str(fmt)
            if types is not None and (t, c) in types.index:
                r = types.loc[(t, c)]
                ev.update({"valeurs renseignées": int(r["non_null"]), "valeurs non converties": int(r["failed"])})
            add_decision(1, "Contract Agent", "type de colonne", f"{t}.{c}", f"la colonne « {c} » ({t}) est de type {SEM_LABEL.get(sem, sem)}",
                         f"Règle : {doc('infer_type')} Une valeur qui ne respecte pas ce type devient vide et est tracée (étape 4.1).",
                         ev, "code", None, terms=[c], audit=audit_seq("contract_inferred"))


@ledger_block
def ledger_relations():
    for r in INFERRED["relationship_details"]:
        weak = r.get("inclusion_pct", 100) < 95 or not r.get("same_name", True)
        add_decision(2, "Contract Agent / Profiler", "lien entre tables", f"{r['child']}.{r['fk']} → {r['parent']}.{r['pk']}",
                     f"« {r['child']} » est reliée à « {r['parent']} » par la colonne « {r['fk']} »"
                     + (" (lien à agréger : plusieurs lignes par clé)" if r.get("aggregate") else ""),
                     f"Règle : {doc('infer_relationships')}",
                     {"valeurs retrouvées dans la table liée (%)": r.get("inclusion_pct"), "même nom de colonne": r.get("same_name"),
                      "à vérifier": "oui" if weak else "non"}, "code",
                     "Un lien dont moins de 95 % des valeurs sont retrouvées, ou dont les noms diffèrent, est signalé « à vérifier » "
                     "et soumis au Domain Agent (étape 3).", terms=[r["fk"], r["child"], r["parent"]],
                     audit=audit_seq("contract_inferred"))


@ledger_block
def ledger_profiling():
    labels = {"cellules_manquantes_%": "cellules manquantes (%)", "valeurs_non_conformes": "valeurs non conformes au type",
              "grain_unique": "identifiant unique", "doublons_exacts": "lignes en double", "anomalies_IF": "lignes atypiques (Isolation Forest)",
              "extrêmes_IQR": "valeurs extrêmes (> 3 IQR)"}
    for t, row in HEALTH.iterrows():
        ev = {"lignes": row.get("lignes"), "colonnes": row.get("colonnes"),
              **{labels[k]: ("—" if row.get(k) is None else row.get(k)) for k in labels if k in row}}
        add_decision(2, "Data Profiler (outils)", "santé de table", f"santé de {t}",
                     f"diagnostic chiffré de la table « {t} »",
                     "Mesures faites par les outils du Profiler, sans LLM : profil des colonnes, unicité et doublons, liens entre "
                     "tables, valeurs manquantes expliquées (V de Cramér : " + doc("cramers_v") + ") et anomalies (règle IQR colonne "
                     "par colonne + Isolation Forest multivarié). Ces mesures sont ensuite interprétées par le LLM (étape 3).",
                     ev, "code", None, terms=[t], audit=audit_seq("profiling_completed"))
    done, fallback = AGENT_RUN.get("done", []), AGENT_RUN.get("fallback", [])
    add_decision(3, "Data Profiler Agent", "investigations", "investigations du Profiler",
                 f"{len(done) + len(fallback)} investigation(s) : {len(done)} choisie(s) par le LLM, {len(fallback)} faite(s) par le superviseur",
                 "Le LLM choisit quels outils lancer sur quelles tables ; le superviseur contrôle chaque décision avant exécution "
                 f"({doc('validate_decision')}) et réalise lui-même les investigations obligatoires que l'agent n'a pas faites.",
                 {"par le LLM": ", ".join(f"{a} sur {t}" for a, t in done) or "aucune",
                  "par le superviseur": ", ".join(f"{a} sur {t}" for a, t in fallback) or "aucune"},
                 "agent" if done and not fallback else "repli" if fallback else "code", None,
                 refused=refusals("decision_rejected", "profiler_agent") if fallback else [], terms=["investigation", "profiler"],
                 audit=audit_seq("investigation_completed"))


@ledger_block
def ledger_domain():
    ev = next((e["details"] for e in reversed(AUDIT.events) if e["action"] == "domain_understood"), {})
    add_decision(3, "Domain & Contract Agent", "domaine métier", DOMAIN, f"le domaine métier est « {DOMAIN} »",
                 "Le LLM a lu la structure des données (noms de fichiers, de tables, de colonnes et quelques valeurs) et a nommé le "
                 "métier. Il peut aussi proposer des corrections du contrat ; le code n'accepte que celles qui sont cohérentes "
                 f"avec les données. Règle : {doc('understand_domain')}",
                 {"source": ev.get("source"), "corrections du contrat acceptées": len(ev.get("contract_corrections_accepted", [])),
                  "corrections du contrat refusées": len(ev.get("contract_corrections_rejected", []))},
                 ev.get("source", "LLM"), "Sans réponse valide du LLM, le domaine aurait été déduit des noms de tables (repli).",
                 terms=["domaine", "métier"], audit=audit_seq("domain_understood"))


@ledger_block
def ledger_findings():
    for f in PROFILING_REPORT.itertuples():
        where = f.table if f.colonne in ("*", None) else f"{f.table}.{f.colonne}"
        allowed = ", ".join(ALLOWED_ACTIONS.get(f.dimension, []))
        llm = f.source == "LLM"
        add_decision(3, "Data Profiler Agent", "constat de qualité", f"constat {f.id}",
                     f"constat {f.id} sur {where} ({f.dimension}) : gravité « {f.severity} », action « {f.action} »",
                     (f"Interprétation du LLM : {f.interpretation} " if llm else "") +
                     f"Le constat est mesuré par les outils du Profiler (étape 2). L'action est choisie parmi celles que la politique "
                     f"autorise pour la dimension « {f.dimension} » : {allowed}. Une gravité « blocking » n'est permise que pour "
                     f"{', '.join(sorted(BLOCKING_ALLOWED))}. Chaque chiffre cité par le LLM doit figurer dans la mesure "
                     f"({doc('is_grounded')}).",
                     {"mesure": f.constat, "action": f.action, "gravité": f.severity}, f.source,
                     None if llm else "Avec une interprétation valide du LLM, l'action aurait pu être choisie par l'IA ; ici la "
                                      f"règle de repli associe la dimension « {f.dimension} » à l'action « {f.action} ».",
                     refused=[],
                     terms=[f.id, f.table, f.colonne if f.colonne != "*" else None], audit=audit_seq("interpretation_completed"))


@ledger_block
def ledger_quality():
    applied = set(REVIEW["approved"])
    effects = dict(zip(EXECUTION["id"], EXECUTION["effect"])) if len(EXECUTION) else {}
    for p in CLEANING_PLAN.itertuples():
        risk = REVIEW["set_aside"].get(p.id)
        col = None if p.colonne == "*" else p.colonne
        where = p.table if col is None else f"{p.table}.{col}"
        policy = VALUE_POLICY["imputable"].get((p.table, col)) if col else None
        method = {"median": "médiane des lignes semblables", "infer": "catégorie déduite des autres colonnes",
                  "label": f"libellé « {NOT_FILLED} »"}.get((policy or {}).get("method"), None)
        why = (f"Correction du catalogue : {CORRECTIONS[p.correction][1]}. Elle a d'abord été testée sur une copie (bac à sable) : "
               f"effet mesuré {p.effet_simulé}. Justification : {p.justification}.")
        if method:
            why += (f" Méthode : {method} — cause des manques trouvée par le Profiler : {policy['cause']}. "
                    f"Règle : {doc('missing_method')}")
        why += f" Validation : {doc('review_plan')}"
        cf = (f"Elle n'aurait pas été appliquée en cas de perte d'information, si le test ne la validait pas, ou si plus de "
              f"{xai_num(MAX_ROWS_REMOVED_PCT)} % des lignes étaient supprimées.")
        if method == "médiane des lignes semblables":
            cf += f" Avec plus de {xai_num(MAX_IMPUTE_PCT)} % de manques, ou un manque structurel, la colonne serait restée vide."
        elif policy and policy.get("method") == "label":
            cf += (f" Si le manque avait été aléatoire et inférieur à {xai_num(MAX_IMPUTE_PCT)} %, la catégorie aurait été déduite "
                   "des autres colonnes.")
        add_decision(4, "Data Quality Agent", "correction", f"correction {p.id}",
                     f"correction {p.id} « {p.correction} » sur {where} : " + ("appliquée" if p.id in applied else "mise de côté"),
                     why, {"règle visée": p.règle, "effet testé": str(p.effet_simulé),
                           "cellules ou lignes touchées": effects.get(p.id), "manques (%)": (policy or {}).get("missing_pct"),
                           "risque": ", ".join(risk) if risk else "faible", "constats du Profiler": ", ".join(p.findings or [])},
                     p.décidé_par, cf, refused=[] if p.décidé_par == "agent" else refusals("decision_rejected", "quality_agent", limit=2),
                     terms=[p.id, p.table, col, p.candidat], audit=audit_seq("correction_applied", contains=p.id))
    for o in OTHER_TREATMENTS.itertuples():
        add_decision(4, "Data Quality Agent", "correction écartée", f"correction écartée {o.élément}",
                     f"la correction candidate {o.élément} sur {o.table} n'est pas appliquée : la donnée reste signalée",
                     f"Justification : {o.justification}.", {"traitement": o.traitement}, "agent",
                     "Elle aurait été proposée si l'agent avait jugé son effet testé utile et sans risque.",
                     terms=[o.élément, o.table], audit=audit_seq("cleaning_plan_built"))
    before = RULES_BEFORE.set_index("rule")["violations"]
    for r in RULES_AFTER[RULES_AFTER["violations"] > 0].itertuples():
        add_decision(4, "Data Quality Agent", "règle encore signalée", f"règle {r.rule}",
                     f"la règle « {r.description} » ({r.table}) reste signalée sur {xai_num(r.violations)} ligne(s)",
                     "Aucune correction du catalogue ne la lève sans risque (ou la correction a été mise de côté) : la donnée n'est "
                     "pas modifiée, chaque ligne concernée est marquée dans la colonne _dq_flags pour l'analyse.",
                     {"lignes avant nettoyage": int(before.get(r.rule, r.violations)), "lignes après": r.violations,
                      "gravité": r.severity, "dimension": r.dimension}, "code",
                     "Une correction sans risque du catalogue (testée sur une copie) l'aurait levée.", terms=[r.rule, r.table],
                     audit=audit_seq("quality_completed"))
    add_decision(4, "Data Quality Agent", "statut qualité", "statut qualité",
                 f"statut qualité « {STATUS} » : score moyen {xai_num(round(SCORES_BEFORE.mean(), 2))} → "
                 f"{xai_num(round(SCORES_AFTER.mean(), 2))} / 100",
                 f"Règle : « blocked » s'il reste une violation bloquante, « ready_with_warnings » s'il reste des violations "
                 f"signalées, « ready » sinon. Score par dimension : {doc('dq_scores')}",
                 {f"score {k} (avant → après)": f"{xai_num(round(SCORES_BEFORE[k], 2))} → {xai_num(round(SCORES_AFTER[k], 2))}"
                  for k in SCORES_AFTER.index}, "code",
                 "Le statut serait « blocked » si une règle bloquante (unicité du grain, intégrité) restait violée : le modèle en "
                 "étoile n'aurait pas été construit.", terms=["qualité", "score"], audit=audit_seq("quality_completed"))


@ledger_block
def ledger_etl():
    for name, spec in ETL_TEMPLATES.items():
        r = ETL_RESULTS.get(name, {})
        add_decision(5, "ETL Agent", "table du modèle en étoile", name,
                     f"« {name} » est construite comme {'table de faits' if spec['type'] == 'fait' else 'dimension'}, une ligne par "
                     f"{' + '.join(spec.get('grain') or ['?'])}",
                     f"{spec.get('description', '')}. Règle de conception : {doc('design_star_schema')} Tests : {doc('test_table')}",
                     {"lignes": r.get("rows"), "tests réussis": f"{sum(r.get('tests', {}).values())} / {len(r.get('tests', {}))}",
                      "dépend de": ", ".join(spec.get("depends_on") or []) or "aucune table",
                      "liens": ", ".join(f"{c} → {t}" for c, (t, k) in (spec.get("fks") or {}).items())[:300] or "aucun"},
                     r.get("decided_by", "code"), "Une table qui échoue à un test n'entre pas dans l'entrepôt et le pipeline s'arrête.",
                     terms=[name, re.sub(r"^(dim|fact)_", "", name)], audit=audit_seq("template_built", contains=name))
    for d in DERIVED.itertuples():
        add_decision(5, "ETL Agent", "indicateur dérivé", d.colonne, f"la colonne « {d.colonne} » est calculée : {d.calcul}",
                     f"Règle : {doc('derive_time_indicators')}", {"table": d.table, "type": d.type}, "code",
                     "Elle n'aurait pas été créée si la seconde date ne suivait pas la date de référence dans la grande majorité des lignes.",
                     terms=[d.table], audit=audit_seq("staging_loaded"))


@ledger_block
def ledger_prep_orchestration():
    r = DATA_PREP_RESULT
    add_decision(6, "Sous-orchestrateur LangGraph (partie 1)", "orchestration", "Data Preparation Agent",
                 f"préparation terminée avec le statut « {r['status']} »" + (f" : {r.get('error')}" if r.get("error") else ""),
                 f"Chaque agent est un nœud du graphe ; après chaque nœud, une arête conditionnelle continue ou s'arrête. "
                 f"{doc('graph_node')}",
                 node_history(r), "code",
                 "Le pipeline se serait arrêté au premier nœud en échec ou bloqué (ex. qualité bloquante).",
                 terms=["préparation", "data preparation"], audit=audit_seq("data_preparation_finished"))


# ---------------------------------------------------------------- partie 2 · BI & Insight Agent
@ledger_block
def ledger_bridge():
    for r in globals().get("REBUILT_DATES", []):
        src = r.get("how") or " + ".join(r["parts"].values())
        add_decision(7, "Pont (partie 2)", "date reconstituée", r["column"], f"la date « {r['column']} » est reconstituée ({src})",
                     "Une date répartie sur plusieurs colonnes (année, mois, jour) ou restée en texte n'est pas analysable mois par "
                     "mois : le pont la reconstitue dans une copie de travail (l'entrepôt de la partie 1 n'est pas modifié).",
                     {"table": r["table"], "source": src}, "code", None, terms=[r["table"]], audit=audit_seq("dates_rebuilt"))
    ev = SECTOR_EVIDENCE.set_index("secteur")
    chosen = BI_SECTORS or []
    add_decision(7, "Base de connaissances (RAG)", "secteur métier", "secteur",
                 f"secteur(s) retenu(s) : {', '.join(chosen) or 'aucun (mode générique)'}",
                 f"Trois signaux : proximité de sens entre le dataset et chaque secteur (RAG), nombre de KPI du secteur calculables, "
                 f"et KPI dont les colonnes portent un nom attendu. Décision : {sector_reason}. Le superviseur n'accepte un secteur que "
                 f"si au moins {MIN_SECTOR_KPIS} KPI et {xai_num(int(MIN_SECTOR_COVERAGE * 100))} % de ses KPI retrouvent des colonnes "
                 f"au nom attendu, sur au moins {MIN_SECTOR_COLUMNS} colonnes différentes.",
                 {f"{s} (proximité · KPI confirmés · colonnes · score)":
                      f"{xai_num(row['proximité'])} · {int(row['kpi_confirmés'])}/{int(row['kpi_total'])} · "
                      f"{int(row['colonnes_confirmées'])} · {xai_num(row['score'])}" for s, row in ev.iterrows()},
                 sector_source,
                 "Sans secteur assez confirmé, le pipeline serait passé en mode générique : KPI génériques + KPI proposés par l'agent.",
                 refused=refusals("decision_rejected", "bi_knowledge") if sector_source != "LLM" else [],
                 terms=["secteur", *chosen], audit=audit_seq("sector_decided"))
    for r in KPI_REFERENCES:
        if not r["feasible"]:
            add_decision(7, "Base de connaissances (RAG)", "KPI non calculable", r["name"],
                         f"le KPI « {r['name']} » ({r['id']}) n'est pas calculé : il n'est pas calculable sur ce dataset",
                         f"Aucune colonne ne peut jouer le rôle demandé par son emplacement {', '.join(r['missing'])} : un KPI dont "
                         f"un rôle n'existe pas dans les données n'est jamais inventé.", {"rôle(s) manquant(s)": ", ".join(r["missing"])},
                         "code", f"Il aurait été calculé si une colonne compatible avec le rôle {', '.join(r['missing'])} existait.",
                         terms=[r["id"]], audit=audit_seq("kpi_references_selected"))


@ledger_block
def ledger_kpis():
    refs = {r["id"]: r for r in KPI_REFERENCES}
    in_catalog = set(KPI_CATALOG["id"])
    cat = KPI_CATALOG.set_index("id")
    for kid, b in BINDINGS.items():
        card = KB_BY_ID[kid]
        ev, ranking = {}, []
        for slot, (t, c) in b["slots"].items():
            cands = (refs.get(kid) or {}).get("candidates", {}).get(slot, [])[:3]
            if cands:
                ranking.append(f"{slot} : " + " ; ".join(f"{x['column']} (score {xai_num(round(x['score'], 3))}"
                                                         f"{', nom attendu' if x.get('name_match') else ''})" for x in cands))
            ev[f"colonne pour « {slot} »"] = f"{t}.{c}"
        for kind, vals in b["params"].items():
            for slot, v in vals.items():
                ev[f"paramètre {kind} ({slot})"] = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
        if ranking:
            ev["candidates classées par la recherche sémantique"] = " | ".join(ranking)
        if kid in in_catalog:
            row = cat.loc[kid]
            ev.update({"valeur": fmt_value(row["value"], row["unit"]), "statut": row["status"], "fiabilité": row["reliability"],
                       "tests": ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in row["tests"].items())})
        src = b["source"]
        why = {"évidente": "Chaque emplacement a trouvé une colonne au nom attendu (confiance 1) et aucun paramètre ne demandait "
                           "de jugement : la liaison est faite par le code.",
               "LLM": f"Le LLM a choisi les colonnes et les valeurs parmi celles qui existent : « {b['reason']} ». Le superviseur a "
                      "vérifié le rôle et l'accès des colonnes, et que les valeurs choisies sont observées (jamais toutes à la fois)."}.get(
            src, f"Raison : {b['reason'] or src}.")
        fate = ("dans le catalogue" if kid in in_catalog else
                "retiré : doublon" if kid in DUPLICATES else
                f"retiré : remplacé par {REPLACED[kid]}" if kid in REPLACED else
                f"en échec : {FAILED.get(kid)}" if kid in FAILED else "retiré")
        add_decision(8, "BI Semantic & KPI Agent", "KPI", card["name"],
                     f"KPI « {card['name']} » = {readable(card, b)} ({fate})",
                     f"{why} Calcul : la formule est compilée en SQL, puis recalculée indépendamment en pandas ; les deux doivent "
                     f"être égaux, et la valeur doit respecter les bornes de son unité. Règle des bornes : {doc('check_bounds')}",
                     ev, src, "Une autre colonne aurait été choisie si elle avait un meilleur score de proximité (ou le nom attendu) "
                              "tout en ayant le rôle demandé ; le KPI aurait été refusé si le double calcul ou les bornes échouaient.",
                     refused=refusals("binding_rejected", "kpi_agent", contains=kid), terms=[kid, card["name"]],
                     audit=audit_seq("kpi_computed", contains=kid))
    for kid, reason in DROPPED.items():
        name = KB_BY_ID[kid]["name"] if kid in KB_BY_ID else kid
        add_decision(8, "BI Semantic & KPI Agent", "KPI écarté", name, f"le KPI « {name} » ({kid}) est écarté",
                     f"Raison : {reason}.", {}, "LLM" if not reason.startswith("repli") else "repli",
                     "Il aurait été gardé si une liaison sûre (colonnes compatibles et paramètres décidés) avait été trouvée.",
                     refused=refusals("binding_rejected", "kpi_agent", contains=kid), terms=[kid], audit=audit_seq("kpis_bound"))
    for kid in DUPLICATES:
        add_decision(8, "BI Semantic & KPI Agent", "KPI retiré (doublon)", KB_BY_ID[kid]["name"],
                     f"le KPI « {KB_BY_ID[kid]['name']} » ({kid}) est retiré du catalogue",
                     "Il donne la même valeur sur les mêmes colonnes qu'un autre KPI : on garde la fiche sectorielle, puis la plus pertinente.",
                     {}, "code", None, terms=[kid], audit=audit_seq("kpi_catalog_built"))
    for g, k in REPLACED.items():
        add_decision(8, "BI Semantic & KPI Agent", "KPI retiré (remplacé)", KB_BY_ID[g]["name"],
                     f"le KPI générique « {KB_BY_ID[g]['name']} » est remplacé par « {KB_BY_ID[k]['name']} »",
                     "Un KPI générique est retiré quand son équivalent sectoriel, plus précis, est calculé.", {}, "code", None,
                     terms=[g, k], audit=audit_seq("kpi_catalog_built"))
    errs = globals().get("proposal_errors") or []
    if PROPOSALS or errs:
        add_decision(8, "BI Semantic & KPI Agent", "KPI proposés par l'agent", "KPI proposés par l'agent",
                     f"{len(PROPOSALS)} KPI proposé(s) par l'agent accepté(s), {len(errs)} refusé(s)",
                     "La base de connaissances ne couvre pas tout : le LLM peut proposer des KPI dans le même langage fermé. Le "
                     "superviseur vérifie colonnes, conditions, valeurs observées, nom cohérent avec la formule et tests ; un KPI "
                     "proposé reste « à confirmer » par un humain.",
                     {"acceptés": ", ".join(f"{k} « {c['name']} »" for k, c in PROPOSALS.items()) or "aucun"}, "agent", None,
                     refused=errs[:4], terms=list(PROPOSALS), audit=audit_seq("kpis_proposed"))


@ledger_block
def ledger_analysis():
    for kid, why in SKIPPED_SERIES.items():
        add_decision(9, "BI Analyst Agent", "série écartée", f"série {kid}", f"la série mensuelle de {kid} n'est pas analysée",
                     f"Raison : {why}. Deux séries qui racontent la même histoire produiraient des signaux en double.", {}, "code",
                     None, terms=[kid], audit=audit_seq("series_prepared"))
    thresholds = {"tendance": [("p", "<", 0.05), ("variation", ">=", 0.05)], "variation récente": [("z", ">=", 2.5), ("variation", ">=", 0.05)],
                  "sur un an": [("variation", ">=", 0.10)], "anomalie": [("z", ">=", 3.5), ("variation", ">=", 0.10)],
                  "rupture": [("t", ">=", 4.0), ("variation", ">=", 0.10)]}
    names = {"p": "p-valeur", "z": "z", "t": "t de Welch", "variation": "variation relative"}
    for f in FACTS.values():
        if f["type"] == "valeur":
            continue
        test, ev = f.get("test") or {}, dict(f.get("chiffres", {}))
        cf = None
        if f["type"] in thresholds and test:
            parts = []
            for key, op, lim in thresholds[f["type"]]:
                if key in test:
                    val = abs(test[key]) if key != "p" else test[key]
                    shown = f"{xai_num(round(val * 100, 1))} %" if key == "variation" else xai_num(val)
                    limit = f"{xai_num(lim * 100)} %" if key == "variation" else xai_num(lim)
                    parts.append(f"{names[key]} {'≥' if op == '<' else '<'} {limit} (ici {shown})")
                    ev[names[key]] = shown
            cf = "Ce signal aurait été écarté si " + " ou si ".join(parts) + "."
            ev["méthode"] = test.get("méthode")
            why = (f"Test statistique déterministe (aucun LLM) : {test.get('méthode')}. Seuils : {test.get('seuils')}. "
                   f"Un signal n'est retenu que s'il est à la fois statistiquement net et assez grand pour compter.")
        elif f["type"] == "segment":
            why = (f"Découpage par segment : pour chaque axe possible, le code calcule le KPI par segment et vérifie que les "
                   f"segments se réconcilient avec la valeur du catalogue ; l'axe retenu est celui qui discrimine le plus. "
                   f"Les axes « jumeaux » d'une colonne de la formule sont écartés.")
        elif f["type"] == "contribution":
            why = ("Contribution à une variation : le code compare deux fenêtres de temps segment par segment et mesure la part "
                   "de la variation globale expliquée par chaque segment.")
        else:
            why = "Fait calculé par le code."
        add_decision(9, "BI Analyst Agent", f"fait ({f['type']})", f"fait {f['id']}",
                     f"fait {f['id']} ({f['type']}) : {f['texte']}", why, ev, "code", cf,
                     terms=[f["id"], f["kpi"], f.get("label")], audit=audit_seq("statistical_signals"))
        if f["type"] in CHANGE_LABELS and len(f["nombres"]) >= 2:
            LEDGER[-1]["avant_après"] = f["nombres"][:2]          # ordre des deux valeurs (contrôle de la reformulation)
            LEDGER[-1]["sens"] = f.get("sens")
    for inv in INVESTIGATIONS:
        axe = ".".join(inv["axe"]) if isinstance(inv["axe"], (list, tuple)) else inv["axe"]
        add_decision(9, "BI Analyst Agent", "investigation", f"investigation {inv['fait']} par {axe}",
                     f"le fait {inv['fait']} est creusé selon l'axe {axe} (nouveau fait {inv.get('résultat')})",
                     f"Raison : {inv['pourquoi']}. Le LLM choisit les signaux à creuser et l'axe ; le code vérifie que le fait et l'axe "
                     f"existent, puis exécute le découpage.", {"fait creusé": inv["fait"], "résultat": inv.get("résultat")},
                     inv.get("source", "code"), None, refused=(globals().get("inv_errors") or [])[:3],
                     terms=[inv["fait"], inv.get("résultat"), axe.split(".")[-1]], audit=audit_seq("investigations"))
    checks = ("les faits cités existent ; chaque nombre du texte figure dans ces faits ; le sens (hausse/baisse) du titre et du "
              "texte est celui des faits ; les segments nommés figurent dans les faits ; pas de redite d'un KPI ; une part de "
              "variation n'est jamais présentée comme une hausse")
    for i in INSIGHTS:
        ev = {f"fait {fid}": FACTS[fid]["texte"][:240] for fid in i["faits"] if fid in FACTS}
        ev["type"] = i["type"]
        add_decision(9, "BI Analyst Agent", "insight", f"insight {i['id']}", f"insight {i['id']} : « {i['titre']} »",
                     (f"Rédigé par le LLM à partir des faits {', '.join(i['faits'])}, puis vérifié par le code : {checks}."
                      if i["source"] == "LLM" else
                      f"Rédigé par le code à partir des faits {', '.join(i['faits'])} (signal important non couvert par le LLM, ou "
                      f"réponse du LLM refusée deux fois)."), ev, i["source"],
                     "Un insight du LLM qui aurait cité un chiffre absent de ses faits, un fait inexistant ou un sens contraire aurait "
                     "été refusé, renvoyé une fois au LLM avec la raison, puis remplacé par une rédaction du code.",
                     refused=(globals().get("insight_errors") or [])[:3], terms=[i["id"], *i["faits"]],
                     audit=audit_seq("insights_written"))


@ledger_block
def ledger_dashboard():
    name = lambda k: KB_BY_ID[k]["name"] if k in KB_BY_ID else k
    add_decision(10, "Dashboard Generator Agent", "mise en page", "dashboard",
                 f"dashboard « {LAYOUT['titre']} » : chiffre principal « {name(LAYOUT['hero'])} », {len(LAYOUT['tuiles'])} tuiles, "
                 f"{len(LAYOUT['graphiques'])} graphiques, {len(LAYOUT['decoupages'])} découpages",
                 "Le LLM choisit et ordonne parmi des candidats préparés par le code (valeurs déjà formatées) ; le superviseur vérifie "
                 "les identifiants, les limites, un graphique seulement pour un KPI qui a une série, aucun chiffre dans le titre, et "
                 "ajoute la courbe ou le découpage de chaque insight qui en a besoin.",
                 {"chiffre principal": name(LAYOUT["hero"]), "tuiles": ", ".join(map(name, LAYOUT["tuiles"])),
                  "graphiques": ", ".join(map(name, LAYOUT["graphiques"])), "découpages": ", ".join(LAYOUT["decoupages"])},
                 layout_source, "Sans réponse valide du LLM, la mise en page par défaut du code aurait été utilisée.",
                 refused=(globals().get("layout_errors") or [])[:3], terms=["dashboard", "tableau de bord", LAYOUT["hero"]],
                 audit=audit_seq("layout_decided"))


@ledger_block
def ledger_bi_orchestration():
    r = globals().get("BI_RESULT")
    if not r:
        return
    add_decision(11, "Sous-orchestrateur LangGraph (partie 2)", "orchestration", "BI & Insight Agent",
                 f"BI & Insight Agent terminé avec le statut « {r['status']} »" + (f" : {r.get('error')}" if r.get("error") else ""),
                 "Le graphe enchaîne pont → KPI → analyste → dashboard ; chaque étape n'est validée que si son point de contrôle "
                 "(ok7 … ok10) est vrai, sinon le pipeline s'arrête proprement avec la raison.",
                 node_history(r), "code", None,
                 terms=["bi insight", "orchestrateur bi"], audit=audit_seq("bi_insight_finished"))


@ledger_block
def ledger_global_orchestration():
    r = globals().get("BIFLOW_RESULT")
    if not r:
        return
    add_decision(13, "BI Orchestrator global", "orchestration", "pipeline complet",
                 f"pipeline complet terminé avec le statut « {r['status']} »" + (f" : {r.get('error')}" if r.get("error") else ""),
                 "L'orchestrateur global enchaîne préparation → BI & insights → explicabilité ; il s'arrête à la première partie qui "
                 "échoue, mais construit toujours l'explicabilité, pour pouvoir expliquer l'arrêt.",
                 node_history(r), "code", None,
                 terms=["pipeline", "orchestrateur global", "de a à z"], audit=audit_seq("biflow_finished"))


LEDGER_BUILDERS = [ledger_contract, ledger_relations, ledger_profiling, ledger_domain, ledger_findings, ledger_quality, ledger_etl,
                   ledger_prep_orchestration, ledger_bridge, ledger_kpis, ledger_analysis, ledger_dashboard,
                   ledger_bi_orchestration, ledger_global_orchestration]


def build_ledger() -> pd.DataFrame:
    LEDGER.clear()
    LEDGER_ERRORS.clear()
    for b in LEDGER_BUILDERS:
        b()
    return pd.DataFrame(LEDGER)


DECISIONS = build_ledger()
AUDIT.log("xai_agent", "decision_ledger_built", {"decisions": len(DECISIONS), "by_step": DECISIONS["étape"].value_counts().to_dict(),
                                                 "errors": LEDGER_ERRORS}, level="INFO" if not LEDGER_ERRORS else "WARNING")
print(f"Registre : {len(DECISIONS)} décisions · " + " · ".join(f"étape {s} : {n}" for s, n in
                                                              DECISIONS["étape"].value_counts().sort_index().items()))
print("Blocs non disponibles :", LEDGER_ERRORS or "aucun")
(DECISIONS.assign(décidé_par=DECISIONS["décidé_par"])
 .groupby(["étape", "décidé_par"]).size().rename("décisions").reset_index()
 .assign(étape=lambda d: d["étape"].map(lambda s: f"{s}. {XAI_STEPS.get(s, '')}")))
