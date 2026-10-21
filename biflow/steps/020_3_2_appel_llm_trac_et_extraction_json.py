def llm_call(agent: str, messages: list[dict], max_new_tokens: int = 256) -> str:
    """Calls the LLM and traces the call (prompt fingerprint, answer, duration) in the audit log."""
    t0 = time.perf_counter()
    response = LLM.chat(messages, max_new_tokens)
    AUDIT.log(agent, "llm_call", {
        "prompt_sha256": sha256_text(canonical_json(messages)),
        "prompt_chars": sum(len(m["content"]) for m in messages),
        "response": response[:600], "seconds": round(time.perf_counter() - t0, 2)})
    return response


def extract_json(text: str, expected: type):
    """Extracts the first valid JSON object {...} or array [...] from an LLM answer."""
    opener = "{" if expected is dict else "["
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == opener:
            try:
                value, _ = decoder.raw_decode(text[i:])
                if isinstance(value, expected):
                    return value
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no valid JSON {'object' if expected is dict else 'array'} in the answer")


print(extract_json('Here is my decision: {"action": "finish", "table": null, "reason": "ok"} thanks', dict))
