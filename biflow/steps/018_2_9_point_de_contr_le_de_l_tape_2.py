checks2 = checkpoint_raw_integrity()
chain_ok, chain_msg = AUDIT.verify()
tool_calls = sum(1 for e in AUDIT.events if e["action"].startswith("tool_called:"))
tool_errors = sum(1 for e in AUDIT.events if e["action"].startswith("tool_failed:"))
ok2 = bool(checks2["content_unchanged"].all()) and chain_ok and tool_errors == 0

AUDIT.log("orchestrator", "checkpoint_step2",
          {"passed": ok2, "raw_unchanged": bool(checks2["content_unchanged"].all()),
           "tool_calls": tool_calls, "tool_errors": tool_errors, "audit_chain": chain_msg},
          level="INFO" if ok2 else "ERROR")

print(f"Registered tools: {list(TOOL_REGISTRY)}")
print(f"Traced tool calls: {tool_calls} · errors: {tool_errors}")
print(f"Raw data unchanged: {bool(checks2['content_unchanged'].all())}")
print(f"Audit log: {chain_msg}")
print("STEP 2 PASSED" if ok2 else "STEP 2 FAILED")
pd.DataFrame([{"tool": k, "agent": v["agent"], "read_only": v["read_only"],
               "parameters": ", ".join(v["params"]), "description": v["description"]}
              for k, v in TOOL_REGISTRY.items()])
