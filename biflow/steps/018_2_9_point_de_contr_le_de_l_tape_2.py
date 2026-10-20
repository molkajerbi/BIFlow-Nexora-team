checks2 = checkpoint_raw_integrity()
chain_ok, chain_msg = AUDIT.verify()
tool_calls = sum(1 for e in AUDIT.events if e["action"].startswith("tool_called:"))
tool_errors = sum(1 for e in AUDIT.events if e["action"].startswith("tool_failed:"))
ok2 = bool(checks2["contenu_inchangé"].all()) and chain_ok and tool_errors == 0

AUDIT.log("orchestrator", "checkpoint_step2",
          {"passed": ok2, "raw_unchanged": bool(checks2["contenu_inchangé"].all()),
           "tool_calls": tool_calls, "tool_errors": tool_errors, "audit_chain": chain_msg},
          level="INFO" if ok2 else "ERROR")

print(f"Outils enregistrés : {list(TOOL_REGISTRY)}")
print(f"Appels d'outils tracés : {tool_calls} · erreurs : {tool_errors}")
print(f"Données brutes inchangées : {bool(checks2['contenu_inchangé'].all())}")
print(f"Journal d'audit : {chain_msg}")
print("ÉTAPE 2 VALIDÉE" if ok2 else "ÉTAPE 2 EN ÉCHEC")
pd.DataFrame([{"outil": k, "agent": v["agent"], "lecture_seule": v["read_only"],
               "paramètres": ", ".join(v["params"]), "description": v["description"]}
              for k, v in TOOL_REGISTRY.items()])
