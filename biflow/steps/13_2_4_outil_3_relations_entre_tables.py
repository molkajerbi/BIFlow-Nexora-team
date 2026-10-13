@audited(agent="profiler",
         description="Vérifie les relations déclarées (orphelins, couverture, cardinalité) et découvre les relations non déclarées par inclusion de valeurs.")
def discover_relationships(min_inclusion: float = 0.95, min_overlap: int = 10) -> ToolResult:
    # 1) Ensemble des valeurs distinctes de chaque colonne clé potentielle (id, zip, category)
    values, unique_cols = {}, set()
    for t, spec in DATA_CONTRACT.items():
        for c, sem in spec["columns"].items():
            if sem in {"id", "zip", "category", "integer"}:
                col = raw_column(t, c)
                values[(t, c)] = (sem, set(col.dropna().unique()))
                if col.notna().all() and col.is_unique:
                    unique_cols.add((t, c))

    rows = []
    # 2) Relations déclarées dans le contrat
    declared = {(r["child"], r["fk"], r["parent"], r["pk"]) for r in RELATIONSHIPS}
    for ch, fk, pa, pk in declared:
        child = raw_column(ch, fk)
        parent_vals = values[(pa, pk)][1]
        present = child.dropna()
        orphan = ~present.isin(parent_vals)
        per_parent = present.value_counts()
        rows.append({
            "relation": f"{ch}.{fk} → {pa}.{pk}", "origin": "déclarée",
            "child_rows": len(child), "null_fk": int(child.isna().sum()),
            "orphan_rows": int(orphan.sum()), "orphan_distinct": int(present[orphan].nunique()),
            "orphan_examples": present[orphan].unique()[:3].tolist(),
            "inclusion_pct": round(100 * (1 - present[orphan].nunique() / max(present.nunique(), 1)), 2),
            "parent_coverage_pct": round(100 * len(set(per_parent.index) & parent_vals) / max(len(parent_vals), 1), 2),
            "max_children_per_parent": int(per_parent.max()) if len(per_parent) else 0,
            "parent_key_unique": (pa, pk) in unique_cols,
            "status": "respectée" if orphan.sum() == 0 else "violée",
        })

    # 3) Découverte : colonne A incluse dans une colonne B unique (clé) d'une autre table, même type sémantique
    #    On ignore les "tables sœurs" : deux colonnes qui pointent déjà vers le même parent déclaré
    #    (ex. order_payments.order_id et order_reviews.order_id -> orders.order_id).
    parent_of = {(r["child"], r["fk"]): (r["parent"], r["pk"]) for r in RELATIONSHIPS}
    for (ct, cc), (csem, cvals) in values.items():
        for (pt, pc) in unique_cols:
            psem, pvals = values[(pt, pc)]
            siblings = (ct, cc) in parent_of and parent_of[(ct, cc)] == parent_of.get((pt, pc))
            if pt == ct or psem != csem or (ct, cc, pt, pc) in declared or not cvals or siblings:
                continue
            overlap = len(cvals & pvals)
            inclusion = overlap / len(cvals)
            if inclusion >= min_inclusion and overlap >= min_overlap:
                one_to_one = (ct, cc) in unique_cols and len(pvals) and overlap / len(pvals) >= min_inclusion
                rows.append({
                    "relation": f"{ct}.{cc} → {pt}.{pc}", "origin": "découverte",
                    "child_rows": None, "null_fk": None, "orphan_rows": None, "orphan_distinct": len(cvals) - overlap,
                    "orphan_examples": [], "inclusion_pct": round(100 * inclusion, 2),
                    "parent_coverage_pct": round(100 * overlap / len(pvals), 2),
                    "max_children_per_parent": 1 if (ct, cc) in unique_cols else None,
                    "parent_key_unique": True,
                    "status": "relation 1:1" if one_to_one else "candidate",
                })

    columns = ["relation", "origin", "child_rows", "null_fk", "orphan_rows", "orphan_distinct", "orphan_examples",
               "inclusion_pct", "parent_coverage_pct", "max_children_per_parent", "parent_key_unique", "status"]
    details = pd.DataFrame(rows, columns=columns).sort_values(["origin", "relation"]).reset_index(drop=True)
    for c in ["child_rows", "null_fk", "orphan_rows", "max_children_per_parent"]:
        details[c] = details[c].astype("Int64")
    d = details[details["origin"] == "déclarée"]
    summary = {
        "declared": len(d), "respected": int((d["status"] == "respectée").sum()),
        "violated": {r.relation: {"orphan_rows": int(r.orphan_rows), "orphan_distinct": int(r.orphan_distinct)}
                     for r in d.itertuples() if r.status == "violée"},
        "parent_key_not_unique": d.loc[~d["parent_key_unique"], "relation"].tolist(),
        "discovered": details.loc[details["origin"] == "découverte", ["relation", "status"]].to_dict(orient="records"),
    }
    return ToolResult(summary, details)


rel = discover_relationships()
print(json.dumps(rel.summary, indent=2, ensure_ascii=False, default=_json_default))
rel.details
