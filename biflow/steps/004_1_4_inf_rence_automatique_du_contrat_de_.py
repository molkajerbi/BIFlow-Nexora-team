import gc
import itertools
import re

DATE_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%SZ",
                "%Y/%m/%d", "%Y-%m-%d %H:%M:%S.%f", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
                "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y%m%d"]
NUMBER_PATTERN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?"          # 12 · -3.5 · 1e10
COMMA_NUMBER_PATTERN = r"[+-]?\d{1,3}(?:[ .]\d{3})+(?:,\d+)?|[+-]?\d+(?:,\d+)?"   # 12,5 · 1 234,56 · 1.234,5
KEY_TYPES = {"id", "zip", "category", "integer"}


def snake(name: str) -> str:
    """'Order Date' / 'OrderDate' -> 'order_date' (noms sûrs)."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name))
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower()
    return s if s and not s[0].isdigit() else f"t_{s}"


def singular(name: str) -> str:
    return name[:-3] + "y" if name.endswith("ies") else name[:-1] if name.endswith("s") else name


# ---------- Lecture de n'importe quel format, toujours en texte (aucune interprétation) ----------
def _as_text(df: pd.DataFrame) -> pd.DataFrame:
    df = df.astype("string")
    df.columns = [str(c) for c in df.columns]
    return df.replace({"": pd.NA})


def read_table(path: Path, spec: dict) -> pd.DataFrame:
    fmt = spec["format"]
    if fmt == "csv":
        return pd.read_csv(path, dtype="string", keep_default_na=False, na_values=[""],
                           sep=spec.get("sep", ","), encoding=spec.get("encoding", "utf-8-sig"))
    if fmt == "excel":
        return _as_text(pd.read_excel(path, sheet_name=spec["sheet"], dtype=str, keep_default_na=False, na_values=[""]))
    if fmt == "parquet":
        return _as_text(pd.read_parquet(path))
    if fmt == "json":
        try:
            return _as_text(pd.read_json(path, dtype=False))
        except ValueError:
            return _as_text(pd.read_json(path, lines=True, dtype=False))
    raise ValueError(f"format non pris en charge : {fmt}")


def sniff(path: Path) -> list[dict]:
    """Détecte le format et ses paramètres. Un classeur Excel donne une table par feuille."""
    ext = path.suffix.lower()
    if ext in {".xlsx", ".xls"}:
        return [{"format": "excel", "sheet": s} for s in pd.ExcelFile(path).sheet_names]
    if ext == ".parquet":
        return [{"format": "parquet"}]
    if ext == ".json":
        return [{"format": "json"}]
    for encoding in ("utf-8-sig", "latin-1"):                  # CSV / TSV / TXT
        try:
            with path.open(encoding=encoding) as f:
                header = f.readline()
                f.read(1 << 20)                                 # vérifie aussi le début du fichier
            return [{"format": "csv", "sep": max([",", ";", "\t", "|"], key=header.count), "encoding": encoding}]
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{path.name} : encodage non reconnu")


def table_names(keys: list[str]) -> list[str]:
    """Nom de table = nom de fichier nettoyé (préfixe commun type 'olist_' et suffixe '_dataset' retirés)."""
    stems = [re.sub(r"_(dataset|data|table)$", "", snake(k)) for k in keys]
    first = pd.Series([s.split("_")[0] for s in stems]).value_counts()
    if len(stems) > 1 and first.iloc[0] >= max(2, len(stems) / 2):
        prefix = first.index[0] + "_"
        stems = [s[len(prefix):] if s.startswith(prefix) and len(s) > len(prefix) else s for s in stems]
    names = []
    for s in stems:
        names.append(s if s not in names else f"{s}_{len(names)}")
    return names


# ---------- Typage sémantique d'une colonne ----------
UNIT_RE = r"\s*(?:€|\$|£|¥|%|EUR|USD|GBP|TND|DT|MAD)\s*"                # symboles retirés avant lecture
US_NUMBER_PATTERN = r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?"                    # 1,234.50


def clean_number_text(s: pd.Series, fmt: dict | None) -> pd.Series:
    """Texte -> texte numérique standard ('1 234,50 €' -> '1234.50') selon le format détecté pour la colonne."""
    if not fmt:
        return s
    if fmt.get("unit"):
        s = s.str.replace(UNIT_RE, "", regex=True).str.strip()
    if fmt.get("decimal") == ",":
        s = s.str.replace(r"[ .\u00a0\u202f]", "", regex=True).str.replace(",", ".", regex=False)
    elif fmt.get("thousands") == ",":
        s = s.str.replace(",", "", regex=False)
    return s


def number_format(sample: pd.Series) -> tuple[float, dict | None]:
    """Part des valeurs qui sont des nombres, et leur écriture : 12.5 · 1,234.5 · 12,5 · 1 234,5 · 12 € · 15 %."""
    units = sample.str.extract("(" + UNIT_RE.strip("\\s*") + ")", expand=False).dropna().str.strip()
    unit = units.mode()[0] if len(units) >= 0.5 * len(sample) else ""
    base = sample.str.replace(UNIT_RE, "", regex=True).str.strip() if unit else sample
    ratio = lambda p: float(base.str.fullmatch(p, na=False).mean())
    has_comma = base.str.contains(",", regex=False).any()
    r_dot = ratio(NUMBER_PATTERN)
    r_us = ratio(f"{US_NUMBER_PATTERN}|{NUMBER_PATTERN}") if has_comma else 0.0
    r_eu = ratio(COMMA_NUMBER_PATTERN) if has_comma else 0.0
    if r_dot >= 0.98:
        return r_dot, ({"decimal": ".", "unit": unit} if unit else None)
    if r_eu >= 0.98 and (r_us < 0.98 or base.str.contains(r",\d{1,2}$|,\d{4,}$", regex=True).any()):
        return r_eu, {"decimal": ",", "unit": unit}
    if r_us >= 0.98:
        return r_us, {"decimal": ".", "thousands": ",", "unit": unit}
    return max(r_dot, r_us, r_eu), None


def is_day_month_swap(a: str, b: str) -> bool:
    return a.replace("%d", "@").replace("%m", "%d").replace("@", "%m") == b


def infer_type(name: str, s: pd.Series) -> tuple[str, Any]:
    """Type sémantique d'une colonne, déduit de son nom ET de ses valeurs.
    Renvoie aussi le format : format de date (ou {'ambiguous': [...]}) ou écriture des nombres."""
    values = s.dropna()
    if values.empty:
        return "text", None
    sample = values.drop_duplicates().head(5000)
    tokens = snake(name).split("_")
    num_ratio, num_fmt = number_format(sample)              # regex : jamais de conversion risquée
    if num_ratio < 0.5 and sample.str.contains(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}", regex=True).mean() > 0.9:
        scores = {f: pd.to_datetime(sample, format=f, errors="coerce").notna().mean() for f in DATE_FORMATS}
        best = max(scores.values())
        if best >= 0.95:
            top = [f for f in DATE_FORMATS if scores[f] == best]
            swap = [f for f in top[1:] if is_day_month_swap(f, top[0])]
            return "datetime", ({"ambiguous": [top[0], swap[0]]} if swap else top[0])   # 01/02 : jour ou mois ?
    if num_ratio >= 0.95 and set(tokens) & {"lat", "latitude", "lng", "lon", "long", "longitude"}:
        return "geo", num_fmt
    if set(tokens) & {"zip", "zipcode", "postal", "postcode", "cep"}:
        return "zip", None
    id_words, code_words = {"id", "key", "uuid", "guid", "pk", "fk"}, {"code", "sku", "ref", "num", "no"}
    if tokens[-1] in id_words or (tokens[0] in id_words and len(tokens) > 1) or \
            ((tokens[-1] in code_words or tokens[0] in code_words) and len(tokens) > 1 and values.nunique() > 100):
        return "id", None
    if num_ratio >= 0.98 and not sample.str.match(r"0\d").mean() > 0.05:     # '01310' est un code, pas un nombre
        x = clean_number_text(sample, num_fmt)
        x = x[x.str.fullmatch(NUMBER_PATTERN, na=False)]
        x = pd.Series([float(v) for v in x], dtype="float64")
        return ("integer" if (x == x.round()).all() else "numeric"), num_fmt
    if not sample.str.contains(r"\s").any() and values.is_unique and len(values) >= 20 and sample.str.len().mean() <= 64:
        return "id", None
    distinct = values.nunique()
    if sample.str.len().mean() <= 60 and (distinct <= 100 or distinct <= 0.2 * len(values)):
        return "category", None
    return "text", None


# ---------- Grain : plus petite combinaison unique (1 à 3 colonnes) ----------
def infer_grain(table: str, df: pd.DataFrame, types: dict) -> list[str] | None:
    body = df[list(types)].drop_duplicates()                   # un doublon exact ne remet pas en cause le grain
    def rank(c):
        stem = re.sub(r"^(id|key|code)_|_(id|key|code)$", "", snake(c))
        return (types[c] != "id", not (stem in table or singular(table) in stem), list(types).index(c))
    keys = sorted([c for c, t in types.items() if t in {"id", "integer", "zip", "category", "datetime"}
                   and body[c].notna().all()], key=rank)
    for c in keys:
        if body[c].is_unique:
            return [c]
    for size, pool in ((2, keys[:8]), (3, keys[:6])):
        for combo in itertools.combinations(pool, size):
            if sum(types[c] == "datetime" for c in combo) < size and not body.duplicated(subset=list(combo)).any():
                return list(combo)
    return None


# ---------- Relations : dépendances d'inclusion + correspondance des noms ----------
def key_name(table: str, col: str) -> str:
    """Nom de clé sans le préfixe de la table : geolocation_zip_code_prefix -> zip_code_prefix."""
    s = snake(col)
    for p in (singular(table) + "_", table + "_"):
        if s.startswith(p) and len(s) > len(p):
            return s[len(p):]
    return s


def names_match(child: str, col: str, parent: str, pk: str) -> bool:
    c, p = snake(col), snake(pk)
    if p in {"id", "key", "code"}:                             # 'id' seul : il faut 'customer_id' -> customers.id
        return c in {f"{singular(parent)}_{p}", f"{parent}_{p}", f"{p}_{singular(parent)}", f"{p}_{parent}"}
    kp = key_name(parent, pk)
    return c == p or c.endswith("_" + p) or key_name(child, col) == kp or (len(kp) > 3 and c.endswith("_" + kp))


def family(sem: str) -> str:
    return "integer" if sem == "integer" else "text"


def infer_relationships(values: dict, types: dict, grains: dict) -> list[dict]:
    """Une colonne pointe vers une clé d'une autre table si ses valeurs y sont (en majorité) incluses.
    Clé unique (grain) : relation classique. Table sans grain (ex. plusieurs points GPS par code postal) :
    relation 'à agréger' (la dimension sera agrégée sur cette clé)."""
    targets = []
    for t, g in grains.items():
        if g and len(g) == 1:
            targets.append((t, g[0], False))
        elif not g:
            targets += [(t, c, True) for c, s in types[t].items() if s in {"id", "zip"} and (t, c) in values]
    type_rank = {"id": 0, "zip": 1, "integer": 2, "category": 3}
    rels = []
    for (child, col), child_values in values.items():
        typ, own_key = types[child][col], grains[child] == [col]
        best = None
        for parent, pk, aggregate in targets:
            if parent == child or family(types[parent][pk]) != family(typ) or not child_values:
                continue                                       # clés comparables : texte avec texte, entier avec entier
            if own_key and re.sub(r"^(id|key|code)_|_(id|key|code)$", "", snake(col)) != singular(parent):
                continue                                       # 1:1 : le parent est la table qui porte le nom de la clé
            inclusion = len(child_values & values[(parent, pk)]) / len(child_values)
            same_name = names_match(child, col, parent, pk)
            by_values = (not aggregate and family(typ) == "text" and inclusion >= 0.95 and len(child_values) >= 20
                         and len(values[(parent, pk)]) >= len(child_values))          # noms différents, mêmes valeurs
            ok = (same_name and inclusion >= (0.8 if aggregate else 0.5)) or by_values
            if ok and (best is None or (same_name, inclusion) > best[0]):
                best = ((same_name, inclusion), {"child": child, "fk": col, "parent": parent, "pk": pk,
                                                 "aggregate": aggregate, "inclusion_pct": round(100 * inclusion, 2),
                                                 "same_name": same_name})
        if best:
            rels.append(best[1])
    # une seule relation par couple (table enfant, table parente) : la plus fiable
    rels.sort(key=lambda r: (type_rank[types[r["child"]][r["fk"]]], -r["inclusion_pct"]))
    kept, seen = [], set()
    for r in rels:
        if (r["child"], r["parent"]) not in seen:
            kept.append(r)
            seen.add((r["child"], r["parent"]))
    return kept


def infer_roles(types: dict, grains: dict, rels: list[dict]) -> dict:
    """Fait = table d'événements (dates) ou de mesures non référencée ; dimension = table référencée (entité)."""
    parents, children = {r["parent"] for r in rels}, {r["child"] for r in rels}
    roles = {}
    for t, cols in types.items():
        fks = {r["fk"] for r in rels if r["child"] == t}
        has_date = "datetime" in cols.values()
        measures = [c for c, s in cols.items() if s in {"numeric", "integer"} and c not in (grains[t] or []) and c not in fks]
        roles[t] = "fait" if (has_date and (t in children or t not in parents)) or (t not in parents and measures) else "dimension"
    return roles


def ram_used_gb() -> float:
    import psutil                                    # mémoire utilisée, sur tous les systèmes
    return psutil.Process().memory_info().rss / 1e9


def infer_contract(data_dir: Path) -> dict:
    """Lit les fichiers UN PAR UN (mémoire libérée après chaque table) et propose le contrat complet."""
    entries = []                                               # (clé de nom, chemin, paramètres de lecture)
    for path in list_data_files(data_dir):
        rel, sheets = str(path.relative_to(data_dir).with_suffix("")), sniff(path)
        for spec in sheets:
            entries.append((rel + (f"_{spec['sheet']}" if len(sheets) > 1 else ""), path, spec))
    assert entries, f"aucun fichier de données dans {data_dir}"
    specs, types, formats, number_formats, grains, stats, values = {}, {}, {}, {}, {}, {}, {}
    ambiguous = {}
    for name, (key, path, spec) in zip(table_names([e[0] for e in entries]), entries):
        t0 = time.perf_counter()
        df = read_table(path, spec)
        specs[name], types[name] = {"file": str(path.relative_to(data_dir)), **spec}, {}
        for c in df.columns:
            types[name][c], extra = infer_type(c, df[c])
            if isinstance(extra, dict) and "ambiguous" in extra:
                ambiguous[f"{name}.{c}"] = extra["ambiguous"]
            elif isinstance(extra, dict):
                number_formats[c] = extra
            elif extra:
                formats[f"{name}.{c}"] = extra
        grains[name] = infer_grain(name, df, types[name])
        stats[name] = {"rows": len(df), "missing_columns": int(df.isna().any().sum()),
                       "numeric_columns": sum(s in {"numeric", "integer"} for s in types[name].values())}
        for c, sem in types[name].items():                     # on ne garde que les valeurs utiles aux relations
            if sem in KEY_TYPES:
                values[(name, c)] = set(df[c].dropna().unique())
        del df
        gc.collect()
        print(f"  {specs[name]['file'][:45]:45s} {stats[name]['rows']:>10,} lignes · grain {grains[name]} · "
              f"{time.perf_counter() - t0:.1f} s · RAM {ram_used_gb():.1f} Go", flush=True)
    # Dates ambiguës (01/02/2023) : on suit l'ordre jour/mois des autres dates du dataset (sinon jour/mois)
    day_first = sum(f.find("%d") < f.find("%m") for f in formats.values() if "%d" in f and f.find("%Y") > 0)
    month_first = sum(f.find("%m") < f.find("%d") for f in formats.values() if "%d" in f and f.find("%Y") > 0)
    for key, options in ambiguous.items():
        formats[key] = next(f for f in options if (f.find("%d") < f.find("%m")) == (day_first >= month_first))
    rels = infer_relationships(values, types, grains)
    del values
    gc.collect()
    roles = infer_roles(types, grains, rels)
    aggregated = {r["parent"] for r in rels if r["aggregate"]}
    # Points à vérifier : ce que l'inférence n'a pas pu établir avec certitude
    checks = [f"{t} : aucun grain trouvé" for t in specs if not grains[t] and t not in aggregated and roles[t] == "dimension"]
    checks += [f"{r['child']}.{r['fk']} -> {r['parent']} : seulement {r['inclusion_pct']} % des valeurs retrouvées"
               for r in rels if r["inclusion_pct"] < 95]
    checks += [f"{k} : date ambiguë (jour/mois), lue comme {formats[k]}" for k in ambiguous]
    checks += [f"{r['child']}.{r['fk']} -> {r['parent']}.{r['pk']} : relation trouvée par les valeurs (noms différents)"
               for r in rels if not r["same_name"]]
    checks += [f"{t} : table isolée (aucune relation)" for t in specs
               if len(specs) > 1 and t not in {r['child'] for r in rels} | {r['parent'] for r in rels}]
    confidence = round(100 * (1 - len(checks) / max(len(specs) + len(rels), 1)), 1)
    contract = {t: {**specs[t], "description": f"{stats[t]['rows']} lignes, {len(types[t])} colonnes (rôle : {roles[t]})",
                    "grain": grains[t], "columns": types[t]} for t in specs}
    return {"contract": contract, "relationships": [{k: r[k] for k in ("child", "fk", "parent", "pk", "aggregate")} for r in rels],
            "relationship_details": rels, "formats": formats, "number_formats": number_formats, "roles": roles,
            "stats": stats, "checks": checks, "confidence": max(confidence, 0.0)}


print("Fonctions d'inférence du contrat prêtes")
