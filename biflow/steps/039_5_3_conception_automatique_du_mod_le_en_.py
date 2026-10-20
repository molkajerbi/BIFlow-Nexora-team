def q(name: str) -> str:
    """Nom SQL protégé (gère les espaces et les majuscules : "Order Date")."""
    return '"' + str(name).replace('"', '""') + '"'


def silver_sum(table: str, col: str, mask: pd.Series | None = None) -> float:
    s = SILVER[table][col].astype("Float64")
    return float((s[mask] if mask is not None else s).sum())


TECH = {"_source_row_id", "_dq_flags"}
NUMERIC = {"numeric", "integer"}


def dimension_key(t: str) -> list[str]:
    """Clé d'une dimension : son grain, sinon la clé par laquelle on la référence (dimension agrégée), sinon le lignage."""
    if DATA_CONTRACT[t]["grain"]:
        return DATA_CONTRACT[t]["grain"]
    refs = [r["pk"] for r in RELATIONSHIPS if r["parent"] == t]
    return [max(set(refs), key=refs.count)] if refs else ["_source_row_id"]


def is_aggregated(t: str) -> bool:
    return not DATA_CONTRACT[t]["grain"] and dimension_key(t) != ["_source_row_id"]


def dim_source_sql(t: str) -> tuple[str, list[str]]:
    """Requête de base d'une dimension (agrégée si la table a plusieurs lignes par clé) et ses colonnes."""
    key, cols = dimension_key(t), DATA_CONTRACT[t]["columns"]
    if is_aggregated(t):
        k = key[0]
        parts = [q(k)] + [f"{'AVG' if s in NUMERIC | {'geo'} else 'MIN'}({q(c)}) AS {q(c)}" for c, s in cols.items() if c != k]
        sql = f"SELECT {', '.join(parts)}, COUNT(*) AS source_rows FROM stg_{t} WHERE {q(k)} IS NOT NULL GROUP BY {q(k)}"
        return sql, [k] + [c for c in cols if c != k] + ["source_rows"]
    columns = list(STAGING[f"stg_{t}"].columns)
    return f"SELECT * FROM stg_{t}", columns


def orphan_keys(t: str, key: str) -> set:
    """Valeurs de clés référencées par d'autres tables mais absentes de la dimension (→ membres « inconnus »)."""
    known, orphans = set(SILVER[t][key].dropna()), set()
    for r in RELATIONSHIPS:
        if r["parent"] == t and r["pk"] == key and r["child"] in SILVER:
            orphans |= set(SILVER[r["child"]][r["fk"]].dropna()) - known
    return orphans


def extracted_dimensions(t: str, min_share: float = 0.99) -> list[dict]:
    """Normalisation automatique : dans une table de faits « à plat », un identifiant (ex. Customer ID) et les colonnes
    qui en dépendent fonctionnellement (Customer Name, Segment) forment une dimension."""
    df, spec = SILVER[t], DATA_CONTRACT[t]
    used = set(spec["grain"] or []) | {r["fk"] for r in RELATIONSHIPS if r["child"] == t}
    out = []
    for x, sx in spec["columns"].items():
        n = df[x].nunique()
        if sx != "id" or x in used or not 2 <= n <= 0.5 * len(df):
            continue
        attrs = []
        for y, sy in spec["columns"].items():
            if y != x and sy in {"category", "text", "zip", "geo"} and df[y].notna().any():
                per_key = df.groupby(x, dropna=True)[y].nunique(dropna=True)
                if float((per_key <= 1).mean()) >= min_share:
                    attrs.append(y)
        if attrs:
            out.append({"key": x, "attributes": attrs})
    return out


def design_star_schema() -> dict:
    """Conçoit le modèle en étoile à partir du contrat : aucune ligne écrite à la main pour un dataset particulier."""
    facts = [t for t in DATA_CONTRACT if TABLE_ROLES[t] == "fait"]
    dims = [t for t in DATA_CONTRACT if TABLE_ROLES[t] != "fait"]
    name = {t: ("fact_" if t in facts else "dim_") + t for t in DATA_CONTRACT}
    templates = {}
    if "stg_dim_date" in STAGING:
        templates["dim_date"] = {"type": "dimension", "grain": ["date_key"], "depends_on": [],
                                 "description": "calendrier continu (année, trimestre, mois, semaine, week-end)",
                                 "sql": "SELECT * FROM stg_dim_date", "expect_rows": lambda: len(STAGING["stg_dim_date"])}

    # ---------- Dimensions : agrégées si besoin, enrichies (aplaties), avec membres « inconnus » ----------
    for t in dims:
        key = dimension_key(t)
        base_sql, base_cols = dim_source_sql(t)
        select, joins, out_cols = [f"b.{q(c)}" for c in base_cols], [], list(base_cols)
        for i, r in enumerate(r for r in RELATIONSHIPS if r["child"] == t and r["parent"] in dims and r["parent"] != t):
            p_sql, p_cols = dim_source_sql(r["parent"])
            alias = f"p{i}"
            joins.append(f"LEFT JOIN ({p_sql}) {alias} ON {alias}.{q(r['pk'])} = b.{q(r['fk'])}")
            for c in p_cols:
                if c in TECH | {r["pk"], "source_rows"} or DATA_CONTRACT[r["parent"]]["columns"].get(c) is None:
                    continue
                new = c if c not in out_cols else f"{r['parent']}_{key_name(r['parent'], c)}"
                if new not in out_cols:
                    select.append(f"{alias}.{q(c)} AS {q(new)}")
                    out_cols.append(new)
        body = f"SELECT {', '.join(select)}, 0 AS is_unknown_member FROM ({base_sql}) b {' '.join(joins)}"
        sql, n_orphans = body, (lambda t=t, key=key: len(orphan_keys(t, key[0])) if len(key) == 1 and key[0] in SILVER[t] else 0)
        refs = [r for r in RELATIONSHIPS if r["parent"] == t and len(key) == 1 and r["pk"] == key[0]]
        if refs and key != ["_source_row_id"]:
            k = key[0]
            orphan_sql = " UNION ".join(
                f"SELECT DISTINCT {q(r['fk'])} AS k FROM stg_{r['child']} WHERE {q(r['fk'])} IS NOT NULL "
                f"AND {q(r['fk'])} NOT IN (SELECT {q(k)} FROM stg_{t} WHERE {q(k)} IS NOT NULL)" for r in refs)
            unknown = [("u.k" if c == k else "'inconnu:' || CAST(u.k AS VARCHAR)" if c == "_source_row_id" else "NULL")
                       + f" AS {q(c)}"
                       for c in out_cols]
            sql = f"{body} UNION ALL SELECT {', '.join(unknown)}, 1 AS is_unknown_member FROM ({orphan_sql}) u"
        base_rows = (lambda t=t, key=key: SILVER[t][key[0]].nunique()) if is_aggregated(t) else (lambda t=t: len(SILVER[t]))
        templates[name[t]] = {
            "type": "dimension", "grain": key, "depends_on": [],
            "description": (f"dimension issue de {t}" + (" (agrégée par clé)" if is_aggregated(t) else "")
                            + (f", enrichie avec {', '.join(sorted({r['parent'] for r in RELATIONSHIPS if r['child'] == t and r['parent'] in dims}))}"
                               if joins else "") + (", membres « inconnus » pour les clés orphelines" if refs else "")),
            "sql": sql, "expect_rows": lambda b=base_rows, o=n_orphans: b() + o(),
            "lineage": None if is_aggregated(t) else t}

    # ---------- Faits : clés propagées, agrégats d'en-tête sans double comptage, dimensions extraites ----------
    for t in facts:
        spec, stg_cols = DATA_CONTRACT[t], list(STAGING[f"stg_{t}"].columns)
        grain = spec["grain"] or ["_source_row_id"]
        select, joins, ctes, out_cols = [f"b.{q(c)}" for c in stg_cols], [], [], list(stg_cols)
        fks, flagged_ok, header_sums, header_children = {}, set(), {}, []
        for r in (r for r in RELATIONSHIPS if r["child"] == t and r["parent"] != t):
            target = name[r["parent"]]
            fks[r["fk"]] = (target, r["pk"])
            if r["parent"] in facts:
                flagged_ok.add(r["fk"])                      # fait -> fait : un orphelin signalé est toléré
                # propagation : les clés de dimension et la date de référence du fait parent descendent dans ce fait
                p, alias = r["parent"], f"f{len(joins)}"
                p_cols = list(STAGING[f"stg_{p}"].columns)
                carry = [rr["fk"] for rr in RELATIONSHIPS if rr["child"] == p and rr["parent"] in dims]
                carry += [c for c in p_cols if c.endswith("_date_key")][:1]
                carry += [c for c, s in DATA_CONTRACT[p]["columns"].items() if s == "category" and SILVER[p][c].nunique() <= 50]
                added = [c for c in dict.fromkeys(carry) if c not in out_cols and c != r["pk"]]
                if added:
                    joins.append(f"LEFT JOIN stg_{p} {alias} ON {alias}.{q(r['pk'])} = b.{q(r['fk'])}")
                    select += [f"{alias}.{q(c)} AS {q(c)}" for c in added]
                    out_cols += added
                    for c in added:
                        rr = next((rr for rr in RELATIONSHIPS if rr["child"] == p and rr["fk"] == c and rr["parent"] in dims), None)
                        if rr:
                            fks[c] = (name[rr["parent"]], dimension_key(rr["parent"])[0])
                        elif c.endswith("_date_key") and "dim_date" in templates:
                            fks[c] = ("dim_date", "date_key")
        # agrégats d'en-tête : chaque fait « enfant » est agrégé SÉPARÉMENT avant la jointure (pas de fan-out)
        for i, r in enumerate(r for r in RELATIONSHIPS if r["parent"] == t and r["child"] in facts and r["child"] != t
                              and not r["aggregate"]):
            c_t = r["child"]
            header_children.append(c_t)
            measures = [m for m, s in DATA_CONTRACT[c_t]["columns"].items() if s in NUMERIC
                        and m not in (DATA_CONTRACT[c_t]["grain"] or []) and m not in {x["fk"] for x in RELATIONSHIPS if x["child"] == c_t}]
            cte = f"agg{i}"
            parts = [f"{q(r['fk'])} AS k", f"COUNT(*) AS {q(c_t + '_count')}"] + \
                    [f"SUM({q(m)}) AS {q(f'{c_t}_{m}_sum')}" for m in measures]
            ctes.append(f"{cte} AS (SELECT {', '.join(parts)} FROM stg_{c_t} GROUP BY {q(r['fk'])})")
            joins.append(f"LEFT JOIN {cte} ON {cte}.k = b.{q(r['pk'])}")
            select.append(f"COALESCE({cte}.{q(c_t + '_count')}, 0) AS {q(c_t + '_count')}")
            out_cols.append(c_t + "_count")
            for m in measures:
                col = f"{c_t}_{m}_sum"
                select.append(f"{cte}.{q(col)} AS {q(col)}")
                out_cols.append(col)
                header_sums[col] = (lambda c_t=c_t, m=m, fk=r["fk"], pk=r["pk"], t=t:
                                    silver_sum(c_t, m, SILVER[c_t][fk].isin(SILVER[t][pk])))
        for c, s in spec["columns"].items():                 # clés de date -> calendrier
            if s == "datetime" and "dim_date" in templates:
                fks[f"{c}_date_key"] = ("dim_date", "date_key")
        # dimensions extraites d'une table à plat (dépendances fonctionnelles)
        for e in extracted_dimensions(t):
            stem = re.sub(r"_(id|key|code|sku|ref)$", "", snake(e["key"])) or snake(e["key"])
            dname = f"dim_{stem}" if f"dim_{stem}" not in templates and stem not in DATA_CONTRACT else f"dim_{t}_{stem}"
            parts = [q(e["key"])] + [f"MIN({q(a)}) AS {q(a)}" for a in e["attributes"]]
            templates[dname] = {"type": "dimension", "grain": [e["key"]], "depends_on": [],
                                "description": f"dimension extraite de {t} : {e['key']} -> {', '.join(e['attributes'])}",
                                "sql": f"SELECT {', '.join(parts)}, COUNT(*) AS source_rows FROM stg_{t} "
                                       f"WHERE {q(e['key'])} IS NOT NULL GROUP BY {q(e['key'])}",
                                "expect_rows": lambda t=t, k=e["key"]: SILVER[t][k].nunique()}
            fks[e["key"]] = (dname, e["key"])
        measures = [c for c, s in spec["columns"].items() if s in NUMERIC and c not in grain and c not in fks]
        with_cte = f"WITH {', '.join(ctes)} " if ctes else ""
        templates[name[t]] = {
            "type": "fait", "grain": grain, "depends_on": sorted({target for target, _ in fks.values()}),
            "description": f"fait issu de {t} · {len(fks)} clé(s) · mesures : {', '.join(measures) or 'aucune'}"
                           + (f" · agrégats séparés de {', '.join(header_children)}" if header_children else ""),
            "sql": f"{with_cte}SELECT {', '.join(select)} FROM stg_{t} b {' '.join(joins)}",
            "expect_rows": lambda t=t: len(SILVER[t]), "lineage": t,
            "sums": {**{m: (lambda t=t, m=m: silver_sum(t, m)) for m in measures}, **header_sums},
            "fks": fks, "flagged_ok": flagged_ok}

    # ---------- Dépendances : on retire celles qui formeraient un cycle (fait <-> fait) ----------
    pending = set(templates)
    while pending:
        free = [n for n in pending if not set(templates[n]["depends_on"]) & pending]
        if free:
            pending -= set(free)
            continue
        for n in pending:                                    # cycle : on casse les dépendances internes
            cyc = set(templates[n]["depends_on"]) & pending
            templates[n]["depends_on"] = [d for d in templates[n]["depends_on"] if d not in cyc]
            templates[n]["fks"] = {c: v for c, v in templates[n].get("fks", {}).items() if v[0] not in cyc}
    return templates


def key_strings(s: pd.Series) -> pd.Series:
    """Normalise des clés pour les comparer (un entier relu en float, 20170101.0, redevient 20170101)."""
    s = s.dropna()
    return (pd.to_numeric(s).astype("int64") if pd.api.types.is_numeric_dtype(s) else s).astype(str)


def test_table(name: str) -> dict:
    """Tests exécutés par le superviseur après chaque construction (jamais par le LLM)."""
    spec, df = ETL_TEMPLATES[name], WH.query(f"SELECT * FROM {name}")
    tests = {"grain_unique": bool(not df.duplicated(subset=spec["grain"]).any() and df[spec["grain"]].notna().all().all()),
             "row_count": len(df) == spec["expect_rows"]()}
    if spec.get("lineage"):
        ids = df["_source_row_id"].dropna()
        tests["lineage_complete"] = set(ids[~ids.astype(str).str.startswith("inconnu:")]) == set(SILVER[spec["lineage"]]["_source_row_id"])
    for col, expected in spec.get("sums", {}).items():
        exp = expected()
        tests[f"sum_{col}"] = abs(float(pd.to_numeric(df[col]).sum()) - exp) <= 0.01 + 1e-9 * abs(exp)
    for col, (target, key) in spec.get("fks", {}).items():
        keys = set(key_strings(WH.query(f"SELECT {q(key)} FROM {target}")[key]))
        values = key_strings(df[col])
        ok = values.isin(keys)
        if col in spec.get("flagged_ok", set()):             # fait -> fait : orphelin toléré seulement s'il est signalé
            ok |= df.loc[values.index, "_dq_flags"].fillna("").str.contains("REF_", regex=False)
        tests[f"fk_{col}"] = bool(ok.all())
    return {"rows": len(df), "columns": df.shape[1], "tests": tests, "passed": all(tests.values())}


ETL_TEMPLATES = design_star_schema()
TEMPLATES_SHA256 = sha256_text(canonical_json({k: v["sql"] for k, v in ETL_TEMPLATES.items()}))
AUDIT.log("etl_agent", "star_schema_designed", {"templates": {k: v["description"] for k, v in ETL_TEMPLATES.items()},
                                                "templates_sha256": TEMPLATES_SHA256})
print(f"Modèle en étoile conçu automatiquement : "
      f"{sum(v['type'] == 'dimension' for v in ETL_TEMPLATES.values())} dimension(s), "
      f"{sum(v['type'] == 'fait' for v in ETL_TEMPLATES.values())} fait(s)")
pd.DataFrame([{"template": k, "type": v["type"], "grain": " + ".join(v["grain"]), "dépend_de": v["depends_on"],
               "tests": 2 + bool(v.get("lineage")) + len(v.get("sums", {})) + len(v.get("fks", {})),
               "description": v["description"]} for k, v in ETL_TEMPLATES.items()])
