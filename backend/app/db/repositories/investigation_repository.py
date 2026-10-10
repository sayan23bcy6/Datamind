from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models.dataset import DatasetVersion
from app.db.models.investigation import (
    AgentMessage,
    CleaningDecision,
    Evidence,
    HumanReview,
    Investigation,
    InvestigationReport,
    ToolCall,
    Watch,
    WorkflowCheckpoint,
)


class InvestigationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_investigation(self, investigation_id: str) -> Investigation | None:
        return self.db.query(Investigation).filter(Investigation.id == investigation_id).first()

    def get_dataset_version(self, version_id: str) -> DatasetVersion | None:
        return self.db.query(DatasetVersion).filter(DatasetVersion.id == version_id).first()

    def create_investigation(self, *, dataset_id: str, dataset_version_id: str, status: str = "pending", state: str = "PROFILE") -> Investigation:
        investigation = Investigation(dataset_id=dataset_id, dataset_version_id=dataset_version_id, status=status, state=state, cost_budget=20000)
        self.db.add(investigation)
        self.db.commit()
        self.db.refresh(investigation)
        return investigation

    def update_investigation(self, investigation: Investigation, **kwargs: Any) -> Investigation:
        for key, value in kwargs.items():
            setattr(investigation, key, value)
        self.db.commit()
        self.db.refresh(investigation)
        return investigation

    def add_checkpoint(self, investigation_id: str, state: str, iteration: int, payload: dict[str, Any] | None = None) -> WorkflowCheckpoint:
        checkpoint = WorkflowCheckpoint(investigation_id=investigation_id, state=state, iteration=iteration, payload=payload or {})
        self.db.add(checkpoint)
        self.db.commit()
        self.db.refresh(checkpoint)
        return checkpoint

    def add_message(self, investigation_id: str, role: str, content: str) -> AgentMessage:
        message = AgentMessage(investigation_id=investigation_id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def add_tool_call(self, investigation_id: str, dataset_version_id: str, tool_name: str, inputs: dict[str, Any] | None, outputs: dict[str, Any] | None, duration_ms: int, input_hash: str) -> ToolCall:
        call = ToolCall(
            investigation_id=investigation_id,
            dataset_version_id=dataset_version_id,
            tool_name=tool_name,
            inputs=inputs or {},
            outputs=outputs or {},
            duration_ms=duration_ms,
            input_hash=input_hash,
        )
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        return call

    def add_decision(self, investigation_id: str, dataset_version_id: str, operation: str, reason: str, row_count_delta: int, target_columns: list[str] | None = None) -> CleaningDecision:
        decision = CleaningDecision(
            investigation_id=investigation_id,
            dataset_version_id=dataset_version_id,
            operation=operation,
            reason=reason,
            row_count_delta=row_count_delta,
            target_columns=target_columns or [],
        )
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        return decision

    def add_evidence(self, investigation_id: str, claim: str, test_name: str, statistic: str | None = None, p_value: str | None = None, details: dict[str, Any] | None = None) -> Evidence:
        evidence = Evidence(investigation_id=investigation_id, claim=claim, test_name=test_name, statistic=statistic, p_value=p_value, details=details or {})
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def add_review(self, investigation_id: str, action: str, payload: dict[str, Any] | None = None, reviewer: str | None = None) -> HumanReview:
        review = HumanReview(investigation_id=investigation_id, action=action, payload=payload or {}, reviewer=reviewer)
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def add_report(self, investigation_id: str, kind: str, path: str) -> InvestigationReport:
        report = InvestigationReport(investigation_id=investigation_id, kind=kind, path=path)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_reports(self, investigation_id: str):
        return self.db.query(InvestigationReport).filter(InvestigationReport.investigation_id == investigation_id).all()

    def list_messages(self, investigation_id: str):
        return self.db.query(AgentMessage).filter(AgentMessage.investigation_id == investigation_id).order_by(AgentMessage.created_at.asc()).all()

    def list_checkpoints(self, investigation_id: str):
        return self.db.query(WorkflowCheckpoint).filter(WorkflowCheckpoint.investigation_id == investigation_id).order_by(WorkflowCheckpoint.created_at.asc()).all()

    def list_tool_calls(self, investigation_id: str):
        return self.db.query(ToolCall).filter(ToolCall.investigation_id == investigation_id).order_by(ToolCall.created_at.asc()).all()

    def list_decisions(self, investigation_id: str):
        return self.db.query(CleaningDecision).filter(CleaningDecision.investigation_id == investigation_id).order_by(CleaningDecision.created_at.asc()).all()

    def get_or_create_watch(self, dataset_id: str, schedule: str = "@daily", drift_threshold: str = "0.10", enabled: bool = True) -> Watch:
        watch = self.db.query(Watch).filter(Watch.dataset_id == dataset_id).first()
        if watch is None:
            watch = Watch(dataset_id=dataset_id, schedule=schedule, drift_threshold=drift_threshold, enabled=enabled)
            self.db.add(watch)
            self.db.commit()
            self.db.refresh(watch)
        return watch

    def list_watches(self, dataset_id: str | None = None):
        query = self.db.query(Watch)
        if dataset_id is not None:
            query = query.filter(Watch.dataset_id == dataset_id)
        return query.order_by(Watch.created_at.desc()).all()
