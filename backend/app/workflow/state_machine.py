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


def check_budget_exhausted(
    iteration: int,
    max_iterations: int,
    cost_tokens: int = 0,
    budget_tokens: int = 200000,
    tool_calls: int = 0,
    max_tool_calls: int = 500,
) -> tuple[bool, str]:
    """Pure function checking whether any workflow budget is exhausted."""
    if iteration >= max_iterations:
        return True, "iteration cap reached"
    if cost_tokens >= budget_tokens:
        return True, "token budget exhausted"
    if tool_calls >= max_tool_calls:
        return True, "tool call budget exhausted"
    return False, ""


def route_investigation(
    verdicts: list[dict[str, Any]],
    iteration: int,
    max_iterations: int,
    cost_used: int = 0,
    cost_budget: int = 200000,
    tool_calls: int = 0,
    max_tool_calls: int = 500,
) -> tuple[str, str]:
    """Pure function routing critique verdicts to the next workflow state."""
    exhausted, reason = check_budget_exhausted(
        iteration, max_iterations, cost_used, cost_budget, tool_calls, max_tool_calls
    )
    if exhausted:
        return "PARTIAL", reason

    verdicts = verdicts or []
    if any(v.get("verdict") == "ESCALATE_TO_HUMAN" for v in verdicts):
        return "AWAIT_HUMAN", "escalated for human review"

    if verdicts and all(v.get("verdict") == "APPROVE" for v in verdicts):
        return "EXECUTE", "all proposals approved"

    if any(v.get("verdict") == "REJECT" for v in verdicts):
        return "INVESTIGATE", "rejected proposals require another investigation pass"

    return "PARTIAL", "no actionable verdicts"


def route_human_review(decision: str) -> tuple[str, str]:
    """Pure function routing human review decision to next state."""
    dec = (decision or "").lower().strip()
    if dec in ("approve", "edit"):
        return "EXECUTE", f"human decision: {dec}"
    if dec == "reject":
        return "INVESTIGATE", "human reviewer rejected proposals"
    return "AWAIT_HUMAN", "awaiting valid decision"


def route_verification(passed: bool, budget_remaining: bool) -> tuple[str, str]:
    """Pure function routing verification outcome."""
    if passed:
        return "REPORT", "verification tolerances passed"
    if budget_remaining:
        return "INVESTIGATE", "verification failed; retrying investigation within budget"
    return "PARTIAL", "verification failed and budget exhausted"


def transition_to_next_state(current_state: str, next_state: str | None = None) -> str:
    """Deterministic step progression."""
    if next_state is not None:
        return next_state
    transitions = {
        "PROFILE": "INVESTIGATE",
        "INVESTIGATE": "CRITIQUE",
        "CRITIQUE": "ROUTE",
        "EXECUTE": "REPROFILE",
        "REPROFILE": "VERIFY",
        "VERIFY": "REPORT",
        "REPORT": "COMPLETED",
        "AWAIT_HUMAN": "EXECUTE",
    }
    return transitions.get(current_state, current_state)
