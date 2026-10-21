assert STATUS != "blocked", "Blocking quality: the ETL is forbidden until step 4 is unblocked."
assert all("_dq_flags" in df for df in SILVER.values()), "Run the complete step 4 first (4.1 → 4.9)."

try:
    import duckdb
    SQL_ENGINE = "duckdb"
except ImportError:                       # secours : SQLite est inclus dans Python
    import sqlite3
    SQL_ENGINE = "sqlite"
try:
    import pyarrow as pa
except ImportError:
    pa = None


class Warehouse:
    """Small SQL warehouse: loads DataFrames, runs SQL templates, reads the results back."""

    def __init__(self, path: Path):
        self.path = path
        self.con = duckdb.connect(str(path)) if SQL_ENGINE == "duckdb" else sqlite3.connect(str(path))

    @staticmethod
    def _portable(df: pd.DataFrame) -> pd.DataFrame:
        """Neutral types: missing values become NULL (never NaN, which would distort SUMs)."""
        out = pd.DataFrame(index=df.index)
        for c in df.columns:
            s = df[c]
            if pd.api.types.is_datetime64_any_dtype(s) and SQL_ENGINE == "sqlite":
                out[c] = s.dt.strftime(DATETIME_FORMAT).astype(object).where(s.notna(), None)
            elif pd.api.types.is_datetime64_any_dtype(s):
                out[c] = s
            else:
                out[c] = s.astype(object).where(s.notna(), None)
        return out

    def load(self, name: str, df: pd.DataFrame) -> None:
        if SQL_ENGINE == "duckdb":
            frame = pa.Table.from_pandas(df, preserve_index=False) if pa is not None else self._portable(df)
            self.con.register("_incoming", frame)
            self.con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM _incoming")
            self.con.unregister("_incoming")
        else:
            self._portable(df).to_sql(name, self.con, if_exists="replace", index=False)

    def create(self, name: str, sql: str) -> None:
        if SQL_ENGINE == "duckdb":
            self.con.execute(f"CREATE OR REPLACE TABLE {name} AS {sql}")
        else:
            self.con.execute(f"DROP TABLE IF EXISTS {name}")
            self.con.execute(f"CREATE TABLE {name} AS {sql}")
            self.con.commit()

    def query(self, sql: str) -> pd.DataFrame:
        return self.con.execute(sql).df() if SQL_ENGINE == "duckdb" else pd.read_sql_query(sql, self.con)


etl_dir = RUN_DIR / "warehouse"
etl_dir.mkdir(exist_ok=True)
WH = Warehouse(etl_dir / f"biflow_star.{'duckdb' if SQL_ENGINE == 'duckdb' else 'sqlite'}")
AUDIT.log("etl_agent", "warehouse_opened", {"engine": SQL_ENGINE, "path": WH.path, "quality_status": STATUS})
print(f"SQL engine: {SQL_ENGINE} · warehouse: {WH.path.name} · input quality status: {STATUS}")
