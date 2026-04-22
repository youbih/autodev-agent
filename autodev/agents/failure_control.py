from __future__ import annotations

from typing import Any, Dict, List, Tuple


def init_run_controls(state: Dict[str, Any]) -> Dict[str, Any]:
    run = state.setdefault("run", {})
    run.setdefault("retry_count", 0)
    run.setdefault("max_retries", 3)
    run.setdefault("failures", [])
    run.setdefault("errors", [])
    run.setdefault("flags", {})
    run.setdefault("qa", {"passed": False})
    return state


def record_failure(
    state: Dict[str, Any],
    *,
    step: str,
    reason: str,
    detail: str | None = None,
) -> None:
    run = state.setdefault("run", {})
    failures: List[Dict[str, Any]] = run.setdefault("failures", [])
    failures.append(
        {
            "step": step,
            "reason": reason,
            "detail": detail or "",
        }
    )


def bump_retry(state: Dict[str, Any]) -> Tuple[int, int]:
    run = state.setdefault("run", {})
    run["retry_count"] = int(run.get("retry_count", 0)) + 1
    return int(run["retry_count"]), int(run.get("max_retries", 3))