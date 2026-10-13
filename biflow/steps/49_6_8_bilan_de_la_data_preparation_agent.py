r_ = DATA_PREP_RESULT
summary_rows = [
    ("Profiler Agent", f"{r_['profiler']['by_agent']}/{r_['profiler']['investigations']} investigations par l'agent · "
                       f"{r_['profiler']['interpreted_by_llm']}/{r_['profiler']['findings']} constats interprétés"),
    ("Quality Agent", f"{r_['quality']['decided_by_agent']}/{r_['quality']['candidates']} candidats décidés par l'agent · "
                      f"{r_['quality']['corrections_applied']} corrections appliquées · statut {r_['quality']['quality_status']}"),
    ("ETL Agent", f"{r_['etl']['built_by_agent']}/{r_['etl']['tables_expected']} tables choisies par l'agent · "
                  f"{r_['etl']['tables_built']} construites et testées"),
    ("Livrable", f"{len(r_['outputs']['tables'])} tables dans {Path(r_['outputs']['warehouse']).name}"),
    ("Contrôles", f"données brutes inchangées : {r_['outputs']['raw_unchanged']} · audit : {r_['outputs']['audit_chain']}"),
] if r_["status"] == "success" else [("Arrêt", f"{r_['status']} : {r_.get('error')}")]
print("DATA PREPARATION AGENT : " + ("SUCCÈS" if r_["status"] == "success" else r_["status"].upper()))
pd.DataFrame(summary_rows, columns=["composant", "résultat"])
