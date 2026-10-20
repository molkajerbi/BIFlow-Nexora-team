"""LLM local via Ollama : aucune clé d'API, aucune donnée envoyée à l'extérieur."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import requests


class LLMUnavailable(RuntimeError):
    """Ollama ne répond pas, ou le modèle n'est pas téléchargé."""


class OllamaLLM:
    """Même interface que LocalLLM du notebook : chat(messages, max_new_tokens) -> str.

    - décodage déterministe (temperature 0, seed fixe) : même prompt -> même réponse ;
    - cache sur disque : un prompt déjà traité n'est jamais recalculé (relance, ré-exécution du graphe) ;
    - num_ctx élargi : sinon Ollama tronque silencieusement les longs prompts.
    """

    def __init__(self, model_id: str | None = None, url: str | None = None,
                 cache_dir: str | Path | None = None, num_ctx: int = 8192, timeout: int = 900):
        self.model_id = model_id or os.environ.get("BIFLOW_LLM_MODEL", "qwen2.5:7b")
        self.url = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.num_ctx, self.timeout = num_ctx, timeout
        self.disabled = False                       # utilisé par le moteur quand il ne doit plus appeler le LLM
        self.calls = self.cache_hits = 0
        cache_dir = Path(cache_dir or os.environ.get("BIFLOW_CACHE_DIR", "biflow_cache")).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = cache_dir / "llm_cache.jsonl"
        self._cache: dict[str, str] = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                    self._cache[item["key"]] = item["response"]
                except (json.JSONDecodeError, KeyError):
                    continue                        # ligne incomplète (arrêt brutal) : ignorée

    def check(self) -> None:
        """Vérifie qu'Ollama tourne et que le modèle est téléchargé (message clair sinon)."""
        try:
            tags = requests.get(f"{self.url}/api/tags", timeout=10).json()
        except requests.RequestException as exc:
            raise LLMUnavailable(f"Ollama ne répond pas sur {self.url} : lancez l'application Ollama. ({exc})") from exc
        names = {m["name"] for m in tags.get("models", [])}
        if self.model_id not in names and f"{self.model_id}:latest" not in names:
            raise LLMUnavailable(f"Modèle '{self.model_id}' absent d'Ollama : exécutez « ollama pull {self.model_id} ». "
                                 f"Modèles disponibles : {sorted(names) or 'aucun'}")

    def _key(self, messages: list[dict], max_new_tokens: int) -> str:
        payload = json.dumps([self.model_id, messages, max_new_tokens], sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def chat(self, messages: list[dict], max_new_tokens: int = 256) -> str:
        if self.disabled:
            raise LLMUnavailable("appel LLM désactivé à ce stade du pipeline")
        key = self._key(messages, max_new_tokens)
        if key in self._cache:
            self.cache_hits += 1
            return self._cache[key]
        try:
            r = requests.post(f"{self.url}/api/chat", timeout=self.timeout, json={
                "model": self.model_id, "messages": messages, "stream": False,
                "keep_alive": "30m",                    # le modèle reste en mémoire entre deux appels (pas de rechargement)
                "options": {"temperature": 0, "seed": 42, "num_predict": max_new_tokens, "num_ctx": self.num_ctx}})
            r.raise_for_status()
        except requests.RequestException as exc:
            raise LLMUnavailable(f"échec de l'appel à Ollama ({self.model_id}) : {exc}") from exc
        response = r.json()["message"]["content"].strip()
        self.calls += 1
        self._cache[key] = response
        with self.cache_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "response": response}, ensure_ascii=False) + "\n")
        return response