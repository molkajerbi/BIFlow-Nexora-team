def llm_call(agent: str, messages: list[dict], max_new_tokens: int = 256) -> str:
    """Appelle le LLM et trace l'appel (empreinte du prompt, réponse, durée) dans l'audit."""
    t0 = time.perf_counter()
    response = LLM.chat(messages, max_new_tokens)
    AUDIT.log(agent, "llm_call", {
        "prompt_sha256": sha256_text(canonical_json(messages)),
        "prompt_chars": sum(len(m["content"]) for m in messages),
        "response": response[:600], "seconds": round(time.perf_counter() - t0, 2)})
    return response


def extract_json(text: str, expected: type):
    """Extrait le premier objet {...} ou tableau [...] JSON valide d'une réponse de LLM."""
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
    raise ValueError(f"aucun {'objet' if expected is dict else 'tableau'} JSON valide dans la réponse")


print(extract_json('Voici ma décision : {"action": "finish", "table": null, "reason": "ok"} merci', dict))
