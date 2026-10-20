t_start = next(e["ts"] for e in reversed(AUDIT.events)
               if e["action"] == "bi_insight_started" and e["details"].get("start_from") == "bridge_agent")
t_end = next(e["ts"] for e in AUDIT.events if e["action"] == "bi_insight_finished" and e["ts"] > t_start)
calls = [json.loads(line) for line in LLM_LOG.open(encoding="utf-8")]
earlier = {}
for c in calls:
    if c["ts"] < t_start:
        earlier.setdefault(c["prompt_sha256"], set()).add(c["response"])
rows = []
for c in calls:
    if t_start <= c["ts"] <= t_end:
        seen = earlier.get(c["prompt_sha256"])
        verdict = ("question nouvelle" if seen is None else
                   "même question, même réponse" if c["response"] in seen else "même question, réponse différente")
        rows.append({"agent": c["agent"], "verdict": verdict})
REPRO_DIAG = (pd.DataFrame(rows).value_counts().rename("appels").reset_index()
              if rows else pd.DataFrame(columns=["agent", "verdict", "appels"]))
AUDIT.log("orchestrator", "reproducibility_diagnosis", {"rows": REPRO_DIAG.to_dict(orient="records"), "hashes_equal": REPRO})
REPRO_DIAG.sort_values(["agent", "verdict"])
