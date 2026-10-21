r_ = DATA_PREP_RESULT
summary_rows = [
    ("Profiler Agent", f"{r_['profiler']['by_agent']}/{r_['profiler']['investigations']} investigations by the agent · "
                       f"{r_['profiler']['interpreted_by_llm']}/{r_['profiler']['findings']} findings interpreted"),
    ("Quality Agent", f"{r_['quality']['decided_by_agent']}/{r_['quality']['candidates']} candidates decided by the agent · "
                      f"{r_['quality']['corrections_applied']} fixes applied · status {r_['quality']['quality_status']}"),
    ("ETL Agent", f"{r_['etl']['built_by_agent']}/{r_['etl']['tables_expected']} tables chosen by the agent · "
                  f"{r_['etl']['tables_built']} built and tested"),
    ("Deliverable", f"{len(r_['outputs']['tables'])} tables in {Path(r_['outputs']['warehouse']).name}"),
    ("Checks", f"raw data unchanged: {r_['outputs']['raw_unchanged']} · audit: {r_['outputs']['audit_chain']}"),
] if r_["status"] == "success" else [("Stop", f"{r_['status']}: {r_.get('error')}")]
print("DATA PREPARATION AGENT: " + ("SUCCESS" if r_["status"] == "success" else r_["status"].upper()))
pd.DataFrame(summary_rows, columns=["component", "result"])
