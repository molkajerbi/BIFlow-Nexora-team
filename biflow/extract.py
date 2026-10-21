"""Extrait les cellules de code du notebook validé vers biflow/steps/ (le notebook reste la source de vérité)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "notebooks" / "biflowenglisch.ipynb"
STEPS_DIR = Path(__file__).resolve().parent / "steps"

# Cellule LLM du notebook (GPU) : remplacée par le LLM Ollama (voir engine.py)
REPLACED = {"class LocalLLM": "llm"}

# Cellules propres au notebook, ignorées en déploiement (repérées par leur contenu, pas par leur position).
# Le moteur joue lui-même le rôle des orchestrateurs : il n'a pas besoin de « tout refaire une deuxième fois ».
SKIPPED = {
    "class BIFlowState": "graphe global : le moteur joue ce rôle (13.1)",
    "tampered = copy.deepcopy(AUDIT)": "démo de falsification (1.3)",
    "DATA_PREP_RESULT = run_data_preparation()": "relance de la partie 1 par son orchestrateur (6.6)",
    "r_ = DATA_PREP_RESULT": "bilan de la relance 6.6 (6.7)",
    "BI_RESULT = run_bi_insight()": "relance de la partie 2 par son orchestrateur (11.4)",
    "RESUME_RESULT = run_bi_insight(": "démo de reprise (11.5)",
    't_start = next(e["ts"]': "diagnostic de reproductibilité (11.6)",
    "def run_biflow()": "point d'entrée global : le moteur joue ce rôle (13.2)",
    "BIFLOW_RESULT = run_biflow()": "relance de A à Z (13.3)",
    "parts = BIFLOW_RESULT.get(": "bilan de la relance 13.3 (13.4)",
    'ask("Résume le travail de BIFlow de A à Z.", mode="règles")': "démo du chat (13.5) : le chat est dans l'interface",
    'ask("Summarise BIFlow\'s work from A to Z.", mode="rules")': "démo du chat (13.5) : le chat est dans l'interface",
}

# Adaptations au déploiement (le code du notebook supposait Linux + GPU + Jupyter, comme sur Kaggle)
PATCHES = [
    # mémoire utilisée, sur tous les systèmes (Windows n'a pas /proc)
    ('    with open("/proc/self/status") as f:\n        return int(f.read().split("VmRSS:")[1].split()[0]) / 1e6',
     '    import psutil                                    # mémoire utilisée, sur tous les systèmes\n'
     '    return psutil.Process().memory_info().rss / 1e9'),
    # pas de GPU (Ollama tourne sur le processeur) : rien à libérer côté GPU, et torch n'est jamais importé à chaque appel
    ("    try:\n        import torch\n        if torch.cuda.is_available():\n            torch.cuda.empty_cache()\n    except ImportError:\n        pass",
     "    pass                                             # déploiement sur processeur : pas de mémoire GPU à libérer"),
    # pas de Jupyter : pas d'image du graphe (elle demanderait Internet), pas d'aperçu HTML dans le journal
    ("    from IPython.display import Image\n", "    raise ImportError(\"aperçu du graphe désactivé en déploiement\")\n"),
    ("    from IPython.display import HTML\n", "    raise ImportError(\"aperçu HTML désactivé en déploiement\")\n"),
    # questions de démonstration du chat : réponses des règles (rapides) ; le chat avec le LLM est dans l'interface
    ("for demo_q in DEMO_QUESTIONS:\n    ask(demo_q)", "for demo_q in DEMO_QUESTIONS:\n    ask(demo_q, mode=\"rules\", show=False)"),
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
            # titre numéroté (« ## 7.1 Pont… »), même si la cellule a été collée avec des « # » en trop devant
            titles = [re.sub(r"^[#\s]+", "", line).strip() for line in source.splitlines() if line.lstrip().startswith("#")]
            numbered = [t for t in titles if re.match(r"\d+\.\d+", t)]
            if numbered:
                heading = numbered[-1]
            continue
        if cell["cell_type"] != "code" or not source.strip():
            continue
        n = len(manifest) + 1
        kind = next((k for marker, k in REPLACED.items() if marker in source), "code")
        skip = next((why for marker, why in SKIPPED.items() if marker in source), None)
        match = re.match(r"(\d+)\.(\d+)", heading)
        step = int(match.group(1)) if match else 0
        file = f"{n:03d}_{re.sub(r'[^0-9a-z]+', '_', heading.lower()).strip('_')[:40]}.py"
        (STEPS_DIR / file).write_text(source + "\n", encoding="utf-8")
        manifest.append({"n": n, "file": file, "title": heading, "step": step, "kind": kind, "skip": skip})
    (STEPS_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    for m in extract():
        print(f"{m['n']:03d}  étape {m['step']:>2}  {m['title'][:55]:55s}  {m['kind']}"
              f"{'  (ignorée : ' + m['skip'] + ')' if m['skip'] else ''}")
