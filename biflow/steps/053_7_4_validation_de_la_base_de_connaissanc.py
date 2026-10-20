UNITS = {"count", "currency", "percent", "days", "ratio", "score", "number"}
KINDS = {"value", "ratio", "rate", "growth", "top_share", "repeat_rate"}
AGGS = {"count", "count_distinct", "sum", "avg", "add"}
CONDITIONS = {"is_true", "in_values", "low_score", "negative", "above", "dq_flagged"}


def formula_slots(node) -> set:
    """Emplacements utilisés par une formule (parcours récursif)."""
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
        errors.append(f"type de KPI inconnu {f['kind']}")
    for node in [f.get("measure"), f.get("num"), f.get("den")]:
        stack = [node] if node else []
        while stack:
            n = stack.pop()
            if n["agg"] not in AGGS:
                errors.append(f"agrégat inconnu {n['agg']}")
            stack += n.get("terms", [])
            if n.get("where") and n["where"]["op"] not in CONDITIONS:
                errors.append(f"condition inconnue {n['where']['op']}")
            if n["agg"] in {"sum", "avg", "count_distinct"} and "slot" not in n:
                errors.append(f"{n['agg']} sans emplacement")
    for name, slot in card["slots"].items():
        if "·" not in slot["hint"]:
            errors.append(f"{name} : l'indice doit finir par des mots-clés (« · mot, mot »)")
        bad = set(slot["roles"]) - set(ROLES)
        if bad:
            errors.append(f"{name} : rôles inconnus {bad}")
    used, declared = formula_slots(f), set(card["slots"])
    if used - declared:
        errors.append(f"emplacements non déclarés {used - declared}")
    if declared - used:
        errors.append(f"emplacements inutilisés {declared - used}")
    if card["unit"] not in UNITS or card["direction"] not in {"up", "down", "neutral"}:
        errors.append("unité ou sens non autorisé")
    if f["kind"] == "rate" and card["unit"] != "percent":
        errors.append("un taux s'exprime en pourcentage")
    if not all(s in {"générique", *SECTORS} for s in card["sectors"]):
        errors.append("secteur inconnu")
    return errors


kb_errors = {c["id"]: e for c in KPI_KB if (e := validate_card(c))}
duplicate_ids = [i for i, n in pd.Series([c["id"] for c in KPI_KB]).value_counts().items() if n > 1]
assert not kb_errors and not duplicate_ids, f"Base de connaissances invalide : {kb_errors} {duplicate_ids}"
KB_SHA256 = sha256_text(canonical_json(KPI_KB))
AUDIT.log("bi_knowledge", "knowledge_base_validated", {"cards": len(KPI_KB), "sectors": list(SECTORS), "sha256": KB_SHA256})
print(f"Base valide : {len(KPI_KB)} fiches, 0 erreur · empreinte {KB_SHA256[:12]}…")
pd.DataFrame([{"id": c["id"], "KPI": c["name"], "secteur": c["sectors"][0], "type": c["formula"]["kind"], "unité": c["unit"],
               "sens": c["direction"], "emplacements": ", ".join(f"{k}:{'|'.join(v['roles'])}" for k, v in c["slots"].items()) or "—"}
              for c in KPI_KB]).groupby("secteur").head(4)
