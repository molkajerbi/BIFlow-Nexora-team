import contextlib
import io

STAGES = [
    {"node": "bridge_agent", "step": 7, "agent": "Pont & base de connaissances", "checkpoint": "ok7", "checks": "checks7",
     "cells": [r"^TECH_COLUMNS\b[^\n=]*=", r"^ROLES\b[^\n=]*=", r"^def M\(", r"^UNITS\b[^\n=]*=", r"^class SemanticSearch\b",
               r"^INV_INDEX\b[^\n=]*=", r"^MIN_SECTOR_KPIS\b[^\n=]*=", r"^def kpi_relevance\(", r"^checks7\b[^\n=]*="]},
    {"node": "kpi_agent", "step": 8, "agent": "KPI Agent", "checkpoint": "ok8", "checks": "checks8",
     "cells": [r"^BI_ENGINE\b[^\n=]*=", r"^TRUE_WORDS\b[^\n=]*=", r"^def check_bounds\(", r"^MAX_PROPOSALS\b[^\n=]*=",
               r"^def fmt_value\(", r"^checks8\b[^\n=]*="]},
    {"node": "analyst_agent", "step": 9, "agent": "BI Analyst Agent", "checkpoint": "ok9", "checks": "checks9",
     "cells": [r"^WINDOW\b[^\n=]*=", r"^FACTS\b[^\n=]*=", r"^def dimensions\(", r"^MAX_INVESTIGATIONS\b[^\n=]*=",
               r"^MAX_LLM_INSIGHTS\b[^\n=]*=", r"^ANALYSIS\b[^\n=]*="]},
    {"node": "dashboard_agent", "step": 10, "agent": "Dashboard Generator Agent", "checkpoint": "ok10", "checks": "checks10",
     "cells": [r"^def reliable_series\(", r"^LAYOUT_EXAMPLES\b[^\n=]*=", r"^DASHBOARD_CSS\b[^\n=]*=",
               r"^def segment_payload\(", r"^checks10\b[^\n=]*="]},
]
STAGE_NAMES = [s["node"] for s in STAGES]
STAGE_ALIASES = {**{s["node"]: s["node"] for s in STAGES}, **{str(s["step"]): s["node"] for s in STAGES},
                 **{s["step"]: s["node"] for s in STAGES}, "bridge": "bridge_agent", "kpi": "kpi_agent",
                 "analyst": "analyst_agent", "dashboard": "dashboard_agent"}


def stage_sources(stage: dict) -> list[str]:
    """Dernière version exécutée de chaque cellule de l'étape, dans l'ordre du registre."""
    history = globals().get("In") or globals().get("_ih") or []
    out, missing = [], []
    for i, pattern in enumerate(stage["cells"], 1):
        src = next((h for h in reversed(history) if isinstance(h, str) and "STAGES = [" not in h
                    and re.search(pattern, h, re.M)), None)
        (out.append(src) if src else missing.append(f"{stage['step']}.{i}"))
    if missing:
        raise RuntimeError(f"cellule(s) {', '.join(missing)} jamais exécutée(s) dans cette session : exécutez-les une fois "
                           f"à la main (ou « Run all ») avant d'utiliser l'orchestrateur")
    return out


rows = []
for s in STAGES:
    try:
        n, note = len(stage_sources(s)), "prête"
    except RuntimeError as e:
        n, note = 0, str(e)
    rows.append({"étape": s["step"], "nœud": s["node"], "agent": s["agent"], "cellules trouvées": f"{n}/{len(s['cells'])}",
                 "point de contrôle": s["checkpoint"], "état": note})
pd.DataFrame(rows)
