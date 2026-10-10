from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id"), nullable=False)
    output_version_id = Column(String(36), ForeignKey("dataset_versions.id"), nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending, running, awaiting_human, completed, partial, failed
    state = Column(String(32), nullable=False, default="PROFILE")
    iteration = Column(Integer, nullable=False, default=0)
    max_iterations = Column(Integer, nullable=False, default=3)
    cost_used = Column(Integer, nullable=False, default=0)
    cost_budget = Column(Integer, nullable=False, default=200000)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)

    dataset = relationship("Dataset")
    version = relationship("DatasetVersion", foreign_keys=[dataset_version_id])
    output_version = relationship("DatasetVersion", foreign_keys=[output_version_id])
    checkpoints = relationship("WorkflowCheckpoint", back_populates="investigation", cascade="all, delete-orphan")
    messages = relationship("AgentMessage", back_populates="investigation", cascade="all, delete-orphan")
    tool_calls = relationship("ToolCall", back_populates="investigation", cascade="all, delete-orphan")
    decisions = relationship("CleaningDecision", back_populates="investigation", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="investigation", cascade="all, delete-orphan")
    reviews = relationship("HumanReview", back_populates="investigation", cascade="all, delete-orphan")
    reports = relationship("InvestigationReport", back_populates="investigation", cascade="all, delete-orphan")


class WorkflowCheckpoint(Base):
    __tablename__ = "workflow_checkpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    state = Column(String(32), nullable=False)
    iteration = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="checkpoints")


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="messages")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id"), nullable=False)
    tool_name = Column(String(128), nullable=False)
    input_hash = Column(String(128), nullable=False)
    inputs = Column(JSON, nullable=True)
    outputs = Column(JSON, nullable=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="tool_calls")


class CleaningDecision(Base):
    __tablename__ = "cleaning_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id"), nullable=False)
    operation = Column(String(128), nullable=False)
    target_columns = Column(JSON, nullable=True)
    reason = Column(Text, nullable=False)
    row_count_delta = Column(Integer, nullable=False, default=0)
    row_indices = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="decisions")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    claim = Column(Text, nullable=False)
    test_name = Column(String(128), nullable=False)
    statistic = Column(String(128), nullable=True)
    p_value = Column(String(128), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="evidence")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    proposal_id = Column(String(128), nullable=False, default="")
    status = Column(String(32), nullable=False, default="pending")  # pending, approved, edited, rejected
    proposal_summary = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=True)
    decision = Column(String(32), nullable=True)  # approve, edit, reject
    reviewer = Column(String(128), nullable=True)
    action = Column(String(32), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="reviews")


class InvestigationReport(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    kind = Column(String(32), nullable=False)  # json, markdown, html, pdf
    path = Column(String(512), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    investigation = relationship("Investigation", back_populates="reports")


class Watch(Base):
    __tablename__ = "watches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    schedule = Column(String(128), nullable=False, default="@daily")
    drift_threshold = Column(String(32), nullable=False, default="0.10")
    enabled = Column(Boolean, nullable=False, default=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
