BEFORE_GLOBAL = {"catalogue": globals().get("CATALOG_SHA256"), "analyse": globals().get("ANALYSIS_SHA256"),
                 "insights": [i["titre"] for i in globals().get("INSIGHTS", [])]}
BIFLOW_RESULT = run_biflow()
DECISIONS = build_ledger()                              # le registre inclut maintenant la décision de l'orchestrateur global
XAI_INDEX = XAIIndex(LEDGER + METHODS)
REPRO_GLOBAL = {"catalogue": BEFORE_GLOBAL["catalogue"] == globals().get("CATALOG_SHA256"),
                "analyse": BEFORE_GLOBAL["analyse"] == globals().get("ANALYSIS_SHA256"),
                "insights": BEFORE_GLOBAL["insights"] == [i["titre"] for i in globals().get("INSIGHTS", [])]}
print("Reproductibilité par rapport aux exécutions précédentes : "
      + " · ".join(f"{k} {'identique' if v else 'différent'}" for k, v in REPRO_GLOBAL.items()))
biflow_history(BIFLOW_RESULT)
