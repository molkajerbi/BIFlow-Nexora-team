"""Extrait les cellules de code du notebook validé vers biflow/steps/ (le notebook reste la source de vérité)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "notebooks" / "data-preparation-agent.ipynb"
STEPS_DIR = Path(__file__).resolve().parent / "steps"

# Cellules propres au notebook, remplacées ou ignorées en déploiement (repérées par leur contenu, pas leur position)
REPLACED = {"class LocalLLM": "llm"}                                   # LLM GPU -> LLM Ollama (voir engine.py)
SKIPPED = {"tampered = copy.deepcopy(AUDIT)": "démo de falsification (1.3)"}

# Adaptations Windows / Linux / macOS (le code du notebook supposait Linux, comme sur Kaggle)
PATCHES = [
    ('    with open("/proc/self/status") as f:\n        return int(f.read().split("VmRSS:")[1].split()[0]) / 1e6',
     '    import psutil                                    # mémoire utilisée, sur tous les systèmes\n'
     '    return psutil.Process().memory_info().rss / 1e9'),
]


def extract(notebook: Path = NOTEBOOK) -> list[dict]:
    nb = json.loads(notebook.read_text(encoding="utf-8"))
    STEPS_DIR.mkdir(exist_ok=True)
    for old in STEPS_DIR.glob("*.py"):
        old.unlink()
    manifest, heading = [], "Introduction"
    for cell in nb["cells"]:
        source = "".join(cell["source"])
        for old, new in PATCHES:
            source = source.replace(old, new)
        if cell["cell_type"] == "markdown":
            titles = re.findall(r"^#{1,3}\s+(.+)$", source, flags=re.M)
            if titles:
                heading = titles[-1].strip()
            continue
        if cell["cell_type"] != "code" or not source.strip():
            continue
        n = len(manifest) + 1
        kind = next((k for marker, k in REPLACED.items() if marker in source), "code")
        skip = next((why for marker, why in SKIPPED.items() if marker in source), None)
        match = re.match(r"(\d+)\.(\d+)", heading)
        step = int(match.group(1)) if match else 6          # le bilan final (6.8) n'a pas de numéro d'étape propre
        file = f"{n:02d}_{re.sub(r'[^0-9a-z]+', '_', heading.lower()).strip('_')[:40]}.py"
        (STEPS_DIR / file).write_text(source + "\n", encoding="utf-8")
        manifest.append({"n": n, "file": file, "title": heading, "step": step, "kind": kind, "skip": skip})
    (STEPS_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    for m in extract():
        print(f"{m['n']:02d}  étape {m['step']}  {m['title'][:55]:55s}  {m['kind']}{'  (ignorée : ' + m['skip'] + ')' if m['skip'] else ''}")