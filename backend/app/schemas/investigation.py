from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CleaningOperation(str):
    pass


class CleaningProposal(BaseModel):
    operation: str
    target_columns: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str
    expected_effect: str
    verification_check: str
    confidence: Literal["low", "medium", "high"] = "medium"
    basis: str


class CriticVerdict(BaseModel):
    verdict: Literal["APPROVE", "REJECT", "ESCALATE_TO_HUMAN"]
    reasons: list[str] = Field(default_factory=list)
    unsupported_assumptions: list[str] = Field(default_factory=list)
    requested_checks: list[str] = Field(default_factory=list)


class CleaningDecisionRecord(BaseModel):
    rows_removed: int = 0
    rows_added: int = 0
    reason: str = ""
    operation: str = ""
    target_columns: list[str] = Field(default_factory=list)


class InvestigationSummary(BaseModel):
    status: str = "pending"
    state: str = "PROFILE"
    iteration: int = 0
    cost_used: int = 0
    cost_budget: int = 0
