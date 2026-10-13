# Garde-fou : l'agent doit travailler sur des données NON nettoyées (sinon relancer depuis 4.1)
_, current = run_rules(SILVER, RULES)
assert not any("_dq_flags" in df for df in SILVER.values()) and current["violations"].tolist() == RULES_BEFORE["violations"].tolist(), \
    "SILVER a déjà été modifié par une exécution précédente : relancez l'étape 4 depuis la cellule 4.1."

# Catalogue FERMÉ de corrections génériques : la valeur d'origine est toujours conservée dans le journal
CORRECTIONS = {
    "strip_whitespace":     ("FMT_", "retire les espaces en début et fin de valeur"),
    "normalize_missing":    ("NUL_", "remplace une valeur vide déguisée (NA, null, -…) par une vraie valeur manquante"),
    "harmonize_variants":   ("CAS_", "unifie les variantes d'écriture d'une même catégorie (casse, accents, espaces) ; "
                                     "les lignes devenues identiques sont ensuite supprimées par le dédoublonnage"),
    "drop_exact_duplicates": ("DUP_", "supprime les lignes copiées à l'identique"),
    "replace_impossible":   ("BUS_non_negative_", "remplace une valeur négative impossible par la médiane des lignes semblables"),
    "cap_outliers":         ("OUT_", "ramène une valeur extrême à la limite haute ou basse de sa colonne (valeur d'origine journalisée)"),
    "impute_missing":       ("MIS_", "remplit une valeur manquante : médiane des lignes semblables (mesure), catégorie "
                                     "déduite des autres colonnes, ou « Non renseigné » (valeur estimée marquée)"),
}


def transform(correction: str, df: pd.DataFrame, table: str, column: str) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Applique une correction du catalogue. Renvoie (nouvelle table, cellules modifiées, lignes supprimées)."""
    df = df.copy()
    none = pd.Series(False, index=df.index)
    if correction == "drop_exact_duplicates":
        removed = df.duplicated(subset=list(DATA_CONTRACT[table]["columns"]), keep="first")
        return df.loc[~removed], none, removed
    if correction in ESTIMATING:                        # valeurs manquantes, impossibles, extrêmes (4.1 bis)
        new, changed = treat_values(correction, df, table, column)
        df[column] = new
        return df, changed, none
    old = df[column]
    if correction == "strip_whitespace":
        new = old.str.strip().replace("", pd.NA)
    elif correction == "normalize_missing":
        new = old.mask(old.str.strip().str.lower().isin(NULL_TOKENS).fillna(False))
    elif correction == "harmonize_variants":
        mapping = variant_map(old)
        stripped = old.str.strip()
        new = old.where(~stripped.isin(set(mapping)).fillna(False), stripped.map(mapping)).astype("string")
    else:
        raise ValueError(f"Correction hors catalogue : {correction}")
    changed = (old.notna() & (old != new).fillna(True)).astype(bool)
    df[column] = new
    return df, changed, none


def profiler_advice(table: str, column: str) -> tuple[list[str], list[str]]:
    """Recommandations du Profiler Agent (étape 3) qui concernent cette table / colonne."""
    m = PROFILING_REPORT[(PROFILING_REPORT["table"] == table) & (PROFILING_REPORT["colonne"] == column)]
    return m["id"].tolist(), sorted(set(m["action"]))


def exact_duplicates_explain(t: str) -> bool:
    """Le grain redevient unique si l'on retire les copies exactes : la suppression est alors sans perte."""
    spec = DATA_CONTRACT[t]
    return not SILVER[t].drop_duplicates(subset=list(spec["columns"])).duplicated(subset=spec["grain"]).any()


def build_candidates() -> list[dict]:
    """Corrections possibles, déduites des règles en violation (le code ne propose que ce que le catalogue sait faire)."""
    cands = []
    for r in RULES_BEFORE.query("violations > 0").itertuples():
        correction = next((k for k, (p, _) in CORRECTIONS.items() if r.rule.startswith(p)), None)
        if r.rule.startswith("UNQ_") and exact_duplicates_explain(r.table):
            correction = "drop_exact_duplicates"          # grain cassé uniquement par des copies exactes
        if correction is None:
            continue
        table, column = (r.table, "*") if correction == "drop_exact_duplicates" \
            else r.rule[len(CORRECTIONS[correction][0]):].split(".", 1)
        adv = profiler_advice(table, column)
        cands.append({"id": f"K{len(cands) + 1}", "correction": correction, "table": table, "column": column,
                      "rule": r.rule, "violations": r.violations, "profiler_findings": adv[0],
                      "profiler_actions": adv[1], "status": "à traiter", "simulation": None})
    return cands


def rules_touching(table: str) -> list[Rule]:
    """Règles dont le résultat peut changer si cette table change : règles de la table, intégrité vers elle,
    et totaux entre tables (modifier un montant peut casser « montant de la vente = somme des paiements »)."""
    parents = {f"REF_{r['child']}.{r['fk']}" for r in RELATIONSHIPS if r["parent"] == table}
    return [r for r in RULES if r.table == table or r.id in parents or r.id.startswith("BUS_total_")]


def simulate_correction(c: dict) -> dict:
    """Applique la correction sur une COPIE (bac à sable) et mesure son effet. SILVER n'est jamais modifié ici."""
    t, col = c["table"], c["column"]
    new_df, changed, removed = transform(c["correction"], SILVER[t], t, col)
    sandbox = {**SILVER, t: new_df}
    if c["correction"] == "drop_exact_duplicates":
        examples = SILVER[t].loc[removed, "_source_row_id"].head(3).tolist()
    else:
        examples = [{"avant": repr(a), "après": repr(b)} for a, b in
                    zip(SILVER[t].loc[changed, col].head(3), new_df.loc[changed, col].head(3))]
    rules = rules_touching(t)
    _, before = run_rules(SILVER, rules)
    _, after = run_rules(sandbox, rules)
    delta = before[["rule", "violations"]].merge(after[["rule", "violations"]], on="rule", suffixes=("_avant", "_après"))
    delta = delta[delta["violations_avant"] != delta["violations_après"]]
    # Unifier des valeurs peut rendre des lignes identiques : ces copies exactes seront supprimées (sans perte)
    # par le dédoublonnage, appliqué APRÈS les corrections de valeurs. Ce n'est donc pas un effet négatif.
    revealed = delta["rule"].eq(f"DUP_{t}") & (delta["violations_après"] > delta["violations_avant"])
    if c["correction"] == "impute_missing":            # une catégorie estimée peut RÉVÉLER une valeur extrême,
        revealed |= delta["rule"].str.startswith(f"OUT_{t}.") & (delta["violations_après"] > delta["violations_avant"])
        # elle sera plafonnée ensuite (les extrêmes sont traités après les manques)
    elif c["correction"] in {"strip_whitespace", "normalize_missing"}:   # un texte fait d'espaces devient un vrai vide :
        revealed |= delta["rule"].eq(f"MIS_{t}.{col}") & (delta["violations_après"] > delta["violations_avant"])
        # ce n'est pas un problème créé : il sera rempli ensuite (les manques sont traités après les formats)
    dup_revealed = int((delta.loc[revealed, "violations_après"] - delta.loc[revealed, "violations_avant"]).sum())
    worse = delta[~revealed]
    return {"cells_changed": int(changed.sum()), "rows_removed": int(removed.sum()), "rows_added": 0,
            "estimated_values": c["correction"] in ESTIMATING,
            "duplicates_revealed": dup_revealed,
            "rows_removed_pct": round(100 * float(removed.mean()), 2) if len(removed) else 0.0,
            "impact": CORRECTIONS[c["correction"]][1], "information_loss": False, "examples": examples,
            "rules_changed": {r.rule: f"{r.violations_avant} -> {r.violations_après}" for r in delta.itertuples()},
            "target_fixed": int(delta.loc[delta["rule"] == c["rule"], "violations_après"].sum()) == 0
                            and c["rule"] in set(delta["rule"]),
            "new_violations": bool((worse["violations_après"] > worse["violations_avant"]).any())}


CANDIDATES = build_candidates()
candidate_rules = {c["rule"] for c in CANDIDATES}
AUTO_FLAGGED = RULES_BEFORE[(RULES_BEFORE["violations"] > 0) & ~RULES_BEFORE["rule"].isin(candidate_rules)][
    ["rule", "table", "severity", "violations"]]
AUDIT.log("quality_agent", "candidates_built",
          {"candidates": [{k: c[k] for k in ("id", "correction", "table", "column", "rule", "violations")} for c in CANDIDATES],
           "auto_flagged_rules": AUTO_FLAGGED["rule"].tolist()})
print(f"{len(CANDIDATES)} correction(s) candidate(s) · {len(AUTO_FLAGGED)} règle(s) seulement signalées (aucune correction sûre)")
pd.DataFrame(CANDIDATES, columns=["id", "correction", "table", "column", "rule", "violations", "profiler_actions"])
