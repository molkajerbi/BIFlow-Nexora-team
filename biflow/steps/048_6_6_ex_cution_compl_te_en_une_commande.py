t0 = time.perf_counter()
DATA_PREP_RESULT = run_data_preparation()
print(f"Final status: {DATA_PREP_RESULT['status']} · duration: {time.perf_counter() - t0:.0f} s"
      + (f" · error: {DATA_PREP_RESULT['error']}" if DATA_PREP_RESULT.get("error") else ""))
pd.DataFrame(DATA_PREP_RESULT["history"])[["node", "status", "seconds", "summary"]]
