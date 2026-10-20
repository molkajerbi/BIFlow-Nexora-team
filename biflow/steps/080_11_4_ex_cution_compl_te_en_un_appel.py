BEFORE = {"catalogue": globals().get("CATALOG_SHA256"), "analyse": globals().get("ANALYSIS_SHA256"),
          "insights": [i["titre"] for i in globals().get("INSIGHTS", [])]}
BI_RESULT = run_bi_insight()
REPRO = {"catalogue": BEFORE["catalogue"] == CATALOG_SHA256, "analyse": BEFORE["analyse"] == ANALYSIS_SHA256,
         "insights": BEFORE["insights"] == [i["titre"] for i in INSIGHTS]}
print("Reproductibilité par rapport à l'exécution cellule par cellule : "
      + " · ".join(f"{k} {'identique' if v else 'différent'}" for k, v in REPRO.items()))
bi_history_table(BI_RESULT)
