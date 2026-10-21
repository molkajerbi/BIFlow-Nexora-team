# Garde-fou : l'agent doit travailler sur des données NON nettoyées (sinon relancer depuis 4.1)
_, current = run_rules(SILVER, RULES)
assert not any("_dq_flags" in df for df in SILVER.values()) and current["violations"].tolist() == RULES_BEFORE["violations"].tolist(), \
    "SILVER has already been modified by a previous run: re-run step 4 from cell 4.1."

# Catalogue FERMÉ de corrections génériques : la valeur d'origine est toujours conservée dans le journal
CORRECTIONS = {
    "strip_whitespace":     ("FMT_", "removes the whitespace at the beginning and end of the value"),
    "normalize_missing":    ("NUL_", "replaces a disguised empty value (NA, null, -…) with a true missing value"),
    "harmonize_variants":   ("CAS_", "unifies the spelling variants of the same category (case, accents, spaces); "
                                     "rows that become identical are then removed by deduplication"),
    "drop_exact_duplicates": ("DUP_", "removes exactly copied rows"),
    "replace_impossible":   ("BUS_non_negative_", "replaces an impossible negative value with the median of similar rows"),
    "cap_outliers":         ("OUT_", "brings an extreme value back to the upper or lower limit of its column (original value logged)"),
    "impute_missing":       ("MIS_", "fills a missing value: median of similar rows (measure), category "
                                     'inferred from the other columns, or "Not specified" (estimated value marked)'),
}


def transform(correction: str, df: pd.DataFrame, table: str, column: str) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Applies a fix from the catalog. Returns (new table, changed cells, removed rows)."""
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
        raise ValueError(f"Fix outside the catalog: {correction}")
    changed = (old.notna() & (old != new).fillna(True)).astype(bool)
    df[column] = new
    return df, changed, none


def profiler_advice(table: str, column: str) -> tuple[list[str], list[str]]:
    """Recommendations of the Profiler Agent (step 3) that concern this table / column."""
    m = PROFILING_REPORT[(PROFILING_REPORT["table"] == table) & (PROFILING_REPORT["column"] == column)]
    return m["id"].tolist(), sorted(set(m["action"]))


def exact_duplicates_explain(t: str) -> bool:
    """The grain becomes unique again once the exact copies are removed: the removal is then lossless."""
    spec = DATA_CONTRACT[t]
    return not SILVER[t].drop_duplicates(subset=list(spec["columns"])).duplicated(subset=spec["grain"]).any()


def build_candidates() -> list[dict]:
    """Possible fixes, derived from the violated rules (the code only proposes what the catalog can do)."""
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
                      "profiler_actions": adv[1], "status": "to process", "simulation": None})
    return cands


def rules_touching(table: str) -> list[Rule]:
    """Rules whose result may change if this table changes: rules of the table, integrity towards it,
    and totals across tables (changing an amount may break "sale amount = sum of payments")."""
    parents = {f"REF_{r['child']}.{r['fk']}" for r in RELATIONSHIPS if r["parent"] == table}
    return [r for r in RULES if r.table == table or r.id in parents or r.id.startswith("BUS_total_")]


def simulate_correction(c: dict) -> dict:
    """Applies the fix on a COPY (sandbox) and measures its effect. SILVER is never modified here."""
    t, col = c["table"], c["column"]
    new_df, changed, removed = transform(c["correction"], SILVER[t], t, col)
    sandbox = {**SILVER, t: new_df}
    if c["correction"] == "drop_exact_duplicates":
        examples = SILVER[t].loc[removed, "_source_row_id"].head(3).tolist()
    else:
        examples = [{"before": repr(a), "after": repr(b)} for a, b in
                    zip(SILVER[t].loc[changed, col].head(3), new_df.loc[changed, col].head(3))]
    rules = rules_touching(t)
    _, before = run_rules(SILVER, rules)
    _, after = run_rules(sandbox, rules)
    delta = before[["rule", "violations"]].merge(after[["rule", "violations"]], on="rule", suffixes=("_before", "_after"))
    delta = delta[delta["violations_before"] != delta["violations_after"]]
    # Unifier des valeurs peut rendre des lignes identiques : ces copies exactes seront supprimées (sans perte)
    # par le dédoublonnage, appliqué APRÈS les corrections de valeurs. Ce n'est donc pas un effet négatif.
    revealed = delta["rule"].eq(f"DUP_{t}") & (delta["violations_after"] > delta["violations_before"])
    if c["correction"] == "impute_missing":            # une catégorie estimée peut RÉVÉLER une valeur extrême,
        revealed |= delta["rule"].str.startswith(f"OUT_{t}.") & (delta["violations_after"] > delta["violations_before"])
        # elle sera plafonnée ensuite (les extrêmes sont traités après les manques)
    elif c["correction"] in {"strip_whitespace", "normalize_missing"}:   # un texte fait d'espaces devient un vrai vide :
        revealed |= delta["rule"].eq(f"MIS_{t}.{col}") & (delta["violations_after"] > delta["violations_before"])
        # ce n'est pas un problème créé : il sera rempli ensuite (les manques sont traités après les formats)
    dup_revealed = int((delta.loc[revealed, "violations_after"] - delta.loc[revealed, "violations_before"]).sum())
    worse = delta[~revealed]
    return {"cells_changed": int(changed.sum()), "rows_removed": int(removed.sum()), "rows_added": 0,
            "estimated_values": c["correction"] in ESTIMATING,
            "duplicates_revealed": dup_revealed,
            "rows_removed_pct": round(100 * float(removed.mean()), 2) if len(removed) else 0.0,
            "impact": CORRECTIONS[c["correction"]][1], "information_loss": False, "examples": examples,
            "rules_changed": {r.rule: f"{r.violations_before} -> {r.violations_after}" for r in delta.itertuples()},
            "target_fixed": int(delta.loc[delta["rule"] == c["rule"], "violations_after"].sum()) == 0
                            and c["rule"] in set(delta["rule"]),
            "new_violations": bool((worse["violations_after"] > worse["violations_before"]).any())}


CANDIDATES = build_candidates()
candidate_rules = {c["rule"] for c in CANDIDATES}
AUTO_FLAGGED = RULES_BEFORE[(RULES_BEFORE["violations"] > 0) & ~RULES_BEFORE["rule"].isin(candidate_rules)][
    ["rule", "table", "severity", "violations"]]
AUDIT.log("quality_agent", "candidates_built",
          {"candidates": [{k: c[k] for k in ("id", "correction", "table", "column", "rule", "violations")} for c in CANDIDATES],
           "auto_flagged_rules": AUTO_FLAGGED["rule"].tolist()})
print(f"{len(CANDIDATES)} candidate fix(es) · {len(AUTO_FLAGGED)} rule(s) only flagged (no safe fix)")
pd.DataFrame(CANDIDATES, columns=["id", "correction", "table", "column", "rule", "violations", "profiler_actions"])
