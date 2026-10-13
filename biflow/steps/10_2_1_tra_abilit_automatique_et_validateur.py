import functools
import inspect


@dataclass
class ToolResult:
    """Résultat standard d'un outil : un résumé compact (pour le LLM et l'audit) + un détail tabulaire."""
    summary: dict
    details: pd.DataFrame | None = None


TOOL_REGISTRY: dict[str, dict] = {}   # catalogue des outils disponibles pour les agents
TOOL_RESULTS: dict[str, ToolResult] = {}   # derniers résultats, clé "outil:table"


def audited(agent: str, description: str, read_only: bool = True):
    """Enregistre l'outil dans le catalogue et trace automatiquement chaque appel dans l'audit."""
    def decorator(fn):
        signature = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            params = dict(bound.arguments)
            t0 = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                AUDIT.log(agent, f"tool_failed:{fn.__name__}",
                          {"params": params, "error": f"{type(exc).__name__}: {exc}"}, level="ERROR")
                raise
            seconds = round(time.perf_counter() - t0, 2)
            AUDIT.log(agent, f"tool_called:{fn.__name__}",
                      {"params": params, "seconds": seconds, "summary": result.summary})
            TOOL_RESULTS[f"{fn.__name__}:{params.get('table', 'all')}"] = result
            return result

        TOOL_REGISTRY[fn.__name__] = {"agent": agent, "description": description,
                                      "read_only": read_only, "params": list(signature.parameters), "fn": wrapper}
        return wrapper
    return decorator


# Validateurs par type sémantique : renvoient True si une valeur (non manquante) est conforme
def _to_float(s: pd.Series) -> pd.Series:
    """Texte -> nombre. Seules les valeurs qui ONT la forme d'un nombre sont converties (le reste devient NaN).
    Les écritures « 1 234,5 », « 1,234.5 », « 12 € » ou « 15 % » sont gérées grâce au contrat."""
    s = clean_number_text(s.astype("string"), NUMBER_FORMATS.get(s.name))
    ok = s.str.fullmatch(NUMBER_PATTERN, na=False).to_numpy(dtype=bool)
    out = np.full(len(s), np.nan)
    out[ok] = [float(v) for v in s[ok]]
    return pd.Series(out, index=s.index, dtype="float64")


def _valid_numeric(s):
    x = _to_float(s)
    return pd.Series(np.isfinite(x), index=s.index)


def _valid_integer(s):
    x = _to_float(s)
    return pd.Series(np.isfinite(x) & (np.floor(x) == x), index=s.index)


def dt_format(table: str, column: str) -> str:
    """Format de date de la colonne (inféré en mode auto), sinon le format par défaut du dataset."""
    return DATETIME_FORMATS.get(f"{table}.{column}", DATETIME_FORMAT)


def _valid_datetime(s, fmt: str | None = None):
    return pd.to_datetime(s, format=fmt or DATETIME_FORMAT, errors="coerce").notna()


def raw_column(table: str, column: str) -> pd.Series:
    """Copie d'une seule colonne brute (évite de copier toute la table, ex. geolocation = 1 M lignes)."""
    return RAW._tables[table][column].copy()


SEMANTIC_VALIDATORS = {
    "id":       lambda s: s.str.fullmatch(ID_PATTERN, na=False).astype(bool),       # identifiant non vide, sans espace
    "zip":      lambda s: s.str.fullmatch(ZIP_PATTERN, na=False).astype(bool),
    "datetime": _valid_datetime,
    "numeric":  _valid_numeric,
    "integer":  _valid_integer,
    "geo":      _valid_numeric,
    "category": lambda s: (s.str.len().gt(0) & s.eq(s.str.strip())).fillna(False).astype(bool),
    "text":     lambda s: pd.Series(True, index=s.index),
}

print(f"{len(SEMANTIC_VALIDATORS)} validateurs sémantiques prêts")
