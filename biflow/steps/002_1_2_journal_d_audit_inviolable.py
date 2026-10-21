def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _json_default(obj: Any) -> Any:
    """Makes numpy / pandas / Path types serializable."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (set, tuple)):
        return list(obj)
    if obj is pd.NA or obj is pd.NaT:
        return None
    return str(obj)


def canonical_json(obj: Any) -> str:
    """Deterministic JSON (sorted keys): same content => same hash."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=_json_default)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AuditTrail:
    """Append-only audit log, chained by SHA-256 hashes."""

    GENESIS = "0" * 64
    LEVELS = {"INFO", "WARNING", "ERROR", "DECISION"}

    def __init__(self, run_id: str, path: Path):
        self.run_id = run_id
        self.path = path
        self.events: list[dict] = []

    def log(self, agent: str, action: str, details: dict | None = None, level: str = "INFO") -> dict:
        if level not in self.LEVELS:
            raise ValueError(f"Unknown level: {level}")
        event = {
            "seq": len(self.events) + 1,
            "ts": utc_now(),
            "run_id": self.run_id,
            "agent": agent,
            "action": action,
            "level": level,
            "details": json.loads(canonical_json(details or {})),
            "prev_hash": self.events[-1]["hash"] if self.events else self.GENESIS,
        }
        event["hash"] = sha256_text(canonical_json(event))
        self.events.append(event)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(canonical_json(event) + "\n")
        return event

    def verify(self) -> tuple[bool, str]:
        """Recomputes the whole chain and locates the first break, if any."""
        prev = self.GENESIS
        for e in self.events:
            body = {k: v for k, v in e.items() if k != "hash"}
            if e["prev_hash"] != prev:
                return False, f"chain broken at event {e['seq']} (wrong prev_hash)"
            if sha256_text(canonical_json(body)) != e["hash"]:
                return False, f"event {e['seq']} modified afterwards"
            prev = e["hash"]
        return True, f"{len(self.events)} events, chain intact"

    def to_frame(self) -> pd.DataFrame:
        df = pd.DataFrame(self.events)
        if df.empty:
            return df
        df["details"] = df["details"].map(lambda d: canonical_json(d)[:120])
        df["hash"] = df["hash"].str[:12] + "…"
        return df[["seq", "ts", "agent", "level", "action", "details", "hash"]]


AUDIT = AuditTrail(RUN_ID, RUN_DIR / "audit_log.jsonl")
AUDIT.log("orchestrator", "run_started", {
    "config": {k: str(v) for k, v in CONFIG.__dict__.items()},
    "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
})
print(AUDIT.verify())
