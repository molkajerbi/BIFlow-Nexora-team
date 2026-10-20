INV_INDEX = {(r.table, r.column): i for i, r in enumerate(BI_INVENTORY.itertuples())}


def slot_candidates(card: dict, slot: str, fact: str, top: int = 3) -> list[dict]:
    """Colonnes compatibles avec un emplacement, depuis un fait de base : nom attendu d'abord, puis rôle préféré, puis proximité de sens."""
    spec, row = card["slots"][slot], SLOT_KEYS.index((card["id"], slot))
    measure_slot = set(spec["roles"]) <= MEASURE_ROLES
    out = []
    for t, link in reachable_tables(fact).items():
        if measure_slot and link != "base":
            continue                                       # une mesure se lit dans le fait de base (pas de double comptage)
        sub = BI_INVENTORY[BI_INVENTORY["table"] == t]
        for r in sub.itertuples():
            if not set(spec["roles"]) & set(r.roles):
                continue
            if "transaction_id" in spec["roles"] and t != fact:
                continue
            if spec.get("repeated") and BI_INPUT["tables"][t]["grain"] == [r.column]:
                continue                                   # la fiche exige plusieurs lignes par transaction (grain « article »)
            via = link
            if link == "base" and r.origin.startswith("hérité de ") and \
                    BI_INPUT["tables"].get("fact_" + r.origin[len("hérité de "):], {}).get("kind") == "fait":
                via = "hérité d'un fait parent"            # attribut recopié depuis la commande : il appartient au fait parent
            out.append({"table": t, "column": r.column, "via": via,
                        "score": round(float(SLOT_COLUMN_SIM[row, INV_INDEX[(t, r.column)]]), 3)})
    keys = hint_keywords(card, slot)
    for x in out:
        rank = keyword_rank(x["column"], keys)
        x["name_match"], x["kw_rank"] = rank is not None, rank if rank is not None else 99
        col_roles = BI_INVENTORY.loc[INV_INDEX[(x["table"], x["column"])], "roles"]
        x["role_rank"] = min(spec["roles"].index(r) for r in spec["roles"] if r in col_roles)
    if "entity_id" in spec["roles"]:                   # une entité suivie revient plusieurs fois (un identifiant par commande n'en est pas une)
        for x in out:
            r = BI_INVENTORY.loc[INV_INDEX[(x["table"], x["column"])]]
            ids = BI_INVENTORY[(BI_INVENTORY["table"] == x["table"]) & (BI_INVENTORY["semantic"] == "id")
                               & (BI_INVENTORY["column"] != x["column"])]["distinct"]
            one_to_one = any(abs(d - r["distinct"]) <= 0.02 * r["distinct"] for d in ids)   # même nombre de valeurs qu'un autre identifiant
            x["unique_per_row"] = (r["distinct"] >= 0.98 * r["rows"] or one_to_one) and len(out) > 1
    out.sort(key=lambda x: (x["kw_rank"], x["role_rank"], x.get("unique_per_row", False), -x["score"]))
    return [{k: x[k] for k in ("table", "column", "via", "score", "name_match")} for x in out[:top]]


OWN_LINKS = {"base", "dimension"}      # une colonne propre au fait ou à une de ses dimensions : le grain du KPI est le bon


def fact_hub_rank(fact: str) -> tuple:
    """Fait « pivot » d'abord (référencé par d'autres faits, ex. la commande), puis le plus volumineux."""
    incoming = sum(tg == fact for s in BI_INPUT["tables"].values() for tg, _ in s["fks"].values())
    return (incoming, BI_INPUT["tables"][fact]["rows"])


GENERIC_TOKENS = {"id", "key", "number", "date", "unique", "total", "value", "type", "name", "code", "of", "the"}


def hint_keywords(card: dict, slot: str) -> list[str]:
    """Mots-clés anglais d'un emplacement (après « · » dans l'indice), dans l'ordre de préférence, sans les mots trop génériques."""
    hint = card["slots"][slot]["hint"]
    if "·" not in hint:
        return []
    toks = [t for t in words(hint.split("·", 1)[1]).split() if t not in GENERIC_TOKENS]
    return list(dict.fromkeys(toks))


def keyword_rank(col: str, keys: list[str]) -> int | None:
    """Rang du premier mot-clé retrouvé dans le nom de la colonne (None si aucun)."""
    toks = [t for t in words(col).split() if t not in GENERIC_TOKENS]
    for i, k in enumerate(keys):
        if any(t == k or (len(k) >= 4 and len(t) >= 4 and (t.startswith(k) or k.startswith(t))) for t in toks):
            return i
    return None


def binding_confidence(card: dict, cands: dict) -> float:
    """Part des emplacements dont la colonne suggérée porte un nom attendu par la fiche (1 = liaison évidente)."""
    if not cands:
        return 1.0
    return round(float(np.mean([bool(c) and c[0]["name_match"] for c in cands.values()])), 2)


def assess_card(card: dict) -> dict:
    """Meilleur fait de base pour une fiche : tous les emplacements couverts, avec des colonnes propres au fait ou à ses
    dimensions plutôt qu'héritées d'un fait parent (un taux d'annulation se compte par commande, pas par article),
    puis la meilleure proximité de sens, puis le fait « pivot »."""
    options = []
    for fact in BI_FACTS:
        cands = {}
        for s in card["slots"]:
            c = slot_candidates(card, s, fact, top=6)
            own = [x for x in c if x["via"] in OWN_LINKS]
            cands[s] = (own or c)[:3]                      # colonne propre au fait (ou à ses dimensions) préférée
        missing = [s for s, c in cands.items() if not c]
        used = set()                                       # deux emplacements ne reçoivent jamais la même colonne
        for s in sorted(cands, key=lambda s: -(bool(cands[s]) and cands[s][0]["name_match"])):
            free = [x for x in cands[s] if (x["table"], x["column"]) not in used]
            if free:
                cands[s] = [free[0]] + [x for x in cands[s] if x is not free[0]]
                used.add((free[0]["table"], free[0]["column"]))
        own = float(np.mean([c[0]["via"] in OWN_LINKS for c in cands.values()])) if cands and not missing else 0.0
        fit = float(np.mean([c[0]["score"] for c in cands.values()])) if cands and not missing else (0.5 if not cands else 0.0)
        conf = binding_confidence(card, cands) if not missing else 0.0
        options.append({"fact": fact, "feasible": not missing, "missing": missing, "own_share": round(own, 2),
                        "fit": round(fit, 3), "confidence": conf, "candidates": cands,
                        "_rank": (not missing, own, conf, fit if card["slots"] else 0, fact_hub_rank(fact))})
    if not options:
        return {"fact": None, "feasible": False, "missing": list(card["slots"]), "own_share": 0.0, "fit": 0.0,
                "confidence": 0.0, "candidates": {}}
    best = max(options, key=lambda o: o["_rank"])
    return {k: v for k, v in best.items() if k != "_rank"}


def distinct_bindings_possible(card: dict, cands: dict) -> bool:
    """Vérifie qu'on peut donner une colonne différente à chaque emplacement (ex. frais de port ≠ prix)."""
    slots = list(cands)
    for combo in itertools.product(*[[c["column"] for c in cands[s]] for s in slots]):
        if len(set(combo)) == len(combo):
            return True
    return not slots


KPI_ASSESSMENT = {}
for card in KPI_KB:
    a = assess_card(card)
    if a["feasible"] and not distinct_bindings_possible(card, a["candidates"]):
        a = {**a, "feasible": False, "missing": ["colonnes distinctes"], "fit": 0.0}
    KPI_ASSESSMENT[card["id"]] = a
feasible_ids = [i for i, a in KPI_ASSESSMENT.items() if a["feasible"]]
print(f"{len(feasible_ids)}/{len(KPI_KB)} fiches calculables sur ce dataset "
      f"(génériques : {sum(i.startswith('GEN_') for i in feasible_ids)}/{sum(c['id'].startswith('GEN_') for c in KPI_KB)})")
pd.DataFrame([{"id": c["id"], "KPI": c["name"], "secteur": c["sectors"][0], "calculable": a["feasible"],
               "confiance": a["confidence"], "adéquation": a["fit"],
               "fait de base": a["fact"],
               "liaison suggérée": "; ".join(f"{s}→{v[0]['column']}" for s, v in a["candidates"].items() if v) or "—",
               "manque": ", ".join(a["missing"]) or "—"}
              for c in KPI_KB for a in [KPI_ASSESSMENT[c["id"]]]]).sort_values(["calculable", "confiance", "adéquation"], ascending=False).head(25)
