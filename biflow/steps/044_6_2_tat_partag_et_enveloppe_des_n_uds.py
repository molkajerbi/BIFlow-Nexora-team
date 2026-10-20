from typing import TypedDict


class DataPrepState(TypedDict, total=False):
    run_id: str
    status: str                      # running · blocked · failed · success
    error: str | None
    history: list                    # une entrée par nœud exécuté
    profiler: dict
    quality: dict
    etl: dict
    outputs: dict


STOP_STATES = {"failed", "blocked"}


def graph_node(name: str):
    """Chaque nœud est chronométré, tracé dans l'audit, et une exception devient un état 'failed' (pas un crash)."""
    def decorator(fn):
        def wrapper(state: DataPrepState) -> dict:
            t0 = time.perf_counter()
            AUDIT.log("orchestrator", f"node_started:{name}", {"status_in": state.get("status")})
            try:
                update = fn(state) or {}
            except Exception as exc:
                update = {"status": "failed", "error": f"{name} : {type(exc).__name__} : {exc}"}
            summary = update.pop("summary", None)
            entry = {"node": name, "seconds": round(time.perf_counter() - t0, 1),
                     "status": update.get("status", state.get("status")), "summary": summary}
            AUDIT.log("orchestrator", f"node_finished:{name}", entry,
                      level="ERROR" if entry["status"] == "failed" else "INFO")
            update["history"] = list(state.get("history", [])) + [entry]
            return update
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


def route(state: DataPrepState) -> str:
    """Après chaque nœud : continuer, ou aller au rapport si le pipeline doit s'arrêter."""
    return "stop" if state.get("status") in STOP_STATES else "continue"


print("État partagé et enveloppe des nœuds prêts")
