ROLES = {
    "transaction_id": {"types": {"id"}, "label": "identifier of an event or a transaction"},
    "entity_id": {"types": {"id"}, "label": "identifier of a tracked entity (customer, product, seller…)"},
    "amount": {"types": {"numeric", "integer"}, "label": "monetary amount"},
    "profit": {"types": {"numeric", "integer"}, "label": "profit or margin (can be negative)"},
    "discount": {"types": {"numeric", "integer"}, "label": "discount"},
    "quantity": {"types": {"integer", "numeric"}, "label": "quantity or count"},
    "score": {"types": {"integer", "numeric"}, "label": "rating or score on a scale"},
    "duration": {"types": {"numeric", "integer"}, "label": "duration or delay"},
    "event_date": {"types": {"datetime"}, "label": "date of an event"},
    "flag": {"types": {"category", "integer", "numeric"}, "label": "yes/no indicator (two values)"},
    "status": {"types": {"category"}, "label": "status or state"},
    "category": {"types": {"category", "zip"}, "label": "category used for grouping"},
    "location": {"types": {"category", "zip", "geo"}, "label": "place (country, region, city…)"},
}
MEASURE_ROLES = {"amount", "profit", "discount", "quantity", "score", "duration"}
MAX_GROUP_VALUES = 100                                    # au-delà, une colonne est trop fine pour servir de catégorie (Olist : 71 catégories)


def profile_column(s: pd.Series, semantic: str | None) -> dict:
    """Compact profile of a warehouse column."""
    if semantic == "datetime":
        s = pd.to_datetime(s, errors="coerce")
    elif semantic in {"numeric", "integer", "geo"}:
        s = pd.to_numeric(s, errors="coerce")
    nn = s.dropna()
    prof = {"non_null_pct": round(100 * len(nn) / max(len(s), 1), 2), "distinct": int(nn.nunique())}
    if semantic in {"numeric", "integer", "geo"} and len(nn):
        prof.update(min=float(nn.min()), max=float(nn.max()), mean=round(float(nn.mean()), 4),
                    is_integer=bool((nn == nn.round()).all()), negatives=int((nn < 0).sum()))
        if nn.nunique() <= 2:
            prof["values"] = sorted(float(v) for v in nn.unique())
    elif semantic == "datetime" and len(nn):
        prof.update(min=str(nn.min()), max=str(nn.max()), months=int(nn.dt.to_period("M").nunique()))
    elif len(nn):
        prof["top_values"] = {str(k): int(v) for k, v in nn.astype(str).value_counts().head(8).items()}
    prof["binary"] = prof["distinct"] == 2
    return prof


ROLE_WORDS = {   # indices de nom multilingues (fr, en, pt, es) : connaissance générale, jamais propre à un dataset
    "amount": "price prix preco precio amount montant valor value valeur sales sale vente ventes revenue revenu receita charge charges "
              "fare fee fees cost cout custo total balance solde saldo payment paiement pagamento income salary salaire spend spent "
              "tip tips pourboire freight frete shipping loan pret credit debt gmv turnover ca prime premium",
    "profit": "profit profits benefice margin marge lucro gain gains ebit",
    "discount": "discount discounts remise rabais desconto rebate reduction promo",
    "duration": "duration duree delay delays retard atraso tenure anciennete time temps days jours hours heures minutes seconds "
                "secondes lead wait attente",
    "score": "score scores rating ratings note notes stars etoiles satisfaction nps csat grade avaliacao evaluation",
    "status": "status statut stage etat phase situation outcome resultat result",
    "location": "city ville cidade ciudad state region country pays zip postal borough district address adresse lat lng lon latitude "
                "longitude geo province county estado municipio town area zone neighborhood quartier",
    "quantity": "qty quantity quantite quantidade units unit count nombre number nb contacts calls distance passengers passager "
                "installments parcelas items",
}
ROLE_WORDS = {r: set(w.split()) for r, w in ROLE_WORDS.items()}


WEAK_AMOUNT_WORDS = {"total", "value", "valeur", "valor"}    # « total_of_special_requests » est un comptage, pas un montant
ID_WORDS = {"id", "code", "ref", "agent", "agency", "company", "vendor", "supplier", "store", "shop", "branch", "account"}
DATE_PARTS = {"year": (1900, 2100), "yr": (1900, 2100), "annee": (1900, 2100), "ano": (1900, 2100), "quarter": (1, 4),
              "trimestre": (1, 4), "month": (1, 12), "mois": (1, 12), "mes": (1, 12), "week": (1, 53), "semaine": (1, 53),
              "semana": (1, 53), "day": (1, 31), "jour": (1, 31), "dia": (1, 31), "weekday": (0, 7), "hour": (0, 23),
              "heure": (0, 23), "hora": (0, 23)}
MONTH_WORDS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
               "december", "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
               "novembre", "décembre", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"}


def name_says(col: str, role: str, ignore: set = frozenset()) -> bool:
    """Does the column name contain a word suggesting the role? (exact word or prefix of at least 4 letters)"""
    toks, vocab = words(col).split(), ROLE_WORDS[role] - set(ignore)
    return any(t in vocab or any(len(w) >= 4 and t.startswith(w) for w in vocab) for t in toks)


def date_part(col: str, prof: dict) -> str | None:
    """Date part (year, month, week, day…): a time marker, never a measure nor a segment.
    Recognized by the name ("arrival_date_year", "week_number", "day_of_month") AND by values within the calendar range."""
    toks = [t for t in words(col).split() if t not in {"number", "num", "no", "nb", "of", "the", "de", "du"}]
    part = "day" if toks[-2:] in (["day", "month"], ["day", "week"], ["day", "year"]) else toks[-1] if toks else None
    if part not in DATE_PARTS:
        return None
    if prof.get("top_values"):                         # mois écrits en toutes lettres
        return part if all(str(v).strip().lower() in MONTH_WORDS for v in prof["top_values"]) else None
    lo, hi = DATE_PARTS[part]
    ok = prof.get("min") is not None and prof.get("is_integer") and lo <= prof["min"] and prof["max"] <= hi
    return part if ok else None


def compatible_roles(col: str, meta: dict, prof: dict, is_grain: bool, is_fk: bool, rows: int) -> list[str]:
    """Roles a column CAN play according to its type, its profile and its name (the final choice belongs to the KPI agent)."""
    sem = meta["semantic"]
    if meta.get("derived") == "duration":
        return ["duration"]
    if meta.get("derived") == "flag":
        return ["flag"]
    if sem in {None, "technical", "key", "calendar", "text"}:
        return []
    if date_part(col, prof):
        return []                                          # année, mois, jour… : repère de temps (la date est reconstituée en 7.1)
    numeric, distinct = sem in {"numeric", "integer"}, prof["distinct"]
    integer = bool(prof.get("is_integer"))
    many = distinct >= max(10, 0.01 * rows)                # un identifiant prend beaucoup de valeurs différentes
    if numeric and integer and many and set(words(col).split()) & ID_WORDS and not is_grain:
        return ["entity_id"]                               # code numérique (agent, société…) : se compte, ne s'additionne pas
    measure_ok = numeric and not is_grain and not is_fk and distinct > 1
    is_profit = name_says(col, "profit")                   # un bénéfice n'est jamais un montant de vente ni une remise
    checks = {
        "transaction_id": sem == "id" and many,
        "entity_id": sem == "id" and many,
        "amount": measure_ok and not is_profit and not name_says(col, "duration") and
                  (name_says(col, "amount", WEAK_AMOUNT_WORDS) or (not integer and not (prof.get("min", -1) >= 0 and prof.get("max", 2) <= 1))),
        "profit": measure_ok and (is_profit or (prof.get("negatives", 0) > 0 and not integer)),
        "discount": measure_ok and not is_profit and
                    (name_says(col, "discount") or (prof.get("min", -1) >= 0 and prof.get("max", 2) <= 1 and not integer)),
        "quantity": measure_ok and ((integer and prof.get("negatives", 1) == 0) or name_says(col, "quantity")),
        "score": measure_ok and name_says(col, "score") and prof.get("max", 1e9) <= 100,
        "duration": measure_ok and name_says(col, "duration"),
        "event_date": sem == "datetime",
        "flag": prof["binary"] and (sem == "category" or set(prof.get("values", [])) <= {0, 1, 0.0, 1.0}),
        "status": sem == "category" and 2 <= distinct <= MAX_GROUP_VALUES and name_says(col, "status"),
        "category": sem in {"category", "zip"} and 2 <= distinct <= MAX_GROUP_VALUES,
        "location": (sem == "geo") or (sem in {"category", "zip"} and 2 <= distinct <= MAX_GROUP_VALUES and name_says(col, "location")),
    }
    return [r for r, ok in checks.items() if ok]


def reachable_tables(fact: str) -> dict:
    """Tables reachable from a base fact: itself (measures + attributes) and the joined tables (attributes only)."""
    reach = {fact: "base"}
    for col, (target, key) in BI_INPUT["tables"][fact]["fks"].items():
        if target in BI_INPUT["tables"] and target not in reach:
            reach[target] = "parent fact" if BI_INPUT["tables"][target]["kind"] == "fact" else "dimension"
    return reach


def build_inventory() -> pd.DataFrame:
    rows = []
    for t, spec in BI_INPUT["tables"].items():
        df = BI_WH.query(f"SELECT * FROM {qi(t)}")
        fk_cols = set(spec["fks"]) | {c for s in BI_INPUT["tables"].values() for c, (tg, k) in s["fks"].items() if tg == t and k == c}
        for c, meta in spec["columns"].items():
            if meta["semantic"] in {"technical", "key", "calendar"}:
                continue
            if meta["semantic"] is None:                  # colonne non documentée : type déduit des valeurs
                meta = {**meta, "semantic": "numeric" if pd.api.types.is_numeric_dtype(df[c]) else "category"}
            prof = profile_column(df[c], meta["semantic"])
            roles = compatible_roles(c, meta, prof, c in spec["grain"], c in fk_cols, len(df))
            semantic = "date_part" if meta["semantic"] in {"integer", "numeric", "category"} and date_part(c, prof) else meta["semantic"]
            rows.append({"table": t, "table_kind": spec["kind"], "rows": len(df), "column": c, "semantic": semantic,
                         "origin": meta["origin"], "roles": roles, "is_grain": c in spec["grain"], "is_fk": c in fk_cols,
                         **{k: prof.get(k) for k in ("non_null_pct", "distinct", "binary", "min", "max", "mean", "negatives",
                                                     "months", "top_values")}})
        del df
        gc.collect()
    return pd.DataFrame(rows)


BI_INVENTORY = build_inventory()
ROLE_COVERAGE = {r: sorted(BI_INVENTORY.loc[BI_INVENTORY["roles"].map(lambda x: r in x), "column"].unique().tolist())
                 for r in ROLES}
AUDIT.log("bi_bridge", "inventory_built", {"columns": len(BI_INVENTORY), "role_coverage": {r: len(c) for r, c in ROLE_COVERAGE.items()}})
print(f"{len(BI_INVENTORY)} analyzable columns · roles covered: "
      + ", ".join(f"{r} ({len(c)})" for r, c in ROLE_COVERAGE.items() if c))
print("Missing roles:", [r for r, c in ROLE_COVERAGE.items() if not c] or "none")
BI_INVENTORY[["table", "column", "semantic", "origin", "distinct", "roles"]].assign(roles=lambda d: d["roles"].map(", ".join))
