import inspect as _inspect
import unicodedata

XAI_DIR = RUN_DIR / "xai"
XAI_DIR.mkdir(exist_ok=True)
XAI_STEPS = {1: "Contract and ingestion", 2: "Profiler tools", 3: "Domain and diagnosis (LLM)", 4: "Quality and cleaning",
             5: "ETL: star schema", 6: "Preparation orchestration", 7: "Bridge and knowledge base",
             8: "KPI agent", 9: "Analyst agent", 10: "Dashboard agent", 11: "BI orchestration", 12: "Explainability (XAI)",
             13: "Global orchestrator"}
DECIDED_BY = {
    "code": "code rule", "rule": "code rule", "obvious": "code rule (obvious binding)",
    "LLM": "LLM, verified by the supervisor", "agent": "LLM, verified by the supervisor",
    "fallback": "supervisor fallback (LLM answer missing or rejected)",
    "proposed by the agent": "LLM (proposed KPI), verified by the supervisor — to be confirmed by a human",
    "policy": "automatic risk policy", "human": "human validation",
}
SEM_LABEL = {"id": "identifier", "category": "category", "datetime": "date", "numeric": "decimal measure",
             "integer": "integer", "text": "free text", "zip": "postal code", "geo": "GPS coordinate"}


def decided_by(source) -> str:
    s = str(source or "code")
    if s.startswith("fallback"):
        return DECIDED_BY["fallback"]
    if s.startswith("policy"):
        return DECIDED_BY["policy"]
    return DECIDED_BY.get(s, s)


def xai_num(v) -> str:
    """Readable number in English format (1,234 · 12.35)."""
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    if isinstance(v, (int, np.integer)) or (isinstance(v, (float, np.floating)) and float(v).is_integer() and abs(v) < 1e15):
        return f"{int(v):,}"
    if isinstance(v, (float, np.floating)):
        return (f"{v:,.4f}" if abs(v) < 1 else f"{v:,.2f}").rstrip("0").rstrip(".")
    return str(v)


def doc(name: str) -> str:
    """Documentation of a pipeline function: the global explanation comes from the code itself (always up to date)."""
    fn = globals().get(name)
    text = _inspect.getdoc(fn) if callable(fn) else None
    return " ".join((text or "").split())


def audit_seq(action: str, agent: str | None = None, contains: str | None = None) -> list[int]:
    """Number of the last matching event of the audit log (traceability)."""
    for e in reversed(AUDIT.events):
        if e["action"] == action and (agent is None or e["agent"] == agent) and \
                (contains is None or contains in canonical_json(e["details"])):
            return [e["seq"]]
    return []


def refusals(action: str, agent: str | None = None, contains: str | None = None, limit: int = 3) -> list[str]:
    """LLM answers rejected by the supervisor (last run), with the reason for the rejection."""
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
NODE_STATUS = {"running": "finished, moving on", "success": "finished (success)", "failed": "failed", "blocked": "blocked"}


def node_history(result: dict) -> dict:
    """Readable history of an orchestrator: "running" after a node means "finished, moving on to the next one"."""
    return {h["node"]: f"{NODE_STATUS.get(h['status'], h['status'])} · {xai_num(h['seconds'])} s" for h in result.get("history", [])}


def add_decision(step: int, agent: str, subject: str, obj: str, decision: str, why: str, evidence: dict | None = None,
                 by: str = "code", counterfactual: str | None = None, refused: list | None = None, terms=(),
                 audit: list | None = None) -> str:
    rid = f"D{len(LEDGER) + 1:03d}"
    LEDGER.append({"id": rid, "step": step, "agent": agent, "subject": subject, "object": str(obj), "decision": decision,
                   "why": why, "evidence": {k: xai_num(v) if not isinstance(v, str) else v for k, v in (evidence or {}).items()
                                            if v is not None and v != ""},
                   "decided_by": decided_by(by), "counterfactual": counterfactual, "rejections": list(refused or []),
                   "terms": sorted({str(t) for t in [obj, *terms] if t}), "audit": audit or []})
    return rid


def ledger_block(fn):
    """Each block of the ledger is independent: a missing part (pipeline stopped) does not prevent the others."""
    def run():
        try:
            fn()
        except Exception as exc:
            LEDGER_ERRORS.append(f"{fn.__name__}: {type(exc).__name__}: {exc}")
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
        where = (f"it contains {len(dates)} date(s)" if dates else "it contains no date") + \
                (f", {len(measures)} measure(s)" if measures else ", no measure of its own") + \
                (", and other tables refer to it" if t in parents else ", and no table refers to it")
        cf = ("It would have been a dimension if it had only been referenced by other tables, without dates or measures of its own."
              if role == "fact" else "It would have been a fact table if it had contained event dates or measures "
                                     "without being a mere reference for other tables.")
        add_decision(1, "Contract Agent", "table role", t,
                     f"the table “{t}” is a {role} table" if role == "fact" else f"the table “{t}” is a dimension",
                     f"Rule: {doc('infer_roles')} Here, {where}.",
                     {"file": spec.get("file"), "rows": stats.get(t, {}).get("rows"), "columns": len(cols),
                      "identifier (grain)": " + ".join(spec["grain"]) if spec["grain"] else "none (several rows per value)",
                      "dates": ", ".join(dates[:6]) or "none", "measures": ", ".join(measures[:6]) or "none"},
                     "code", cf, terms=[f"table {t}"], audit=audit_seq("contract_inferred"))
    types = TYPE_REPORT.set_index(["table", "column"]) if "TYPE_REPORT" in globals() else None
    for t, spec in DATA_CONTRACT.items():
        for c, sem in spec["columns"].items():
            ev = {"type retained": SEM_LABEL.get(sem, sem)}
            fmt = INFERRED["formats"].get(f"{t}.{c}")
            if fmt:
                ev["format read"] = str(fmt)
            if types is not None and (t, c) in types.index:
                r = types.loc[(t, c)]
                ev.update({"filled values": int(r["non_null"]), "values not converted": int(r["failed"])})
            add_decision(1, "Contract Agent", "column type", f"{t}.{c}", f"the column “{c}” ({t}) is of type {SEM_LABEL.get(sem, sem)}",
                         f"Rule: {doc('infer_type')} A value that does not match this type becomes empty and is traced (step 4.1).",
                         ev, "code", None, terms=[c], audit=audit_seq("contract_inferred"))


@ledger_block
def ledger_relations():
    for r in INFERRED["relationship_details"]:
        weak = r.get("inclusion_pct", 100) < 95 or not r.get("same_name", True)
        add_decision(2, "Contract Agent / Profiler", "link between tables", f"{r['child']}.{r['fk']} → {r['parent']}.{r['pk']}",
                     f"“{r['child']}” is linked to “{r['parent']}” by the column “{r['fk']}”"
                     + (" (link to aggregate: several rows per key)" if r.get("aggregate") else ""),
                     f"Rule: {doc('infer_relationships')}",
                     {"values found in the linked table (%)": r.get("inclusion_pct"), "same column name": r.get("same_name"),
                      "to check": "yes" if weak else "no"}, "code",
                     "A link for which less than 95% of the values are found, or whose names differ, is flagged \"to check\" "
                     "and submitted to the Domain Agent (step 3).", terms=[r["fk"], r["child"], r["parent"]],
                     audit=audit_seq("contract_inferred"))


@ledger_block
def ledger_profiling():
    labels = {"missing_cells_%": "missing cells (%)", "invalid_values": "values not matching the type",
              "unique_grain": "unique identifier", "exact_duplicates": "duplicate rows", "IF_anomalies": "atypical rows (Isolation Forest)",
              "IQR_extremes": "extreme values (> 3 IQR)"}
    for t, row in HEALTH.iterrows():
        ev = {"rows": row.get("rows"), "columns": row.get("columns"),
              **{labels[k]: ("—" if row.get(k) is None else row.get(k)) for k in labels if k in row}}
        add_decision(2, "Data Profiler (tools)", "table health", f"health of {t}",
                     f"quantified diagnosis of the table “{t}”",
                     "Measurements made by the Profiler tools, without LLM: column profile, uniqueness and duplicates, links between "
                     "tables, explained missing values (Cramér's V: " + doc("cramers_v") + ") and anomalies (IQR rule column "
                     "by column + multivariate Isolation Forest). These measurements are then interpreted by the LLM (step 3).",
                     ev, "code", None, terms=[t], audit=audit_seq("profiling_completed"))
    done, fallback = AGENT_RUN.get("done", []), AGENT_RUN.get("fallback", [])
    add_decision(3, "Data Profiler Agent", "investigations", "Profiler investigations",
                 f"{len(done) + len(fallback)} investigation(s): {len(done)} chosen by the LLM, {len(fallback)} done by the supervisor",
                 "The LLM chooses which tools to run on which tables; the supervisor checks each decision before execution "
                 f"({doc('validate_decision')}) and itself carries out the mandatory investigations the agent did not do.",
                 {"by the LLM": ", ".join(f"{a} on {t}" for a, t in done) or "none",
                  "by the supervisor": ", ".join(f"{a} on {t}" for a, t in fallback) or "none"},
                 "agent" if done and not fallback else "fallback" if fallback else "code", None,
                 refused=refusals("decision_rejected", "profiler_agent") if fallback else [], terms=["investigation", "profiler"],
                 audit=audit_seq("investigation_completed"))


@ledger_block
def ledger_domain():
    ev = next((e["details"] for e in reversed(AUDIT.events) if e["action"] == "domain_understood"), {})
    add_decision(3, "Domain & Contract Agent", "business domain", DOMAIN, f"the business domain is “{DOMAIN}”",
                 "The LLM read the structure of the data (names of files, tables, columns and a few values) and named the "
                 "business. It can also propose corrections to the contract; the code only accepts those that are consistent "
                 f"with the data. Rule: {doc('understand_domain')}",
                 {"source": ev.get("source"), "contract corrections accepted": len(ev.get("contract_corrections_accepted", [])),
                  "contract corrections rejected": len(ev.get("contract_corrections_rejected", []))},
                 ev.get("source", "LLM"), "Without a valid answer from the LLM, the domain would have been deduced from the table names (fallback).",
                 terms=["domain", "business"], audit=audit_seq("domain_understood"))


@ledger_block
def ledger_findings():
    for f in PROFILING_REPORT.itertuples():
        where = f.table if f.column in ("*", None) else f"{f.table}.{f.column}"
        allowed = ", ".join(ALLOWED_ACTIONS.get(f.dimension, []))
        llm = f.source == "LLM"
        add_decision(3, "Data Profiler Agent", "quality finding", f"finding {f.id}",
                     f"finding {f.id} on {where} ({f.dimension}): severity “{f.severity}”, action “{f.action}”",
                     (f"LLM interpretation: {f.interpretation} " if llm else "") +
                     f"The finding is measured by the Profiler tools (step 2). The action is chosen among those the policy "
                     f"allows for the dimension “{f.dimension}”: {allowed}. A “blocking” severity is only allowed for "
                     f"{', '.join(sorted(BLOCKING_ALLOWED))}. Every figure cited by the LLM must appear in the measurement "
                     f"({doc('is_grounded')}).",
                     {"measurement": f.finding, "action": f.action, "severity": f.severity}, f.source,
                     None if llm else "With a valid interpretation from the LLM, the action could have been chosen by the AI; here the "
                                      f"fallback rule associates the dimension “{f.dimension}” with the action “{f.action}”.",
                     refused=[],
                     terms=[f.id, f.table, f.column if f.column != "*" else None], audit=audit_seq("interpretation_completed"))


@ledger_block
def ledger_quality():
    applied = set(REVIEW["approved"])
    effects = dict(zip(EXECUTION["id"], EXECUTION["effect"])) if len(EXECUTION) else {}
    for p in CLEANING_PLAN.itertuples():
        risk = REVIEW["set_aside"].get(p.id)
        col = None if p.column == "*" else p.column
        where = p.table if col is None else f"{p.table}.{col}"
        policy = VALUE_POLICY["imputable"].get((p.table, col)) if col else None
        method = {"median": "median of similar rows", "infer": "category deduced from the other columns",
                  "label": f"label “{NOT_FILLED}”"}.get((policy or {}).get("method"), None)
        why = (f"Catalog correction: {CORRECTIONS[p.correction][1]}. It was first tested on a copy (sandbox): "
               f"measured effect {p.simulated_effect}. Justification: {p.justification}.")
        if method:
            why += (f" Method: {method} — cause of the missing values found by the Profiler: {policy['cause']}. "
                    f"Rule: {doc('missing_method')}")
        why += f" Validation: {doc('review_plan')}"
        cf = (f"It would not have been applied in case of information loss, if the test did not validate it, or if more than "
              f"{xai_num(MAX_ROWS_REMOVED_PCT)}% of the rows were removed.")
        if method == "median of similar rows":
            cf += f" With more than {xai_num(MAX_IMPUTE_PCT)}% missing values, or a structural gap, the column would have stayed empty."
        elif policy and policy.get("method") == "label":
            cf += (f" If the gap had been random and below {xai_num(MAX_IMPUTE_PCT)}%, the category would have been deduced "
                   "from the other columns.")
        add_decision(4, "Data Quality Agent", "correction", f"correction {p.id}",
                     f"correction {p.id} “{p.correction}” on {where}: " + ("applied" if p.id in applied else "set aside"),
                     why, {"targeted rule": p.rule, "tested effect": str(p.simulated_effect),
                           "cells or rows affected": effects.get(p.id), "missing (%)": (policy or {}).get("missing_pct"),
                           "risk": ", ".join(risk) if risk else "low", "Profiler findings": ", ".join(p.findings or [])},
                     p.decided_by, cf, refused=[] if p.decided_by == "agent" else refusals("decision_rejected", "quality_agent", limit=2),
                     terms=[p.id, p.table, col, p.candidate], audit=audit_seq("correction_applied", contains=p.id))
    for o in OTHER_TREATMENTS.itertuples():
        add_decision(4, "Data Quality Agent", "dismissed correction", f"dismissed correction {o.item}",
                     f"the candidate correction {o.item} on {o.table} is not applied: the data stays flagged",
                     f"Justification: {o.justification}.", {"treatment": o.treatment}, "agent",
                     "It would have been proposed if the agent had judged its tested effect useful and risk-free.",
                     terms=[o.item, o.table], audit=audit_seq("cleaning_plan_built"))
    before = RULES_BEFORE.set_index("rule")["violations"]
    for r in RULES_AFTER[RULES_AFTER["violations"] > 0].itertuples():
        add_decision(4, "Data Quality Agent", "rule still flagged", f"rule {r.rule}",
                     f"the rule “{r.description}” ({r.table}) remains flagged on {xai_num(r.violations)} row(s)",
                     "No catalog correction lifts it without risk (or the correction was set aside): the data is "
                     "not modified, each affected row is marked in the _dq_flags column for the analysis.",
                     {"rows before cleaning": int(before.get(r.rule, r.violations)), "rows after": r.violations,
                      "severity": r.severity, "dimension": r.dimension}, "code",
                     "A risk-free catalog correction (tested on a copy) would have lifted it.", terms=[r.rule, r.table],
                     audit=audit_seq("quality_completed"))
    add_decision(4, "Data Quality Agent", "quality status", "quality status",
                 f"quality status “{STATUS}”: average score {xai_num(round(SCORES_BEFORE.mean(), 2))} → "
                 f"{xai_num(round(SCORES_AFTER.mean(), 2))} / 100",
                 f"Rule: “blocked” if a blocking violation remains, “ready_with_warnings” if flagged violations "
                 f"remain, “ready” otherwise. Score per dimension: {doc('dq_scores')}",
                 {f"score {k} (before → after)": f"{xai_num(round(SCORES_BEFORE[k], 2))} → {xai_num(round(SCORES_AFTER[k], 2))}"
                  for k in SCORES_AFTER.index}, "code",
                 "The status would be “blocked” if a blocking rule (grain uniqueness, integrity) remained violated: the star "
                 "schema would not have been built.", terms=["quality", "score"], audit=audit_seq("quality_completed"))


@ledger_block
def ledger_etl():
    for name, spec in ETL_TEMPLATES.items():
        r = ETL_RESULTS.get(name, {})
        add_decision(5, "ETL Agent", "star schema table", name,
                     f"“{name}” is built as a {'fact table' if spec['type'] == 'fact' else 'dimension'}, one row per "
                     f"{' + '.join(spec.get('grain') or ['?'])}",
                     f"{spec.get('description', '')}. Design rule: {doc('design_star_schema')} Tests: {doc('test_table')}",
                     {"rows": r.get("rows"), "tests passed": f"{sum(r.get('tests', {}).values())} / {len(r.get('tests', {}))}",
                      "depends on": ", ".join(spec.get("depends_on") or []) or "no table",
                      "links": ", ".join(f"{c} → {t}" for c, (t, k) in (spec.get("fks") or {}).items())[:300] or "none"},
                     r.get("decided_by", "code"), "A table that fails a test does not enter the warehouse and the pipeline stops.",
                     terms=[name, re.sub(r"^(dim|fact)_", "", name)], audit=audit_seq("template_built", contains=name))
    for d in DERIVED.itertuples():
        add_decision(5, "ETL Agent", "derived indicator", d.column, f"the column “{d.column}” is computed: {d.calculation}",
                     f"Rule: {doc('derive_time_indicators')}", {"table": d.table, "type": d.type}, "code",
                     "It would not have been created if the second date did not follow the reference date in the vast majority of rows.",
                     terms=[d.table], audit=audit_seq("staging_loaded"))


@ledger_block
def ledger_prep_orchestration():
    r = DATA_PREP_RESULT
    add_decision(6, "LangGraph sub-orchestrator (part 1)", "orchestration", "Data Preparation Agent",
                 f"preparation finished with status “{r['status']}”" + (f": {r.get('error')}" if r.get("error") else ""),
                 f"Each agent is a node of the graph; after each node, a conditional edge continues or stops. "
                 f"{doc('graph_node')}",
                 node_history(r), "code",
                 "The pipeline would have stopped at the first failed or blocked node (e.g. blocking quality).",
                 terms=["preparation", "data preparation"], audit=audit_seq("data_preparation_finished"))


# ---------------------------------------------------------------- partie 2 · BI & Insight Agent
@ledger_block
def ledger_bridge():
    for r in globals().get("REBUILT_DATES", []):
        src = r.get("how") or " + ".join(r["parts"].values())
        add_decision(7, "Bridge (part 2)", "rebuilt date", r["column"], f"the date “{r['column']}” is rebuilt ({src})",
                     "A date split over several columns (year, month, day) or left as text cannot be analysed month by "
                     "month: the bridge rebuilds it in a working copy (the part 1 warehouse is not modified).",
                     {"table": r["table"], "source": src}, "code", None, terms=[r["table"]], audit=audit_seq("dates_rebuilt"))
    ev = SECTOR_EVIDENCE.set_index("sector")
    chosen = BI_SECTORS or []
    add_decision(7, "Knowledge base (RAG)", "business sector", "sector",
                 f"selected sector(s): {', '.join(chosen) or 'none (generic mode)'}",
                 f"Three signals: semantic proximity between the dataset and each sector (RAG), number of the sector's KPIs that can be computed, "
                 f"and KPIs whose columns have an expected name. Decision: {sector_reason}. The supervisor only accepts a sector "
                 f"if at least {MIN_SECTOR_KPIS} KPIs and {xai_num(int(MIN_SECTOR_COVERAGE * 100))}% of its KPIs find columns "
                 f"with the expected name, over at least {MIN_SECTOR_COLUMNS} different columns.",
                 {f"{s} (proximity · confirmed KPIs · columns · score)":
                      f"{xai_num(row['proximity'])} · {int(row['kpi_confirmed'])}/{int(row['kpi_total'])} · "
                      f"{int(row['columns_confirmed'])} · {xai_num(row['score'])}" for s, row in ev.iterrows()},
                 sector_source,
                 "Without a sufficiently confirmed sector, the pipeline would have switched to generic mode: generic KPIs + KPIs proposed by the agent.",
                 refused=refusals("decision_rejected", "bi_knowledge") if sector_source != "LLM" else [],
                 terms=["sector", *chosen], audit=audit_seq("sector_decided"))
    for r in KPI_REFERENCES:
        if not r["feasible"]:
            add_decision(7, "Knowledge base (RAG)", "KPI not computable", r["name"],
                         f"the KPI “{r['name']}” ({r['id']}) is not computed: it cannot be computed on this dataset",
                         f"No column can play the role required by its slot {', '.join(r['missing'])}: a KPI for which "
                         f"a role does not exist in the data is never invented.", {"missing role(s)": ", ".join(r["missing"])},
                         "code", f"It would have been computed if a column compatible with the role {', '.join(r['missing'])} existed.",
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
                ranking.append(f"{slot}: " + "; ".join(f"{x['column']} (score {xai_num(round(x['score'], 3))}"
                                                       f"{', expected name' if x.get('name_match') else ''})" for x in cands))
            ev[f"column for “{slot}”"] = f"{t}.{c}"
        for kind, vals in b["params"].items():
            for slot, v in vals.items():
                ev[f"parameter {kind} ({slot})"] = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
        if ranking:
            ev["candidates ranked by the semantic search"] = " | ".join(ranking)
        if kid in in_catalog:
            row = cat.loc[kid]
            ev.update({"value": fmt_value(row["value"], row["unit"]), "status": row["status"], "reliability": row["reliability"],
                       "tests": ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in row["tests"].items())})
        src = b["source"]
        why = {"obvious": "Each slot found a column with the expected name (confidence 1) and no parameter required "
                          "judgement: the binding is made by the code.",
               "LLM": f"The LLM chose the columns and the values among those that exist: “{b['reason']}”. The supervisor "
                      "checked the role and the reachability of the columns, and that the chosen values are observed (never all of them at once)."}.get(
            src, f"Reason: {b['reason'] or src}.")
        fate = ("in the catalog" if kid in in_catalog else
                "removed: duplicate" if kid in DUPLICATES else
                f"removed: replaced by {REPLACED[kid]}" if kid in REPLACED else
                f"failed: {FAILED.get(kid)}" if kid in FAILED else "removed")
        add_decision(8, "BI Semantic & KPI Agent", "KPI", card["name"],
                     f"KPI “{card['name']}” = {readable(card, b)} ({fate})",
                     f"{why} Calculation: the formula is compiled into SQL, then recomputed independently in pandas; both must "
                     f"be equal, and the value must respect the bounds of its unit. Bounds rule: {doc('check_bounds')}",
                     ev, src, "Another column would have been chosen if it had a better proximity score (or the expected name) "
                              "while having the required role; the KPI would have been rejected if the double calculation or the bounds failed.",
                     refused=refusals("binding_rejected", "kpi_agent", contains=kid), terms=[kid, card["name"]],
                     audit=audit_seq("kpi_computed", contains=kid))
    for kid, reason in DROPPED.items():
        name = KB_BY_ID[kid]["name"] if kid in KB_BY_ID else kid
        add_decision(8, "BI Semantic & KPI Agent", "dropped KPI", name, f"the KPI “{name}” ({kid}) is dropped",
                     f"Reason: {reason}.", {}, "LLM" if not reason.startswith("fallback") else "fallback",
                     "It would have been kept if a safe binding (compatible columns and decided parameters) had been found.",
                     refused=refusals("binding_rejected", "kpi_agent", contains=kid), terms=[kid], audit=audit_seq("kpis_bound"))
    for kid in DUPLICATES:
        add_decision(8, "BI Semantic & KPI Agent", "KPI removed (duplicate)", KB_BY_ID[kid]["name"],
                     f"the KPI “{KB_BY_ID[kid]['name']}” ({kid}) is removed from the catalog",
                     "It gives the same value on the same columns as another KPI: the sector card is kept, then the most relevant one.",
                     {}, "code", None, terms=[kid], audit=audit_seq("kpi_catalog_built"))
    for g, k in REPLACED.items():
        add_decision(8, "BI Semantic & KPI Agent", "KPI removed (replaced)", KB_BY_ID[g]["name"],
                     f"the generic KPI “{KB_BY_ID[g]['name']}” is replaced by “{KB_BY_ID[k]['name']}”",
                     "A generic KPI is removed when its more precise sector equivalent is computed.", {}, "code", None,
                     terms=[g, k], audit=audit_seq("kpi_catalog_built"))
    errs = globals().get("proposal_errors") or []
    if PROPOSALS or errs:
        add_decision(8, "BI Semantic & KPI Agent", "KPIs proposed by the agent", "KPIs proposed by the agent",
                     f"{len(PROPOSALS)} KPI(s) proposed by the agent accepted, {len(errs)} rejected",
                     "The knowledge base does not cover everything: the LLM can propose KPIs in the same closed language. The "
                     "supervisor checks columns, conditions, observed values, a name consistent with the formula and tests; a "
                     "proposed KPI remains “to confirm” by a human.",
                     {"accepted": ", ".join(f"{k} “{c['name']}”" for k, c in PROPOSALS.items()) or "none"}, "agent", None,
                     refused=errs[:4], terms=list(PROPOSALS), audit=audit_seq("kpis_proposed"))


@ledger_block
def ledger_analysis():
    for kid, why in SKIPPED_SERIES.items():
        add_decision(9, "BI Analyst Agent", "dropped series", f"series {kid}", f"the monthly series of {kid} is not analysed",
                     f"Reason: {why}. Two series telling the same story would produce duplicate signals.", {}, "code",
                     None, terms=[kid], audit=audit_seq("series_prepared"))
    thresholds = {"trend": [("p", "<", 0.05), ("change", ">=", 0.05)], "recent change": [("z", ">=", 2.5), ("change", ">=", 0.05)],
                  "year over year": [("change", ">=", 0.10)], "anomaly": [("z", ">=", 3.5), ("change", ">=", 0.10)],
                  "level shift": [("t", ">=", 4.0), ("change", ">=", 0.10)]}
    names = {"p": "p-value", "z": "z", "t": "Welch's t", "change": "relative change"}
    for f in FACTS.values():
        if f["type"] == "value":
            continue
        test, ev = f.get("test") or {}, dict(f.get("figures", {}))
        cf = None
        if f["type"] in thresholds and test:
            parts = []
            for key, op, lim in thresholds[f["type"]]:
                if key in test:
                    val = abs(test[key]) if key != "p" else test[key]
                    shown = f"{xai_num(round(val * 100, 1))}%" if key == "change" else xai_num(val)
                    limit = f"{xai_num(lim * 100)}%" if key == "change" else xai_num(lim)
                    parts.append(f"{names[key]} {'≥' if op == '<' else '<'} {limit} (here {shown})")
                    ev[names[key]] = shown
            cf = "This signal would have been dropped if " + " or if ".join(parts) + "."
            ev["method"] = test.get("method")
            why = (f"Deterministic statistical test (no LLM): {test.get('method')}. Thresholds: {test.get('thresholds')}. "
                   f"A signal is only kept if it is both statistically clear and large enough to matter.")
        elif f["type"] == "segment":
            why = (f"Breakdown by segment: for each possible axis, the code computes the KPI per segment and checks that the "
                   f"segments reconcile with the catalog value; the axis kept is the most discriminating one. "
                   f"“Twin” axes of a formula column are dropped.")
        elif f["type"] == "contribution":
            why = ("Contribution to a change: the code compares two time windows segment by segment and measures the share "
                   "of the overall change explained by each segment.")
        else:
            why = "Fact computed by the code."
        add_decision(9, "BI Analyst Agent", f"fact ({f['type']})", f"fact {f['id']}",
                     f"fact {f['id']} ({f['type']}): {f['text']}", why, ev, "code", cf,
                     terms=[f["id"], f["kpi"], f.get("label")], audit=audit_seq("statistical_signals"))
        if f["type"] in CHANGE_LABELS and len(f["numbers"]) >= 2:
            LEDGER[-1]["before_after"] = f["numbers"][:2]        # ordre des deux valeurs (contrôle de la reformulation)
            LEDGER[-1]["direction"] = f.get("direction")
    for inv in INVESTIGATIONS:
        axe = ".".join(inv["axis"]) if isinstance(inv["axis"], (list, tuple)) else inv["axis"]
        add_decision(9, "BI Analyst Agent", "investigation", f"investigation {inv['fact']} by {axe}",
                     f"the fact {inv['fact']} is investigated along the axis {axe} (new fact {inv.get('result')})",
                     f"Reason: {inv['why']}. The LLM chooses the signals to investigate and the axis; the code checks that the fact and the axis "
                     f"exist, then runs the breakdown.", {"investigated fact": inv["fact"], "result": inv.get("result")},
                     inv.get("source", "code"), None, refused=(globals().get("inv_errors") or [])[:3],
                     terms=[inv["fact"], inv.get("result"), axe.split(".")[-1]], audit=audit_seq("investigations"))
    checks = ("the cited facts exist; every number in the text appears in these facts; the direction (increase/decrease) of the title and of the "
              "text is that of the facts; the named segments appear in the facts; no KPI is repeated; a share of "
              "change is never presented as an increase")
    for i in INSIGHTS:
        ev = {f"fact {fid}": FACTS[fid]["text"][:240] for fid in i["facts"] if fid in FACTS}
        ev["type"] = i["type"]
        add_decision(9, "BI Analyst Agent", "insight", f"insight {i['id']}", f"insight {i['id']}: “{i['title']}”",
                     (f"Written by the LLM from the facts {', '.join(i['facts'])}, then verified by the code: {checks}."
                      if i["source"] == "LLM" else
                      f"Written by the code from the facts {', '.join(i['facts'])} (important signal not covered by the LLM, or "
                      f"LLM answer rejected twice)."), ev, i["source"],
                     "An LLM insight that had cited a figure missing from its facts, a non-existent fact or a contrary direction would have "
                     "been rejected, sent back once to the LLM with the reason, then replaced by a code-written version.",
                     refused=(globals().get("insight_errors") or [])[:3], terms=[i["id"], *i["facts"]],
                     audit=audit_seq("insights_written"))


@ledger_block
def ledger_dashboard():
    name = lambda k: KB_BY_ID[k]["name"] if k in KB_BY_ID else k
    add_decision(10, "Dashboard Generator Agent", "layout", "dashboard",
                 f"dashboard “{LAYOUT['title']}”: main figure “{name(LAYOUT['hero'])}”, {len(LAYOUT['tiles'])} tiles, "
                 f"{len(LAYOUT['charts'])} charts, {len(LAYOUT['breakdowns'])} breakdowns",
                 "The LLM chooses and orders among candidates prepared by the code (values already formatted); the supervisor checks "
                 "the identifiers, the limits, a chart only for a KPI that has a series, no figure in the title, and "
                 "adds the curve or the breakdown of each insight that needs one.",
                 {"main figure": name(LAYOUT["hero"]), "tiles": ", ".join(map(name, LAYOUT["tiles"])),
                  "charts": ", ".join(map(name, LAYOUT["charts"])), "breakdowns": ", ".join(LAYOUT["breakdowns"])},
                 layout_source, "Without a valid answer from the LLM, the code's default layout would have been used.",
                 refused=(globals().get("layout_errors") or [])[:3], terms=["dashboard", "layout", LAYOUT["hero"]],
                 audit=audit_seq("layout_decided"))


@ledger_block
def ledger_bi_orchestration():
    r = globals().get("BI_RESULT")
    if not r:
        return
    add_decision(11, "LangGraph sub-orchestrator (part 2)", "orchestration", "BI & Insight Agent",
                 f"BI & Insight Agent finished with status “{r['status']}”" + (f": {r.get('error')}" if r.get("error") else ""),
                 "The graph chains bridge → KPI → analyst → dashboard; each step is only validated if its checkpoint "
                 "(ok7 … ok10) is true, otherwise the pipeline stops cleanly with the reason.",
                 node_history(r), "code", None,
                 terms=["bi insight", "bi orchestrator"], audit=audit_seq("bi_insight_finished"))


@ledger_block
def ledger_global_orchestration():
    r = globals().get("BIFLOW_RESULT")
    if not r:
        return
    add_decision(13, "Global BI Orchestrator", "orchestration", "full pipeline",
                 f"full pipeline finished with status “{r['status']}”" + (f": {r.get('error')}" if r.get("error") else ""),
                 "The global orchestrator chains preparation → BI & insights → explainability; it stops at the first part that "
                 "fails, but always builds the explainability, so that the stop can be explained.",
                 node_history(r), "code", None,
                 terms=["pipeline", "global orchestrator", "from a to z"], audit=audit_seq("biflow_finished"))


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
AUDIT.log("xai_agent", "decision_ledger_built", {"decisions": len(DECISIONS), "by_step": DECISIONS["step"].value_counts().to_dict(),
                                                 "errors": LEDGER_ERRORS}, level="INFO" if not LEDGER_ERRORS else "WARNING")
print(f"Ledger: {len(DECISIONS)} decisions · " + " · ".join(f"step {s}: {n}" for s, n in
                                                          DECISIONS["step"].value_counts().sort_index().items()))
print("Unavailable blocks:", LEDGER_ERRORS or "none")
(DECISIONS.assign(decided_by=DECISIONS["decided_by"])
 .groupby(["step", "decided_by"]).size().rename("decisions").reset_index()
 .assign(step=lambda d: d["step"].map(lambda s: f"{s}. {XAI_STEPS.get(s, '')}")))
