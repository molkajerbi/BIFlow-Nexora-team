demo = run_data_preparation(None, autonomy="manual")      # mode manuel sans décision humaine
print(demo["status"], "→", [h["node"] for h in demo["history"]])
demo["history"][-1]["summary"]
