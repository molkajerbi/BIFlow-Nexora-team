import copy

tampered = copy.deepcopy(AUDIT)
tampered.path = RUN_DIR / "_tamper_test.jsonl"          # n'écrit pas dans le vrai journal
tampered.log("profiler", "demo_event", {"rows": 100})
tampered.log("quality", "demo_event", {"rows": 100})

print("Before tampering:", tampered.verify())
tampered.events[1]["details"]["rows"] = 999               # modification frauduleuse
print("After tampering :", tampered.verify())

(RUN_DIR / "_tamper_test.jsonl").unlink(missing_ok=True)
del tampered
