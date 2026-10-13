CHANGE_LOG, ROW_LOG = [], []


def frame_hash(df: pd.DataFrame, cols: list[str]) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(df[cols], index=True).values.tobytes()).hexdigest()


def apply_correction(cid: str, correction: str, table: str, column: str) -> dict:
    """Applique UNE correction approuvée, journalise chaque cellule / ligne touchée et vérifie l'absence d'effet de bord."""
    df = SILVER[table]
    rows_before = len(df)
    new_df, changed, removed = transform(correction, df, table, column)
    if correction == "drop_exact_duplicates":
        ROW_LOG.append(df.loc[removed, ["_source_row_id"]].assign(correction=cid, table=table,
                                                                  operation="supprimée (doublon exact)"))
        assert not new_df.duplicated(subset=list(DATA_CONTRACT[table]["columns"])).any(), "il reste des doublons"
        effect = int(removed.sum())
    else:
        CHANGE_LOG.append(pd.DataFrame({"correction": cid, "table": table, "column": column,
                                        "_source_row_id": df.loc[changed, "_source_row_id"],
                                        "before": df.loc[changed, column], "after": new_df.loc[changed, column]}))
        untouched = [c for c in df.columns if c != column]
        assert frame_hash(new_df, untouched) == frame_hash(df, untouched), "effet de bord : une autre colonne a changé"
        effect = int(changed.sum())
    SILVER[table] = new_df
    ids = SILVER[table]["_source_row_id"]
    assert ids.is_unique and ids.notna().all(), "lignage cassé"
    result = {"id": cid, "correction": correction, "table": table, "column": column,
              "rows_before": rows_before, "rows_after": len(SILVER[table]), "effect": effect}
    AUDIT.log("quality_agent", "correction_applied", result)
    return result


def plan_in_order():
    """Corrections de valeurs d'abord, dédoublonnage en dernier (il retire aussi les copies révélées par l'harmonisation)."""
    return sorted(CLEANING_PLAN.itertuples(), key=lambda p: (p.correction == "drop_exact_duplicates", p.id))


EXECUTION = pd.DataFrame([apply_correction(p.id, p.correction, p.table, p.colonne)
                          for p in plan_in_order() if p.id in APPROVED],
                         columns=["id", "correction", "table", "column", "rows_before", "rows_after", "effect"])
CHANGES = pd.concat(CHANGE_LOG, ignore_index=True) if CHANGE_LOG else pd.DataFrame()
ROW_CHANGES = pd.concat(ROW_LOG, ignore_index=True) if ROW_LOG else pd.DataFrame()
print(f"{len(EXECUTION)} correction(s) appliquée(s) · {len(CHANGES)} cellule(s) modifiée(s) · "
      f"{len(ROW_CHANGES)} ligne(s) supprimée(s)")
EXECUTION
