import gc
import glob
import itertools
import os
import re
import sqlite3
import shutil
import time

# ---------------------------------------------------------------- appel LLM de la partie 2 : tracé et protégé
LLM_LOG = RUN_DIR / "llm_calls.jsonl"      # échanges complets avec le LLM (prompt + réponse), référencés dans l'audit


def free_gpu_memory() -> None:
    """Frees the GPU memory left by previous calls (essential with the long prompts of part 2 on a T4).
    After an error, Jupyter keeps the traceback of the exception, which holds the tensors: it is freed too."""
    import sys
    sys.last_type = sys.last_value = sys.last_traceback = None
    gc.collect()
    pass                                             # déploiement sur processeur : pas de mémoire GPU à libérer


def llm_call(agent: str, messages: list[dict], max_new_tokens: int = 256) -> str:
    """Calls the LLM and traces the call: fingerprint, duration and answer in the audit log; full prompt and answer in llm_calls.jsonl.
    A lack of GPU memory does not crash the pipeline: the answer is empty and the supervisor switches to its fallback."""
    t0 = time.perf_counter()
    prompt_sha = sha256_text(canonical_json(messages))
    free_gpu_memory()
    try:
        response, error = LLM.chat(messages, max_new_tokens), None
    except Exception as exc:                             # torch.cuda.OutOfMemoryError et autres erreurs de génération
        if "out of memory" not in str(exc).lower() and type(exc).__name__ != "OutOfMemoryError":
            raise
        response, error = "", f"{type(exc).__name__}: not enough GPU memory"
        free_gpu_memory()
    seconds = round(time.perf_counter() - t0, 2)
    with LLM_LOG.open("a", encoding="utf-8") as f:
        f.write(canonical_json({"ts": utc_now(), "agent": agent, "prompt_sha256": prompt_sha, "messages": messages,
                                "max_new_tokens": max_new_tokens, "response": response, "error": error, "seconds": seconds}) + "\n")
    AUDIT.log(agent, "llm_call", {"prompt_sha256": prompt_sha, "prompt_chars": sum(len(m["content"]) for m in messages),
                                  "response": response[:600], "response_sha256": sha256_text(response), "error": error,
                                  "seconds": seconds}, level="WARNING" if error else "INFO")
    if error:
        print(f"⚠ {agent}: {error}; the supervisor uses its fallback")
    return response


TECH_COLUMNS = {"_source_row_id", "_dq_flags", "is_unknown_member", "source_rows"}
CALENDAR_COLUMNS = {"date_key", "date", "year", "quarter", "month", "month_name", "year_month", "week", "day_of_week", "is_weekend"}


def qi(name: str) -> str:
    """Quoted SQL name (spaces, capitals)."""
    return '"' + str(name).replace('"', '""') + '"'


def words(name: str) -> str:
    """'order_purchase_timestamp' / 'MonthlyCharges' / 'Order Date' -> 'order purchase timestamp' / 'monthly charges' / 'order date'."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(name))
    return re.sub(r"[^0-9a-zA-ZÀ-ÿ]+", " ", s).strip().lower()


class BIWarehouse:
    """Read-only access to the part 1 warehouse (DuckDB or SQLite), used after a restart."""

    def __init__(self, path: str):
        self.path, self.engine = Path(path), "duckdb" if str(path).endswith(".duckdb") else "sqlite"
        if self.engine == "duckdb":
            import duckdb
            self.con = duckdb.connect(str(path), read_only=True)
        else:
            self.con = sqlite3.connect(str(path))

    def query(self, sql: str) -> pd.DataFrame:
        return self.con.execute(sql).df() if self.engine == "duckdb" else pd.read_sql_query(sql, self.con)


def source_table(name: str, spec: dict) -> str | None:
    """Original cleaned table of a star schema table."""
    if spec.get("lineage"):
        return spec["lineage"]
    stem = re.sub(r"^(dim|fact)_", "", name)
    if stem in DATA_CONTRACT:
        return stem
    m = re.search(r"FROM stg_(\w+)", spec["sql"])
    return m.group(1) if m and m.group(1) in DATA_CONTRACT else None


def column_meta(name: str, col: str, spec: dict, source: str | None, derived: dict) -> dict:
    """Semantic type and origin of a warehouse column (inferred from part 1, never from a dataset name)."""
    if col in TECH_COLUMNS:
        return {"semantic": "technical", "origin": "technical"}
    if name == "dim_date":
        return {"semantic": "key" if col == "date_key" else "calendar", "origin": "calendar"}
    if col.endswith("_date_key"):
        return {"semantic": "key", "origin": "date key"}
    if source and (source, col) in derived:
        kind = derived[(source, col)]
        return {"semantic": "numeric" if kind.startswith("duration") else "integer",
                "origin": "derived indicator: " + kind, "derived": "duration" if kind.startswith("duration") else "flag"}
    if col in spec.get("sums", {}) and source and col not in DATA_CONTRACT[source]["columns"]:
        return {"semantic": "numeric", "origin": "aggregate of a child fact (sum per key)"}
    if col.endswith("_count") and source and col not in DATA_CONTRACT[source]["columns"]:
        return {"semantic": "integer", "origin": "aggregate of a child fact (row count)"}
    if source and col in DATA_CONTRACT[source]["columns"]:
        return {"semantic": DATA_CONTRACT[source]["columns"][col], "origin": "source"}
    for t, s in DATA_CONTRACT.items():                    # clé propagée d'un fait parent ou attribut d'une dimension jointe
        if col in s["columns"]:
            return {"semantic": s["columns"][col], "origin": f"inherited from {t}"}
    return {"semantic": None, "origin": "unknown"}


def build_handoff() -> dict:
    """Assembles the handoff file from the final state of part 1."""
    assert DATA_PREP_RESULT["status"] == "success", "Part 1 must end with the success status."
    derived = {(r.table, r.column): r.type for r in DERIVED.itertuples()}
    tables = {}
    for name, spec in ETL_TEMPLATES.items():
        if ETL_STATUS.get(name) != "tested":
            continue
        source = source_table(name, spec)
        cols = list(WH.query(f"SELECT * FROM {qi(name)} LIMIT 0").columns)
        tables[name] = {
            "kind": spec["type"], "grain": spec["grain"], "source": source, "rows": ETL_RESULTS[name]["rows"],
            "description": (DATA_CONTRACT[source]["description"] if source and name != "dim_date" else spec["description"]),
            "fks": {c: list(v) for c, v in spec.get("fks", {}).items()},
            "checked_sums": sorted(spec.get("sums", {})),
            "columns": {c: column_meta(name, c, spec, source, derived) for c in cols}}
    violated = RULES_AFTER[RULES_AFTER["violations"] > 0]
    return {
        "run_id": RUN_ID, "created_at": utc_now(), "domain": DOMAIN,
        "warehouse": {"engine": SQL_ENGINE, "path": str(WH.path)},
        "tables": tables,
        "quality": {"status": STATUS, "scores_after": {k: float(v) for k, v in SCORES_AFTER.items()},
                    "open_rules": violated[["rule", "table", "dimension", "description", "violations"]].to_dict(orient="records")},
        "data_prep_audit_sha256": AUDIT.events[-1]["hash"]}


INPUT_ROOT = Path(os.environ.get("BIFLOW_INPUT_ROOT", "/kaggle/input"))


def latest_handoff() -> Path:
    """Latest handoff file: first in the working folder, otherwise in a notebook output
    attached as an input (Add Input → Your Work). In that case the run is copied to a writable place and its paths fixed."""
    found = sorted(glob.glob(str(CONFIG.output_root / "*" / "bi_handoff.json")))
    if found:
        return Path(found[-1])
    found = sorted(glob.glob(str(INPUT_ROOT / "**" / "bi_handoff.json"), recursive=True), key=lambda p: Path(p).parent.name)
    assert found, ("No handoff file: run the complete part 1, "
                   "or attach as an input the output of a saved version of the notebook.")
    src = Path(found[-1]).parent
    dst = CONFIG.output_root / src.name
    if not dst.exists():
        shutil.copytree(src, dst)
    handoff = json.loads((dst / "bi_handoff.json").read_text(encoding="utf-8"))
    old = Path(handoff["warehouse"]["path"])
    rel = Path(*old.parts[old.parts.index(src.name) + 1:]) if src.name in old.parts else Path(old.name)
    handoff["warehouse"]["path"] = str(dst / rel)
    (dst / "bi_handoff.json").write_text(canonical_json(handoff), encoding="utf-8")
    print(f"Previous run copied from the inputs: {src} → {dst}")
    return dst / "bi_handoff.json"


if "DATA_PREP_RESULT" in globals() and DATA_PREP_RESULT.get("status") == "success" and "WH" in globals():
    BI_INPUT, BI_WH = build_handoff(), WH                 # même session : on consomme directement la partie 1
    HANDOFF_PATH = RUN_DIR / "bi_handoff.json"
    HANDOFF_PATH.write_text(canonical_json(BI_INPUT), encoding="utf-8")
    handoff_mode = "same session"
else:                                                     # session redémarrée : on recharge le dernier dossier
    HANDOFF_PATH = latest_handoff()
    BI_INPUT = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))
    BI_WH = BIWarehouse(BI_INPUT["warehouse"]["path"])
    handoff_mode = "reloaded from " + str(HANDOFF_PATH.parent.name)

HANDOFF_SHA256 = sha256_text(canonical_json(BI_INPUT))
BI_FACTS = [t for t, s in BI_INPUT["tables"].items() if s["kind"] == "fact"]
if not BI_FACTS:            # aucun fait (ex. une seule table de référence) : la table principale sert de base de calcul
    BI_FACTS = [max((t for t in BI_INPUT["tables"] if t != "dim_date"), key=lambda t: BI_INPUT["tables"][t]["rows"])]

# ---------------------------------------------------------------- dates éclatées en colonnes année / mois / jour

MONTH_NUMBERS = {m: i + 1 for names in (
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"],
    ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"])
    for i, m in enumerate(names)}
MONTH_NUMBERS.update({m[:3]: i for m, i in list(MONTH_NUMBERS.items())})
SPLIT_PARTS = {"year": {"year", "yr", "annee", "année", "ano", "año"}, "month": {"month", "mois", "mes"},
               "day": {"day", "jour", "dia", "día"}}


def split_part(col: str) -> tuple[str, str] | None:
    """"arrival_date_year" → ("arrival date", "year"); "arrival_date_day_of_month" → ("arrival date", "day")."""
    toks = [t for t in words(col).split() if t not in {"of", "the", "de", "du", "number", "num", "no"}]
    if len(toks) >= 2 and toks[-2] in SPLIT_PARTS["day"] and toks[-1] in SPLIT_PARTS["month"]:
        return " ".join(toks[:-2]), "day"
    for part, vocab in SPLIT_PARTS.items():
        if toks and toks[-1] in vocab:
            return " ".join(toks[:-1]), part
    return None


def month_number(s: pd.Series) -> pd.Series:
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() > 0.95:
        return num.where(num.between(1, 12))
    return s.astype("string").str.strip().str.lower().map(MONTH_NUMBERS).astype("Float64")


def split_dates(table: str, df: pd.DataFrame) -> list[dict]:
    """Finds a split date (same prefix, year + month, optional day) whose values are in the calendar."""
    groups = {}
    for c in df.columns:
        sp = split_part(c)
        if sp and c not in TECH_COLUMNS:
            groups.setdefault(sp[0], {}).setdefault(sp[1], c)
    found = []
    for prefix, parts in sorted(groups.items()):
        if not {"year", "month"} <= set(parts):
            continue
        y, m = pd.to_numeric(df[parts["year"]], errors="coerce"), month_number(df[parts["month"]])
        d = pd.to_numeric(df[parts["day"]], errors="coerce") if "day" in parts else pd.Series(1, index=df.index)
        if not (y.between(1900, 2100).mean() > 0.95 and m.notna().mean() > 0.95 and d.between(1, 31).mean() > 0.95):
            continue
        date = pd.to_datetime(pd.DataFrame({"year": y, "month": m, "day": d}).astype("float"), errors="coerce")
        stem = "_".join(prefix.split())
        name = stem if stem.endswith("date") else (stem + "_date" if stem else "date")
        if name in df.columns or date.notna().mean() < 0.95:
            continue
        found.append({"table": table, "column": name, "parts": parts, "values": date})
    return found


class BIWorkspace:
    """In-memory working copy (DuckDB) of the warehouse, enriched with the rebuilt dates. The part 1 warehouse is
    never modified; only used when a split date exists."""

    def __init__(self, source, frames: dict):
        self.path = getattr(source, "path", None)
        try:
            import duckdb
            self.engine, self.con = "duckdb", duckdb.connect()
            for name, df in frames.items():
                self.con.register("_frame", df)
                self.con.execute(f"CREATE TABLE {qi(name)} AS SELECT * FROM _frame")
                self.con.unregister("_frame")
        except ImportError:                                # repli : SQLite en mémoire
            self.engine, self.con = "sqlite", sqlite3.connect(":memory:")
            for name, df in frames.items():
                df.to_sql(name, self.con, index=False)

    def query(self, sql: str) -> pd.DataFrame:
        return self.con.execute(sql).df() if self.engine == "duckdb" else pd.read_sql_query(sql, self.con)


TEXT_DATE_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p",
                     "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
                     "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"]


def text_dates(table: str, df: pd.DataFrame) -> list[dict]:
    """Dates left as text (format not recognized upstream, e.g. "06/26/2022 03:00:00 PM"): recognized if a single format
    reads at least 95% of the values, between 1900 and 2100."""
    found = []
    for c, meta in BI_INPUT["tables"][table]["columns"].items():
        if meta["semantic"] not in {"text", None} or c not in df or df[c].dtype.kind in "biufcM":
            continue
        vals = df[c].dropna().astype(str).str.strip()
        if len(vals) < 10 or not vals.str.contains(r"\d").all():
            continue
        sample = vals.sample(min(500, len(vals)), random_state=0)
        for fmt in TEXT_DATE_FORMATS:
            if pd.to_datetime(sample, format=fmt, errors="coerce").notna().mean() < 0.95:
                continue
            parsed = pd.to_datetime(df[c].astype("string").str.strip(), format=fmt, errors="coerce")
            ok = parsed.dropna()
            if len(ok) >= 0.95 * len(vals) and ok.dt.year.between(1900, 2100).all():
                found.append({"table": table, "column": c, "values": parsed, "how": f"text in format {fmt}"})
            break
    return found


def durations(table: str, dates: list[dict]) -> list[dict]:
    """Duration between two recognized dates of the same row (e.g. creation → closing), when the second follows the first
    in at least 95% of the rows: "Created_Date_to_Closed_Date_days"."""
    out = []
    for a, b in itertools.permutations(dates, 2):
        d = (b["values"] - a["values"]).dt.total_seconds() / 86400
        if d.notna().sum() >= 30 and (d.dropna() >= 0).mean() >= 0.95 and a["values"].notna().mean() >= b["values"].notna().mean():
            name = f"{a['column']}_to_{b['column']}_days"           # même convention que les délais de la partie 1
            out.append({"table": table, "column": name, "values": d.where(d >= 0), "how": f"{a['column']} → {b['column']}"})
    return out


REBUILT_DATES, REBUILT_DURATIONS = [], []
frames = {t: BI_WH.query(f"SELECT * FROM {qi(t)}") for t in BI_FACTS}
for t in BI_FACTS:
    found = split_dates(t, frames[t]) + text_dates(t, frames[t])
    REBUILT_DATES += found
    REBUILT_DURATIONS += durations(t, [r for r in found if "how" in r])
if REBUILT_DATES:
    frames.update({t: BI_WH.query(f"SELECT * FROM {qi(t)}") for t in BI_INPUT["tables"] if t not in frames})
    for r in REBUILT_DATES:
        frames[r["table"]][r["column"]] = r["values"]
        frames[r["table"]][r["column"] + "_date_key"] = pd.to_numeric(r["values"].dt.strftime("%Y%m%d"), errors="coerce").astype("Int64")
        how = r.get("how") or "rebuilt date (" + " + ".join(r["parts"][p] for p in ("year", "month", "day") if p in r["parts"]) + ")"
        BI_INPUT["tables"][r["table"]]["columns"].update({
            r["column"]: {"semantic": "datetime", "origin": how, "derived": "date"},
            r["column"] + "_date_key": {"semantic": "key", "origin": "date key"}})
    for r in REBUILT_DURATIONS:
        frames[r["table"]][r["column"]] = r["values"]
        BI_INPUT["tables"][r["table"]]["columns"][r["column"]] = {"semantic": "numeric", "origin": f"derived duration ({r['how']})",
                                                                  "derived": "duration"}
    BI_WH = BIWorkspace(BI_WH, frames)
    AUDIT.log("bi_bridge", "dates_rebuilt", {"dates": [{"table": r["table"], "column": r["column"],
                                                        "source": r.get("how") or r["parts"]} for r in REBUILT_DATES],
                                             "durations": [{k: r[k] for k in ("table", "column", "how")} for r in REBUILT_DURATIONS]},
              level="DECISION")
    print("Rebuilt date(s): " + " · ".join(f"{r['table']}.{r['column']} ← "
                                           + (r.get("how") or " + ".join(r["parts"].values())) for r in REBUILT_DATES))
    if REBUILT_DURATIONS:
        print("Derived duration(s): " + " · ".join(f"{r['column']} ({r['how']})" for r in REBUILT_DURATIONS))
del frames
gc.collect()
AUDIT.log("bi_bridge", "handoff_loaded", {"mode": handoff_mode, "path": HANDOFF_PATH, "sha256": HANDOFF_SHA256,
                                         "domain": BI_INPUT["domain"], "tables": list(BI_INPUT["tables"]),
                                         "quality_status": BI_INPUT["quality"]["status"]})
print(f"Handoff file ({handoff_mode}) · fingerprint {HANDOFF_SHA256[:12]}…")
print(f"Domain: {BI_INPUT['domain']} · quality: {BI_INPUT['quality']['status']} · "
      f"base table(s): {', '.join(BI_FACTS)} · "
      f"{len(BI_INPUT['quality']['open_rules'])} quality rule(s) still flagged")
pd.DataFrame([{"table": t, "type": s["kind"], "rows": s["rows"], "grain": " + ".join(s["grain"]),
               "columns": len(s["columns"]), "joins": ", ".join(sorted({v[0] for v in s["fks"].values()})) or "—"}
              for t, s in BI_INPUT["tables"].items()])
