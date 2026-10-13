from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

pd.set_option("display.max_columns", 60)
pd.set_option("display.width", 180)
pd.set_option("display.max_colwidth", 80)

# ===== Réglages (facultatifs) : le pipeline fonctionne sans rien modifier =====
AUTONOMY = os.environ.get("BIFLOW_AUTONOMY", "risk_based")   # "risk_based" (automatique) ou "manual" (un humain valide tout)

DATA_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xls", ".parquet", ".json"}
MODEL_EXTENSIONS = {".safetensors", ".bin", ".gguf", ".pt", ".pth", ".onnx", ".h5"}   # dossiers de modèles à ignorer


def dataset_root(path: Path, root: Path) -> Path:
    """Racine du dataset qui contient `path` (gère /kaggle/input/<nom> et /kaggle/input/datasets/<auteur>/<nom>)."""
    parts = path.relative_to(root).parts
    if len(parts) == 1:
        return root
    if parts[0] == "datasets" and len(parts) >= 4:
        return root.joinpath(*parts[:3])
    if parts[0] == "competitions" and len(parts) >= 3:
        return root.joinpath(*parts[:2])
    return root / parts[0]


def list_data_files(folder: Path) -> list[Path]:
    """Tous les fichiers de données d'un dossier (récursif), hors dossiers de modèles d'IA."""
    files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in DATA_EXTENSIONS
             and not p.name.startswith(".") and p.name != "biflow_overrides.json"]
    model_dirs = {p.parent for p in folder.rglob("*") if p.suffix.lower() in MODEL_EXTENSIONS}
    return sorted(p for p in files if not any(d == p.parent or d in p.parents for d in model_dirs))


def find_data_dir() -> Path:
    """Trouve LE dataset fourni en entrée (Kaggle ou local). Zéro ou plusieurs datasets : arrêt explicite."""
    explicit = os.environ.get("BIFLOW_DATA_DIR")
    roots = [Path(explicit)] if explicit else [Path("/kaggle/input"), Path("./data")]
    found = {dataset_root(p, root) for root in roots if root.exists() for p in list_data_files(root)}
    if len(found) != 1:
        raise FileNotFoundError(
            f"{len(found)} dataset(s) trouvé(s) : {sorted(map(str, found))}. "
            "Attachez UN seul dataset (CSV, Excel, Parquet ou JSON), ou définissez BIFLOW_DATA_DIR.")
    return found.pop()


@dataclass(frozen=True)
class Config:
    data_dir: Path = field(default_factory=find_data_dir)
    autonomy: str = AUTONOMY
    output_root: Path = Path("/kaggle/working/biflow_runs") if Path("/kaggle/working").exists() else Path("./biflow_runs")
    random_seed: int = 42
    project: str = "BIFlow"
    agent: str = "data_preparation_agent"


CONFIG = Config()
assert CONFIG.autonomy in {"risk_based", "manual"}, "AUTONOMY : 'risk_based' ou 'manual'"

random.seed(CONFIG.random_seed)
np.random.seed(CONFIG.random_seed)

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:6]
RUN_DIR = CONFIG.output_root / RUN_ID
RUN_DIR.mkdir(parents=True, exist_ok=False)   # une exécution n'écrase jamais une autre

print(f"Données   : {CONFIG.data_dir} ({len(list_data_files(CONFIG.data_dir))} fichier(s))")
print(f"Autonomie : {CONFIG.autonomy}")
print(f"Run ID    : {RUN_ID}")
print(f"Sorties   : {RUN_DIR}")
print(f"Python {platform.python_version()} · pandas {pd.__version__} · numpy {np.__version__}")
