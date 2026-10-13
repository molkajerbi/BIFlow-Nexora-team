"""Ligne de commande BIFlow.

    python -m biflow extract                         # notebook -> biflow/steps/
    python -m biflow check                           # Ollama et le modèle sont-ils prêts ?
    python -m biflow run data/olist                  # lance le pipeline complet (100 % automatique) sur un dataset
    python -m biflow run data/olist --model qwen2.5:3b
"""
from __future__ import annotations

import argparse
import faulthandler
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    for stream in (sys.stdout, sys.stderr):           # accents et symboles lisibles aussi sous Windows
        stream.reconfigure(encoding="utf-8", errors="replace")
    faulthandler.enable()                             # un plantage « natif » (DLL, mémoire) laisse une trace dans le journal
    print(f"[BIFlow] processus {os.getpid()} démarré le {datetime.now():%d/%m/%Y à %H:%M:%S}", flush=True)
    parser = argparse.ArgumentParser(prog="biflow", description="BIFlow — Data Preparation Agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("extract", help="extrait les étapes du notebook vers biflow/steps/")
    check = sub.add_parser("check", help="vérifie Ollama et le modèle")
    check.add_argument("--model", default=None)
    run = sub.add_parser("run", help="lance le pipeline sur un dossier de données")
    run.add_argument("data_dir", help="dossier contenant UN dataset (CSV, TSV, Excel, Parquet, JSON)")
    run.add_argument("--job-dir", default=None, help="dossier de travail du run (par défaut jobs/<date>)")
    run.add_argument("--model", default=None, help="modèle Ollama (par défaut qwen2.5:7b)")
    args = parser.parse_args()

    if args.command == "extract":
        from .extract import extract
        print(f"{len(extract())} cellules extraites dans biflow/steps/")
        return 0

    from .llm import LLMUnavailable, OllamaLLM
    if args.command == "check":
        llm = OllamaLLM(model_id=args.model)
        try:
            llm.check()
        except LLMUnavailable as exc:
            print(f"ÉCHEC : {exc}")
            return 1
        print(f"OK : {llm.model_id} disponible sur {llm.url}")
        print("Test :", llm.chat([{"role": "user", "content": "Réponds seulement : prêt"}], 10))
        return 0

    from .engine import run_pipeline
    job_dir = Path(args.job_dir or Path("jobs") / datetime.now().strftime("%Y%m%d_%H%M%S"))
    result = run_pipeline(args.data_dir, job_dir, llm=OllamaLLM(model_id=args.model))
    print("\n" + "=" * 70)
    print(f"Statut : {result['status']}" + (f" · {result['error']}" if result.get("error") else ""))
    print(f"Domaine : {result.get('domain')}")
    print(f"Résultats : {job_dir / 'result.json'}")
    if result.get("output_dir"):
        print(f"Livrables : {result['output_dir']}")
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    sys.exit(main())