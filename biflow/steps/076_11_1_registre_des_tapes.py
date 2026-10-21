import contextlib
import io

STAGES = [
    {"node": "bridge_agent", "step": 7, "agent": "Bridge & knowledge base", "checkpoint": "ok7", "checks": "checks7",
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
    """Last executed version of each cell of the step, in registry order."""
    history = globals().get("In") or globals().get("_ih") or []
    out, missing = [], []
    for i, pattern in enumerate(stage["cells"], 1):
        src = next((h for h in reversed(history) if isinstance(h, str) and "STAGES = [" not in h
                    and re.search(pattern, h, re.M)), None)
        (out.append(src) if src else missing.append(f"{stage['step']}.{i}"))
    if missing:
        raise RuntimeError(f"cell(s) {', '.join(missing)} never executed in this session: run them once "
                           f"by hand (or \"Run all\") before using the orchestrator")
    return out


rows = []
for s in STAGES:
    try:
        n, note = len(stage_sources(s)), "ready"
    except RuntimeError as e:
        n, note = 0, str(e)
    rows.append({"step": s["step"], "node": s["node"], "agent": s["agent"], "cells found": f"{n}/{len(s['cells'])}",
                 "checkpoint": s["checkpoint"], "state": note})
pd.DataFrame(rows)
