BEFORE_GLOBAL = {"catalog": globals().get("CATALOG_SHA256"), "analysis": globals().get("ANALYSIS_SHA256"),
                 "insights": [i["title"] for i in globals().get("INSIGHTS", [])]}
BIFLOW_RESULT = run_biflow()
DECISIONS = build_ledger()                              # le registre inclut maintenant la décision de l'orchestrateur global
XAI_INDEX = XAIIndex(LEDGER + METHODS)
REPRO_GLOBAL = {"catalog": BEFORE_GLOBAL["catalog"] == globals().get("CATALOG_SHA256"),
                "analysis": BEFORE_GLOBAL["analysis"] == globals().get("ANALYSIS_SHA256"),
                "insights": BEFORE_GLOBAL["insights"] == [i["title"] for i in globals().get("INSIGHTS", [])]}
print("Reproducibility compared with the previous runs: "
      + " · ".join(f"{k} {'identical' if v else 'different'}" for k, v in REPRO_GLOBAL.items()))
biflow_history(BIFLOW_RESULT)
