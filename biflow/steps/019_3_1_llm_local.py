import gc
import os
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")   # limite la fragmentation mémoire

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

LLM_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"   # 7B sur "GPU T4 x2" ; sinon "Qwen/Qwen2.5-3B-Instruct" sur un seul T4


class LocalLLM:
    """LLM open-source exécuté localement sur le GPU : aucune donnée n'est envoyée à une API externe."""

    def __init__(self, model_id: str):
        self.model_id = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        # Répartition équilibrée sur les GPU, en gardant ~2 Go libres par GPU pour les calculs
        max_memory = {i: "12GiB" for i in range(torch.cuda.device_count())}
        self.model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16,
                                                          device_map="auto", max_memory=max_memory)
        self.model.eval()

    @torch.inference_mode()
    def chat(self, messages: list[dict], max_new_tokens: int = 256) -> str:
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        output = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,   # déterministe
                                     temperature=None, top_p=None, top_k=None,
                                     pad_token_id=self.tokenizer.eos_token_id)
        return self.tokenizer.decode(output[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()


assert torch.cuda.is_available(), "Activez un GPU (Settings > Accelerator > GPU T4 x2) et Internet."

# Si la cellule est relancée, on libère d'abord l'ancien modèle (sinon il est chargé deux fois)
if "LLM" in globals():
    del LLM
    gc.collect()
    torch.cuda.empty_cache()

t0 = time.perf_counter()
LLM = LocalLLM(LLM_MODEL_ID)
gpu_memory = {f"GPU {i}": f"{torch.cuda.memory_allocated(i) / 1e9:.1f} Go" for i in range(torch.cuda.device_count())}
AUDIT.log("orchestrator", "llm_loaded", {
    "model": LLM_MODEL_ID, "gpu": f"{torch.cuda.device_count()} x {torch.cuda.get_device_name(0)}",
    "gpu_memory": gpu_memory, "load_seconds": round(time.perf_counter() - t0, 1),
    "torch": torch.__version__, "transformers": transformers.__version__, "decoding": "greedy (do_sample=False)"})
print(f"{LLM_MODEL_ID} chargé sur {torch.cuda.device_count()} × {torch.cuda.get_device_name(0)} en {time.perf_counter() - t0:.0f} s")
print(f"Mémoire utilisée : {gpu_memory}")
print(LLM.chat([{"role": "user", "content": "En une phrase : pourquoi une valeur manquante n'est-elle pas toujours une erreur ?"}], 60))
