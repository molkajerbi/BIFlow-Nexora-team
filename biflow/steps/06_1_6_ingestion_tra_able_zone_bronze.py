def file_sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


class ContractViolation(Exception):
    """Erreur bloquante : les données ne respectent pas le contrat."""


class RawStore:
    """Zone 'bronze' : données brutes immuables. Toute lecture renvoie une copie."""

    def __init__(self):
        self._tables: dict[str, pd.DataFrame] = {}
        self.manifest: dict[str, dict] = {}

    def add(self, name: str, df: pd.DataFrame, meta: dict) -> None:
        if name in self._tables:
            raise ValueError(f"La table '{name}' est déjà chargée (les données brutes sont immuables).")
        self._tables[name] = df
        self.manifest[name] = meta

    def get(self, name: str) -> pd.DataFrame:
        return self._tables[name].copy(deep=True)

    @property
    def names(self) -> list[str]:
        return list(self._tables)

    def fingerprint(self, name: str) -> str:
        """Hash du contenu en mémoire : permet de prouver plus tard qu'il n'a pas changé."""
        return hashlib.sha256(
            pd.util.hash_pandas_object(self._tables[name], index=True).values.tobytes()
        ).hexdigest()


def ingest_table(name: str, spec: dict, data_dir: Path, audit: AuditTrail) -> tuple[pd.DataFrame, dict]:
    path = data_dir / spec["file"]
    if not path.exists():
        raise ContractViolation(f"{name} : fichier introuvable {path}")

    t0 = time.perf_counter()
    df = read_table(path, spec)                    # même lecteur que l'inférence : tout en texte
    elapsed = time.perf_counter() - t0

    expected, found = set(spec["columns"]), set(df.columns)
    missing, unexpected = sorted(expected - found), sorted(found - expected)
    if missing:
        audit.log("ingestion", "contract_violation", {"table": name, "missing_columns": missing}, level="ERROR")
        raise ContractViolation(f"{name} : colonnes obligatoires absentes {missing}")
    if unexpected:
        audit.log("ingestion", "unexpected_columns", {"table": name, "columns": unexpected}, level="WARNING")

    df.insert(0, "_source_row_id", pd.array([f"{name}:{i}" for i in range(len(df))], dtype="string"))

    meta = {
        "file": spec["file"],
        "sha256": file_sha256(path),
        "size_mb": round(path.stat().st_size / 1e6, 2),
        "rows": len(df),
        "columns": len(df.columns) - 1,
        "unexpected_columns": unexpected,
        "read_seconds": round(elapsed, 2),
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1e6, 1),
    }
    audit.log("ingestion", "table_ingested", {"table": name, **meta})
    return df, meta


RAW = RawStore()
for table_name, table_spec in DATA_CONTRACT.items():
    df_raw, meta = ingest_table(table_name, table_spec, CONFIG.data_dir, AUDIT)
    RAW.add(table_name, df_raw, meta)

RAW_FINGERPRINTS = {name: RAW.fingerprint(name) for name in RAW.names}

ingestion_report = (pd.DataFrame(RAW.manifest).T
                    .assign(sha256=lambda d: d["sha256"].str[:16] + "…")
                    .drop(columns=["file"]))
print(f"{len(RAW.names)} tables chargées · {int(ingestion_report['rows'].sum()):,} lignes au total".replace(",", " "))
ingestion_report
