BEFORE = {"catalogue": globals().get("CATALOG_SHA256"), "analysis": globals().get("ANALYSIS_SHA256"),
          "insights": [i["title"] for i in globals().get("INSIGHTS", [])]}
BI_RESULT = run_bi_insight()
REPRO = {"catalog": BEFORE["catalogue"] == CATALOG_SHA256, "analysis": BEFORE["analysis"] == ANALYSIS_SHA256,
         "insights": BEFORE["insights"] == [i["title"] for i in INSIGHTS]}
print("Reproducibility compared with the cell-by-cell run: "
      + " · ".join(f"{k} {'identical' if v else 'different'}" for k, v in REPRO.items()))
bi_history_table(BI_RESULT)
