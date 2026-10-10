from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CleaningProposal(BaseModel):
    proposal_id: str = Field(default="")
    operation: str
    target_columns: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str
    expected_effect: str = ""
    verification_check: str = ""
    confidence: Literal["low", "medium", "high"] = "medium"
    confidence_basis: str = ""


class CriticVerdict(BaseModel):
    proposal_id: str = Field(default="")
    verdict: Literal["APPROVE", "REJECT", "ESCALATE_TO_HUMAN"]
    reasons: list[str] = Field(default_factory=list)
    unsupported_assumptions: list[str] = Field(default_factory=list)
    requested_checks: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class ProposalItemResponse(BaseModel):
    type: Literal["proposal", "verdict"]
    iteration: Optional[int] = None
    proposal_id: str
    operation: Optional[str] = None
    target_columns: Optional[list[str]] = None
    parameters: Optional[dict[str, Any]] = None
    rationale: Optional[str] = None
    confidence: Optional[str] = None
    confidence_basis: Optional[str] = None
    verdict: Optional[Literal["APPROVE", "REJECT", "ESCALATE_TO_HUMAN"]] = None
    reasons: Optional[list[str]] = None
    unsupported_assumptions: Optional[list[str]] = None
    created_at: Optional[str] = None


class DiffItem(BaseModel):
    column: Optional[str] = None
    row_index: Optional[int] = None
    original_row_index: Optional[int] = None
    change_type: Literal["modified", "removed", "added"]
    original_value: Optional[Any] = None
    new_value: Optional[Any] = None
    rule: str
    confidence: str
    confidence_basis: str


class DistributionBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int
    frequency: float


class ColumnDistribution(BaseModel):
    column: str
    before_bins: list[DistributionBin]
    after_bins: list[DistributionBin]
    ks_statistic: float
    p_value: float
    passed: bool


class EvidenceItem(BaseModel):
    evidence_id: str
    claim: str
    test_name: str
    statistic: Optional[str] = None
    p_value: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class InvestigationResponse(BaseModel):
    investigation_id: str
    status: Literal["pending", "running", "awaiting_human", "completed", "partial", "failed"]
    state: str
    iteration: int
    max_iterations: int
    cost_used: int
    cost_budget: int
    dataset_version_id: str
    output_version_id: Optional[str] = None
    error: Optional[str] = None


class ReviewItem(BaseModel):
    review_id: str
    investigation_id: str
    proposal_id: str
    status: str
    proposal_summary: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None


class ReviewDecisionRequest(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    parameters: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_edit_has_parameters(self) -> "ReviewDecisionRequest":
        if self.decision == "edit" and self.parameters is None:
            raise ValueError("Parameters object is required when decision is 'edit'")
        return self


class WatchCreateRequest(BaseModel):
    dataset_id: str
    schedule: str = "@daily"
    drift_threshold: str = "0.10"
    enabled: bool = True


class WatchResponse(BaseModel):
    id: str
    dataset_id: str
    schedule: str
    drift_threshold: str
    enabled: bool
    last_checked_at: Optional[str] = None
    created_at: str
