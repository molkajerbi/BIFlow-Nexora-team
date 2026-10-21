UNITS = {"count", "currency", "percent", "days", "ratio", "score", "number"}
KINDS = {"value", "ratio", "rate", "growth", "top_share", "repeat_rate"}
AGGS = {"count", "count_distinct", "sum", "avg", "add"}
CONDITIONS = {"is_true", "in_values", "low_score", "negative", "above", "dq_flagged"}


def formula_slots(node) -> set:
    """Slots used by a formula (recursive traversal)."""
    found = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k in {"slot", "by", "date", "entity", "transaction"} and isinstance(v, str):
                found.add(v)
            else:
                found |= formula_slots(v)
    elif isinstance(node, list):
        for v in node:
            found |= formula_slots(v)
    return found


def validate_card(card: dict) -> list[str]:
    errors = []
    f = card["formula"]
    if f["kind"] not in KINDS:
        errors.append(f"unknown KPI type {f['kind']}")
    for node in [f.get("measure"), f.get("num"), f.get("den")]:
        stack = [node] if node else []
        while stack:
            n = stack.pop()
            if n["agg"] not in AGGS:
                errors.append(f"unknown aggregate {n['agg']}")
            stack += n.get("terms", [])
            if n.get("where") and n["where"]["op"] not in CONDITIONS:
                errors.append(f"unknown condition {n['where']['op']}")
            if n["agg"] in {"sum", "avg", "count_distinct"} and "slot" not in n:
                errors.append(f"{n['agg']} without a slot")
    for name, slot in card["slots"].items():
        if "·" not in slot["hint"]:
            errors.append(f'{name}: the hint must end with keywords ("· word, word")')
        bad = set(slot["roles"]) - set(ROLES)
        if bad:
            errors.append(f"{name}: unknown roles {bad}")
    used, declared = formula_slots(f), set(card["slots"])
    if used - declared:
        errors.append(f"undeclared slots {used - declared}")
    if declared - used:
        errors.append(f"unused slots {declared - used}")
    if card["unit"] not in UNITS or card["direction"] not in {"up", "down", "neutral"}:
        errors.append("unit or direction not allowed")
    if f["kind"] == "rate" and card["unit"] != "percent":
        errors.append("a rate is expressed as a percentage")
    if not all(s in {"generic", *SECTORS} for s in card["sectors"]):
        errors.append("unknown sector")
    return errors


kb_errors = {c["id"]: e for c in KPI_KB if (e := validate_card(c))}
duplicate_ids = [i for i, n in pd.Series([c["id"] for c in KPI_KB]).value_counts().items() if n > 1]
assert not kb_errors and not duplicate_ids, f"Invalid knowledge base: {kb_errors} {duplicate_ids}"
KB_SHA256 = sha256_text(canonical_json(KPI_KB))
AUDIT.log("bi_knowledge", "knowledge_base_validated", {"cards": len(KPI_KB), "sectors": list(SECTORS), "sha256": KB_SHA256})
print(f"Valid base: {len(KPI_KB)} cards, 0 errors · fingerprint {KB_SHA256[:12]}…")
pd.DataFrame([{"id": c["id"], "KPI": c["name"], "sector": c["sectors"][0], "type": c["formula"]["kind"], "unit": c["unit"],
               "direction": c["direction"], "slots": ", ".join(f"{k}:{'|'.join(v['roles'])}" for k, v in c["slots"].items()) or "—"}
              for c in KPI_KB]).groupby("sector").head(4)
