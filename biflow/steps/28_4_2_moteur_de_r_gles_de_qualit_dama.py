import unicodedata


@dataclass
class Rule:
    id: str
    table: str
    dimension: str      # complétude, validité, format, unicité, intégrité, cohérence, plausibilité
    severity: str       # blocking (interdit l'ETL) ou warning (signalé)
    description: str
    check: Any          # fonction S -> masque booléen des lignes en violation (index de S[table])


NULL_TOKENS = {"na", "n/a", "n.a.", "nan", "null", "(null)", "none", "nil", "-", "--", "?", "#n/a", "undefined"}


def normalize_text(v: str) -> str:
    """Forme de comparaison : sans accents, sans casse, espaces réduits ('São  Paulo ' -> 'sao paulo')."""
    v = unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", v).strip().lower()


def variant_map(s: pd.Series) -> dict:
    """Variantes d'écriture d'une même catégorie -> forme la plus fréquente ('SAO PAULO', 'Sao Paulo' -> 'sao paulo')."""
    counts = s.dropna().str.strip().value_counts()
    groups = counts.groupby(counts.index.map(normalize_text))
    mapping = {}
    for _, g in groups:
        if len(g) > 1:
            canonical = g.idxmax()
            mapping.update({v: canonical for v in g.index if v != canonical})
    return mapping


def is_variant(s: pd.Series) -> pd.Series:
    mapping = variant_map(s)
    return s.str.strip().isin(set(mapping)).fillna(False).astype(bool)


def build_rules() -> list[Rule]:
    rules = []
    # --- Règles générées automatiquement à partir du contrat de données ---
    for t, spec in DATA_CONTRACT.items():
        cols = list(spec["columns"])
        if spec["grain"]:
            rules.append(Rule(f"UNQ_{t}", t, "unicité", "blocking", f"grain {'+'.join(spec['grain'])} unique",
                              lambda S, t=t, g=spec["grain"]: S[t].duplicated(subset=g, keep=False)))
        else:
            rules.append(Rule(f"DUP_{t}", t, "unicité", "warning", "aucune ligne dupliquée à l'identique",
                              lambda S, t=t, c=cols: S[t].duplicated(subset=c, keep="first")))
        for c, sem in spec["columns"].items():
            if sem in {"category", "text"}:
                rules.append(Rule(f"FMT_{t}.{c}", t, "format", "warning", f"{c} sans espaces parasites",
                                  lambda S, t=t, c=c: (S[t][c].notna() & (S[t][c] != S[t][c].str.strip())).astype(bool)))
            if sem in {"category", "text", "id", "zip"}:
                rules.append(Rule(f"NUL_{t}.{c}", t, "complétude", "warning", f"{c} sans valeur vide déguisée (NA, null, -…)",
                                  lambda S, t=t, c=c: S[t][c].str.strip().str.lower().isin(NULL_TOKENS).fillna(False).astype(bool)))
            if sem == "category" and c not in (spec["grain"] or []):       # jamais sur une clé : fusionner des clés n'est pas sans perte
                rules.append(Rule(f"CAS_{t}.{c}", t, "format", "warning", f"{c} : une seule écriture par catégorie",
                                  lambda S, t=t, c=c: is_variant(S[t][c])))
        rules.append(Rule(f"TYP_{t}", t, "validité", "warning", "toutes les valeurs respectent leur type",
                          lambda S, t=t: S[t]["_source_row_id"].isin(TYPE_FAILURES.loc[TYPE_FAILURES["table"] == t, "_source_row_id"])))
    for r in RELATIONSHIPS:
        rules.append(Rule(f"REF_{r['child']}.{r['fk']}", r["child"], "intégrité", "warning",
                          f"{r['fk']} existe dans {r['parent']}.{r['pk']}",
                          lambda S, r=r: (S[r["child"]][r["fk"]].notna()
                                          & ~S[r["child"]][r["fk"]].isin(S[r["parent"]][r["pk"]])).astype(bool)))
    # --- Doublons probables d'entités (même nom / mêmes attributs, identifiant différent) ---
    for t, spec in DATA_CONTRACT.items():
        identifying, context = near_duplicate_columns(t)
        if identifying:
            rules.append(Rule(f"NDP_{t}", t, "unicité", "warning",
                              f"doublon probable : même {' ou '.join(identifying)} (sans casse ni accents)"
                              + (f" et même {', '.join(context)}" if context else "") + ", identifiant différent",
                              lambda S, t=t, i=identifying, c=context: near_duplicate_mask(S[t], i, c)))
    # --- Règles métier APPRISES des données (dans une table, puis entre tables) ---
    return rules + learned_business_rules() + learned_cross_table_rules()


def normalized(s: pd.Series) -> pd.Series:
    return (s.astype("string").str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")
            .str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip())


def near_duplicate_columns(t: str) -> tuple[list[str], list[str]]:
    """Dans une dimension à clé unique : colonnes qui identifient presque chaque entité (nom, e-mail…)
    et colonnes de contexte (ville, segment…) qui doivent aussi correspondre."""
    spec = DATA_CONTRACT[t]
    if TABLE_ROLES.get(t) != "dimension" or not spec["grain"] or len(spec["grain"]) != 1 or len(SILVER[t]) < 20:
        return [], []
    df = SILVER[t]
    cols = [c for c, s in spec["columns"].items() if s in {"category", "text", "zip"} and c not in spec["grain"]]
    identifying = [c for c in cols if spec["columns"][c] in {"category", "text"} and df[c].nunique() >= 0.5 * len(df)]
    return identifying, [c for c in cols if c not in identifying]


def near_duplicate_mask(df: pd.DataFrame, identifying: list[str], context: list[str]) -> pd.Series:
    """Même nom (ou même e-mail…) une fois casse, accents et ponctuation retirés, et même contexte."""
    ctx = pd.Series("", index=df.index)
    for c in context:
        ctx = ctx + "|" + normalized(df[c]).fillna("")
    mask = pd.Series(False, index=df.index)
    for c in identifying:
        key = normalized(df[c])
        mask |= key.notna() & (key != "") & (key + ctx).duplicated(keep=False)
    return mask


def child_total(S: dict, child: str, fk: str, measures: tuple) -> pd.Series:
    df = S[child]
    values = df[measures[0]].astype("Float64")
    for m in measures[1:]:
        values = values + df[m].astype("Float64")
    return values.groupby(df[fk]).sum(min_count=1).dropna()


def learned_cross_table_rules(min_support: float = 0.95, min_rows: int = 30) -> list[Rule]:
    """Cohérence ENTRE tables, apprise des données : si, pour ≥ 95 % des entités, un total calculé dans une table
    égale un total d'une autre (ex. montant payé = prix + frais de port des articles), cela devient une règle."""
    rules = []
    for p, spec in DATA_CONTRACT.items():
        if not spec["grain"] or len(spec["grain"]) != 1:
            continue
        pk = spec["grain"][0]
        kids = [r for r in RELATIONSHIPS if r["parent"] == p and r["pk"] == pk and r["child"] != p]
        totals = {}
        for r in kids:
            ms = [m for m, s in DATA_CONTRACT[r["child"]]["columns"].items() if s == "numeric"][:6]
            for combo in [(m,) for m in ms] + list(itertools.combinations(ms, 2)):
                totals[(r["child"], r["fk"], combo)] = child_total(SILVER, r["child"], r["fk"], combo)
        for m, s in spec["columns"].items():
            if s == "numeric":
                totals[(p, pk, (m,))] = SILVER[p].set_index(pk)[m].astype("Float64").dropna()
        for a, b in itertools.combinations(totals, 2):
            if a[0] == b[0]:
                continue
            A, B = totals[a], totals[b]
            common = A.index.intersection(B.index)
            if len(common) < min_rows or float(B[common].abs().sum()) == 0:
                continue
            ok = (A[common] - B[common]).abs() <= np.maximum(1.0, 0.005 * B[common].abs())
            share = float(ok.mean())
            if share >= min_support:
                label = lambda k: f"{' + '.join(k[2])} ({k[0]})"
                rules.append(Rule(f"BUS_total_{p}.{'+'.join(a[2])}={'+'.join(b[2])}", p, "cohérence", "warning",
                                  f"{label(a)} = {label(b)} par {pk} (respecté par {100 * share:.2f} %)",
                                  lambda S, p=p, pk=pk, a=a, b=b: cross_mismatch(S, p, pk, a, b)))
    return rules


def cross_mismatch(S: dict, p: str, pk: str, a: tuple, b: tuple) -> pd.Series:
    total = lambda k: (S[p].set_index(pk)[k[2][0]].astype("Float64").dropna() if k[0] == p
                       else child_total(S, k[0], k[1], k[2]))
    A, B = total(a), total(b)
    common = A.index.intersection(B.index)
    bad = common[((A[common] - B[common]).abs() > np.maximum(1.0, 0.005 * B[common].abs())).to_numpy()]
    return S[p][pk].isin(bad)


def learned_business_rules(min_support: float = 0.99, min_rows: int = 30) -> list[Rule]:
    """Une contrainte respectée par ≥ 99 % des lignes devient une règle : les rares exceptions sont signalées."""
    rules, now = [], pd.Timestamp.now()
    for t, spec in DATA_CONTRACT.items():
        df, grain = SILVER[t], spec["grain"] or []
        fks = {r["fk"] for r in RELATIONSHIPS if r["child"] == t}
        dates = [c for c, s in spec["columns"].items() if s == "datetime"]
        for c, sem in spec["columns"].items():
            x = df[c].dropna()
            if sem in {"numeric", "integer"} and c not in grain and c not in fks and len(x) >= min_rows \
                    and float((x >= 0).mean()) >= min_support:
                rules.append(Rule(f"BUS_non_negative_{t}.{c}", t, "plausibilité", "warning",
                                  f"{c} ≥ 0 (respecté par {100 * float((x >= 0).mean()):.2f} % des lignes)",
                                  lambda S, t=t, c=c: (S[t][c] < 0).fillna(False).astype(bool)))
            elif sem == "geo":
                limit = 90 if set(snake(c).split("_")) & {"lat", "latitude"} else 180
                rules.append(Rule(f"BUS_geo_range_{t}.{c}", t, "plausibilité", "warning", f"{c} entre -{limit} et {limit}",
                                  lambda S, t=t, c=c, m=limit: (S[t][c].abs() > m).fillna(False).astype(bool)))
            elif sem == "datetime":
                rules.append(Rule(f"BUS_date_range_{t}.{c}", t, "plausibilité", "warning", f"{c} entre 1900 et aujourd'hui + 1 an",
                                  lambda S, t=t, c=c: ((S[t][c] < pd.Timestamp("1900-01-01"))
                                                       | (S[t][c] > now + pd.DateOffset(years=1))).fillna(False).astype(bool)))
        for a, b in itertools.permutations(dates, 2):           # ordre chronologique appris entre deux dates
            both = df[a].notna() & df[b].notna()
            if both.sum() >= min_rows and float((df.loc[both, a] <= df.loc[both, b]).mean()) >= min_support \
                    and float((df.loc[both, b] <= df.loc[both, a]).mean()) < min_support:
                rules.append(Rule(f"BUS_date_order_{t}.{a}<={b}", t, "cohérence", "warning",
                                  f"{a} ≤ {b} (respecté par {100 * float((df.loc[both, a] <= df.loc[both, b]).mean()):.2f} %)",
                                  lambda S, t=t, a=a, b=b: (S[t][a] > S[t][b]).fillna(False).astype(bool)))
    return rules


def run_rules(S: dict, rules: list[Rule]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Exécute toutes les règles. Renvoie les violations (une ligne par ligne fautive) et le résumé par règle."""
    issues, summary = [], []
    for rule in rules:
        mask = pd.Series(rule.check(S), index=S[rule.table].index).fillna(False).astype(bool)
        n = int(mask.sum())
        summary.append({"rule": rule.id, "table": rule.table, "dimension": rule.dimension, "severity": rule.severity,
                        "description": rule.description, "rows_checked": len(S[rule.table]), "violations": n})
        if n:
            issues.append(S[rule.table].loc[mask, ["_source_row_id"]].assign(
                rule=rule.id, table=rule.table, dimension=rule.dimension, severity=rule.severity))
    issues_df = pd.concat(issues, ignore_index=True) if issues else pd.DataFrame(
        columns=["_source_row_id", "rule", "table", "dimension", "severity"])
    return issues_df, pd.DataFrame(summary)


RULES = build_rules()
ISSUES_BEFORE, RULES_BEFORE = run_rules(SILVER, RULES)
AUDIT.log("quality_agent", "rules_executed",
          {"rules": len(RULES), "learned_business_rules": sum(r.id.startswith("BUS_") for r in RULES),
           "violations": int(RULES_BEFORE["violations"].sum()),
           "blocking_violations": int(RULES_BEFORE.query("severity == 'blocking'")["violations"].sum())})
n_blocking = int(RULES_BEFORE.loc[RULES_BEFORE["severity"] == "blocking", "violations"].sum())
print(f"{len(RULES)} règles (dont {sum(r.id.startswith('BUS_') for r in RULES)} apprises des données) · "
      f"{int((RULES_BEFORE['violations'] > 0).sum())} en violation · {n_blocking} violation(s) bloquante(s)")
RULES_BEFORE.query("violations > 0").sort_values(["severity", "violations"], ascending=[True, False])
