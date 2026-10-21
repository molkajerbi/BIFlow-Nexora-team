"""Chat XAI de l'interface : « Pourquoi BIFlow a-t-il fait ça ? »

Le pipeline tourne dans un processus séparé qui se termine à la fin de l'analyse. Pour discuter ensuite avec l'agent XAI,
ce module reconstruit l'agent à partir de deux sources :
  - le CODE de l'agent, repris tel quel des cellules du notebook (étapes 12.3 à 12.5 : recherche des explications,
    réponse par les règles, reformulation par le LLM vérifiée par le code, fil de conversation) ;
  - les DONNÉES exportées par le run : registre des décisions, règles du système et journal d'audit.
Rien n'est réécrit : si le notebook change, le chat change avec lui.
"""
from __future__ import annotations

import ast
import json
import types
from pathlib import Path

from .extract import STEPS_DIR

ROOT = Path(__file__).resolve().parent.parent

# Ce dont le chat a besoin (définitions des cellules du notebook) ; leurs dépendances sont ajoutées automatiquement
ENTRY_POINTS = ["XAIChat", "XAIIndex", "xai_search", "intent_of", "rule_answer", "llm_explanation", "render_record",
                "AuditTrail"]
CONSTANTS = {"XAI_STEPS", "STEP_WORDS", "INTENTS", "LIST_SUBJECTS", "SYSTEM_XAI", "NUM_RE", "UP_RE", "DOWN_RE"}
PROVIDED = {"LEDGER", "METHODS", "AUDIT", "LLM", "LLM_LOG", "XAI_DIR", "XAI_INDEX", "SEARCH", "RUN_ID", "RUN_DIR",
            "display"}


def _definitions() -> dict:
    """Dernière définition de chaque nom (fonction, classe, constante, import) dans les cellules des étapes 1 à 12."""
    manifest = json.loads((STEPS_DIR / "manifest.json").read_text(encoding="utf-8"))
    found: dict[str, ast.stmt] = {}
    for m in manifest:
        if m["kind"] != "code" or not 1 <= m["step"] <= 12:
            continue
        tree = ast.parse((STEPS_DIR / m["file"]).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                found[node.name] = node
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    found[(alias.asname or alias.name).split(".")[0]] = ast.fix_missing_locations(
                        type(node)(**{**{f: getattr(node, f) for f in node._fields}, "names": [alias]}))
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Name) and (t.id in CONSTANTS or (t.id.isupper() and _is_constant(node.value))):
                        found[t.id] = node
    return found


def _is_constant(value) -> bool:
    """Constante écrite en dur (liste de mois, motif re.compile…) : elle peut être reprise sans les données du run."""
    if value is None:
        return False
    try:
        ast.literal_eval(value)
        return True
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        pass
    return (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and value.func.attr == "compile"
            and isinstance(value.func.value, ast.Name) and value.func.value.id == "re")


def _names_used(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def agent_source() -> str:
    """Code de l'agent XAI repris du notebook : les points d'entrée et tout ce dont ils dépendent."""
    defs = _definitions()
    todo, chosen = list(ENTRY_POINTS), {}
    while todo:
        name = todo.pop()
        if name in chosen or name in PROVIDED or name not in defs:
            continue
        chosen[name] = defs[name]
        todo += sorted(_names_used(defs[name]) - set(chosen))
    order = {id(n): i for i, n in enumerate(defs.values())}
    nodes = sorted({id(n): n for n in chosen.values()}.values(),
                   key=lambda n: (not isinstance(n, (ast.Import, ast.ImportFrom)), order.get(id(n), 0)))
    return "\n\n".join(ast.unparse(n) for n in nodes)


class _Search:
    """Modèle d'embeddings du run (le même qu'à l'étape 7.5), ou None : la recherche reste alors lexicale."""

    def __init__(self, enabled: bool):
        self.model = None
        if enabled:
            try:
                import os
                os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")     # Windows : torch + numpy (OpenMP)
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(os.environ.get("BIFLOW_EMBED_MODEL", "intfloat/multilingual-e5-small"),
                                                 device="cpu")
            except Exception:
                self.model = None


def _turn(turn: dict) -> dict:
    """Un échange du chat avec les clés lues par l'interface (le notebook anglais écrit answer / llm_rejections)."""
    turn = dict(turn)
    turn.setdefault("réponse", turn.get("answer", ""))
    turn.setdefault("refus_llm", turn.get("llm_rejections", []))
    return turn


class XAISession:
    """Une conversation avec l'agent XAI sur UNE analyse (le fil est gardé dans <job>/chat/chat.jsonl)."""

    def __init__(self, job_dir: str | Path, llm=None):
        job_dir = Path(job_dir)
        result = json.loads((job_dir / "result.json").read_text(encoding="utf-8"))
        xai = result.get("xai") or {}
        if not xai.get("ready"):
            raise RuntimeError("explainability was not built for this analysis")
        xai_dir, run_dir = Path(xai["xai_dir"]), Path(result["run_dir"])
        ledger = json.loads((xai_dir / "decision_ledger.json").read_text(encoding="utf-8"))
        if ledger and "décision" in ledger[0] and "decision" not in ledger[0]:
            raise RuntimeError("this analysis was made with the previous (French) notebook: click \"Run again\" to use "
                               "the assistant with the English pipeline")
        chat_dir = job_dir / "chat"
        chat_dir.mkdir(exist_ok=True)
        module = types.ModuleType("biflow_xai_chat")
        ns = module.__dict__
        ns.update({"display": lambda *a, **k: None, "LLM": llm, "LLM_LOG": chat_dir / "llm_calls.jsonl",
                   "XAI_DIR": chat_dir, "RUN_DIR": run_dir, "RUN_ID": result.get("run_id"),
                   "LEDGER": ledger,
                   "METHODS": json.loads((xai_dir / "rules.json").read_text(encoding="utf-8")),
                   "SEARCH": _Search("embeddings" in str((result.get("bi") or {}).get("search_mode")))})
        exec(compile(agent_source(), "<agent XAI (notebook, étapes 12.3 à 12.5)>", "exec"), ns)
        audit = ns["AuditTrail"](result.get("run_id"), chat_dir / "chat_audit.jsonl")
        audit_file = run_dir / "audit_log.jsonl"
        if audit_file.exists():                  # journal du run : refus du LLM, début du run… (lecture seule)
            audit.events = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        ns["AUDIT"] = audit
        ns["XAI_INDEX"] = ns["XAIIndex"](ns["LEDGER"] + ns["METHODS"])
        self.ns, self.chat = ns, ns["XAIChat"]()
        self.history_path = chat_dir / "chat.jsonl"
        if self.history_path.exists():
            self.chat.history = [json.loads(line) for line in self.history_path.read_text(encoding="utf-8").splitlines()
                                 if line.strip()]
        self.llm_ready = llm is not None

    @property
    def history(self) -> list[dict]:
        return [_turn(t) for t in self.chat.history]

    def ask(self, question: str, use_llm: bool = True) -> dict:
        """Réponse des règles, reformulée par le LLM si possible ; une reformulation refusée par le code est remplacée
        par la réponse des règles (l'utilisateur ne reçoit jamais une explication non vérifiée)."""
        mode = "auto" if use_llm and self.llm_ready else "rules"
        try:
            return _turn(self.chat.ask(question, mode=mode, show=False))
        except Exception as exc:                 # Ollama fermé pendant la question : réponse des règles
            if mode == "rules":
                raise
            turn = _turn(self.chat.ask(question, mode="rules", show=False))
            turn["refus_llm"] = [f"LLM unavailable: {exc}"]
            return turn

    def clear(self) -> None:
        self.chat.history.clear()
        self.history_path.unlink(missing_ok=True)
