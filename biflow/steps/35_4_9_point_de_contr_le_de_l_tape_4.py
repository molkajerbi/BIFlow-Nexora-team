def lineage_ok_for(t: str) -> bool:
    """Chaque ligne silver vient d'une ligne brute, ou d'un ajout validé par l'humain."""
    ids = SILVER[t]["_source_row_id"]
    return bool((ids.str.startswith("ajout:") | ids.isin(RAW._tables[t]["_source_row_id"])).all())


def expected_rows(t: str) -> int:
    """Lignes brutes - lignes supprimées + lignes ajoutées (toutes journalisées)."""
    if ROW_CHANGES.empty:
        return len(RAW._tables[t])
    ops = ROW_CHANGES.loc[ROW_CHANGES["table"] == t, "operation"]
    return len(RAW._tables[t]) - int(ops.str.startswith("supprimée").sum()) + int(ops.str.startswith("ajoutée").sum())


checks4 = checkpoint_raw_integrity()
chain_ok, chain_msg = AUDIT.verify()
lineage_ok = all(lineage_ok_for(t) for t in SILVER)
rows_explained = all(expected_rows(t) == len(SILVER[t]) for t in SILVER)
ok4 = bool(checks4["contenu_inchangé"].all()) and chain_ok and lineage_ok and rows_explained and STATUS != "blocked"

AUDIT.log("orchestrator", "checkpoint_step4",
          {"passed": ok4, "status": STATUS, "raw_unchanged": bool(checks4["contenu_inchangé"].all()),
           "lineage_ok": lineage_ok, "row_counts_explained": rows_explained, "audit_chain": chain_msg},
          level="INFO" if ok4 else "ERROR")
print(f"Données brutes inchangées         : {bool(checks4['contenu_inchangé'].all())}")
print(f"Lignage préservé                  : {lineage_ok}")
print(f"Nombres de lignes expliqués       : {rows_explained}")
print(f"Statut qualité                    : {STATUS}")
print(f"Journal d'audit                   : {chain_msg}")
print("ÉTAPE 4 VALIDÉE" if ok4 else "ÉTAPE 4 EN ÉCHEC")
pd.DataFrame({t: {"lignes_brutes": len(RAW._tables[t]), "lignes_silver": len(SILVER[t]),
                  "lignes_signalées": int(SILVER[t]["_dq_flags"].notna().sum())} for t in SILVER}).T
