from __future__ import annotations

from typing import Any

WORKFLOW_STATES = [
    "PROFILE",
    "INVESTIGATE",
    "CRITIQUE",
    "ROUTE",
    "EXECUTE",
    "REPROFILE",
    "VERIFY",
    "REPORT",
    "AWAIT_HUMAN",
    "COMPLETED",
    "PARTIAL",
    "FAILED",
]


def route_investigation(verdicts: list[dict[str, Any]], iteration: int, max_iterations: int, cost_used: int, cost_budget: int) -> tuple[str, str]:
    """Route a critique round to the next workflow step.

    Returns a pair of (next_state, reason).
    """
    if cost_used >= cost_budget:
        return "PARTIAL", "cost budget exhausted"
    if iteration >= max_iterations:
        return "PARTIAL", "iteration cap reached"

    verdicts = verdicts or []
    if any(v.get("verdict") == "ESCALATE_TO_HUMAN" for v in verdicts):
        return "AWAIT_HUMAN", "escalated for human review"

    if all(v.get("verdict") == "APPROVE" for v in verdicts):
        return "EXECUTE", "all proposals approved"

    if any(v.get("verdict") == "REJECT" for v in verdicts):
        return "INVESTIGATE", "rejected proposals require another investigation pass"

    return "PARTIAL", "no actionable verdicts"


def transition_to_next_state(current_state: str, next_state: str | None = None) -> str:
    if next_state is not None:
        return next_state
    if current_state == "PROFILE":
        return "INVESTIGATE"
    if current_state == "INVESTIGATE":
        return "CRITIQUE"
    if current_state == "CRITIQUE":
        return "ROUTE"
    if current_state == "EXECUTE":
        return "REPROFILE"
    if current_state == "REPROFILE":
        return "VERIFY"
    if current_state == "VERIFY":
        return "REPORT"
    if current_state == "REPORT":
        return "COMPLETED"
    if current_state == "AWAIT_HUMAN":
        return "EXECUTE"
    return current_state
