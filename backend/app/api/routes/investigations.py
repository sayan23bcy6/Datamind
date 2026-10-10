from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
import pandas as pd
from sqlalchemy.orm import Session

from app.celery_app import run_investigation
from app.connectors.base import FileSource
from app.core.config import get_settings
from app.core.database import get_db
from app.db.models.dataset import DatasetVersion
from app.db.models.investigation import HumanReview, Investigation, InvestigationReport
from app.db.repositories.dataset_repository import DatasetRepository
from app.db.repositories.investigation_repository import InvestigationRepository
from app.schemas.investigation import (
    ColumnDistribution,
    DiffItem,
    EvidenceItem,
    InvestigationResponse,
    ProposalItemResponse,
    ReviewDecisionRequest,
    ReviewItem,
    WatchCreateRequest,
    WatchResponse,
)
from app.services.investigation_service import InvestigationService
from app.services.watch_service import WatchService
from app.tools.detectors import compute_column_distributions, deduplicate

router = APIRouter(prefix="/api/v1", tags=["investigations"])
settings = get_settings()


@router.post("/datasets/{dataset_id}/investigations")
def create_investigation(dataset_id: str, db: Session = Depends(get_db)):
    repo = DatasetRepository(db)
    latest = repo.get_latest_version_for_dataset(dataset_id)
    if latest is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    service = InvestigationService(db)
    investigation = service.create_investigation(dataset_id, latest.id)

    # Enqueue investigation Celery task
    try:
        run_investigation.delay(investigation.id)
    except Exception:
        # Fallback to in-process execution if Celery broker is unavailable
        service.run(investigation.id)

    refreshed = service.repo.get_investigation(investigation.id)
    return {
        "investigation_id": refreshed.id,
        "status": refreshed.status,
    }


@router.get("/investigations/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(investigation_id: str, db: Session = Depends(get_db)):
    repo = InvestigationRepository(db)
    inv = repo.get_investigation(investigation_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return InvestigationResponse(
        investigation_id=inv.id,
        status=inv.status,
        state=inv.state,
        iteration=inv.iteration,
        max_iterations=inv.max_iterations,
        cost_used=inv.cost_used,
        cost_budget=inv.cost_budget,
        dataset_version_id=inv.dataset_version_id,
        output_version_id=inv.output_version_id,
        error=inv.error,
    )


@router.get("/investigations/{investigation_id}/proposals")
def get_investigation_proposals(investigation_id: str, db: Session = Depends(get_db)):
    repo = InvestigationRepository(db)
    inv = repo.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    checkpoints = repo.list_checkpoints(investigation_id)
    items: list[dict[str, Any]] = []

    for cp in checkpoints:
        payload = cp.payload or {}
        # Proposals
        if "proposals" in payload and isinstance(payload["proposals"], list):
            for p in payload["proposals"]:
                items.append({
                    "type": "proposal",
                    "iteration": cp.iteration,
                    "proposal_id": p.get("proposal_id", f"prop-{cp.iteration}"),
                    "operation": p.get("operation"),
                    "target_columns": p.get("target_columns", []),
                    "parameters": p.get("parameters", {}),
                    "rationale": p.get("rationale", ""),
                    "confidence": p.get("confidence", "medium"),
                    "confidence_basis": p.get("confidence_basis", ""),
                })
        # Verdicts
        if "verdicts" in payload and isinstance(payload["verdicts"], list):
            for v in payload["verdicts"]:
                items.append({
                    "type": "verdict",
                    "proposal_id": v.get("proposal_id", f"prop-{cp.iteration}"),
                    "verdict": v.get("verdict"),
                    "reasons": v.get("reasons", []),
                    "unsupported_assumptions": v.get("unsupported_assumptions", []),
                    "created_at": v.get("created_at") or cp.created_at.isoformat(),
                })

    return items


@router.get("/investigations/{investigation_id}/diff", response_model=list[DiffItem])
def get_investigation_diff(investigation_id: str, db: Session = Depends(get_db)):
    repo = InvestigationRepository(db)
    inv = repo.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    orig_ver = repo.get_dataset_version(inv.dataset_version_id)
    if not orig_ver or not inv.output_version_id:
        return []

    cleaned_ver = repo.get_dataset_version(inv.output_version_id)
    if not cleaned_ver:
        return []

    orig_df = FileSource(orig_ver.stored_path).load()
    cleaned_df = FileSource(cleaned_ver.stored_path).load()

    diffs: list[DiffItem] = []

    # Detect removed duplicate rows
    dup_mask = orig_df.duplicated(keep="first")
    for orig_idx, is_dup in enumerate(dup_mask.tolist()):
        if is_dup:
            diffs.append(
                DiffItem(
                    column=None,
                    row_index=None,
                    original_row_index=orig_idx,
                    change_type="removed",
                    original_value=orig_df.iloc[orig_idx].to_dict(),
                    new_value=None,
                    rule="deduplicate",
                    confidence="high",
                    confidence_basis="Exact duplicate row removed",
                )
            )

    # Detect modified cells across common columns
    common_cols = [c for c in orig_df.columns if c in cleaned_df.columns]
    min_rows = min(len(orig_df), len(cleaned_df))
    for col in common_cols:
        orig_s = orig_df[col].astype(str)
        clean_s = cleaned_df[col].astype(str)
        for r_idx in range(min_rows):
            o_val = orig_s.iloc[r_idx]
            c_val = clean_s.iloc[r_idx]
            if o_val != c_val and not (pd.isna(orig_df[col].iloc[r_idx]) and pd.isna(cleaned_df[col].iloc[r_idx])):
                diffs.append(
                    DiffItem(
                        column=col,
                        row_index=r_idx,
                        original_row_index=r_idx,
                        change_type="modified",
                        original_value=o_val,
                        new_value=c_val,
                        rule="standardize_format",
                        confidence="high",
                        confidence_basis="Format normalized to canonical representation",
                    )
                )

    return diffs


@router.get("/investigations/{investigation_id}/distributions", response_model=list[ColumnDistribution])
def get_investigation_distributions(investigation_id: str, db: Session = Depends(get_db)):
    repo = InvestigationRepository(db)
    inv = repo.get_investigation(investigation_id)
    if not inv or not inv.output_version_id:
        return []

    orig_ver = repo.get_dataset_version(inv.dataset_version_id)
    cleaned_ver = repo.get_dataset_version(inv.output_version_id)
    if not orig_ver or not cleaned_ver:
        return []

    orig_df = FileSource(orig_ver.stored_path).load()
    cleaned_df = FileSource(cleaned_ver.stored_path).load()

    numeric_cols = [
        col for col in orig_df.columns
        if col in cleaned_df.columns and (
            pd.api.types.is_numeric_dtype(orig_df[col]) or
            pd.to_numeric(orig_df[col].astype(str).str.replace(r"[\$,]", "", regex=True), errors="coerce").notna().any()
        )
    ]

    results = compute_column_distributions(orig_df, cleaned_df, numeric_cols)
    return [ColumnDistribution.model_validate(r) for r in results]


@router.get("/investigations/{investigation_id}/evidence", response_model=list[EvidenceItem])
def get_investigation_evidence(investigation_id: str, db: Session = Depends(get_db)):
    repo = InvestigationRepository(db)
    evidence_rows = repo.list_evidence(investigation_id)
    return [
        EvidenceItem(
            evidence_id=e.id,
            claim=e.claim,
            test_name=e.test_name,
            statistic=e.statistic,
            p_value=e.p_value,
            details=e.details,
        )
        for e in evidence_rows
    ]


@router.get("/investigations/{investigation_id}/report")
def get_investigation_report(
    investigation_id: str,
    format: str = Query(default="json", pattern="^(json|markdown|html|pdf)$"),
    db: Session = Depends(get_db),
):
    repo = InvestigationRepository(db)
    reports = repo.get_reports(investigation_id)
    if not reports:
        raise HTTPException(status_code=404, detail="Report not found")

    rep = next((r for r in reports if r.kind == format), None)
    if not rep or not Path(rep.path).exists():
        raise HTTPException(status_code=404, detail=f"Report format '{format}' not found")

    media_map = {
        "json": "application/json",
        "markdown": "text/markdown",
        "html": "text/html",
        "pdf": "application/pdf",
    }
    return FileResponse(
        path=rep.path,
        media_type=media_map.get(format, "application/octet-stream"),
        filename=Path(rep.path).name,
    )


@router.get("/investigations/{investigation_id}/audit")
def get_investigation_audit(investigation_id: str, db: Session = Depends(get_db)):
    repo = InvestigationRepository(db)
    inv = repo.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    audit_path = Path(settings.storage_root) / "reports" / investigation_id / "audit.json"
    if audit_path.exists():
        return json.loads(audit_path.read_text(encoding="utf-8"))

    # Fallback to generating from database
    checkpoints = repo.list_checkpoints(investigation_id)
    messages = repo.list_messages(investigation_id)
    tool_calls = repo.list_tool_calls(investigation_id)
    decisions = repo.list_decisions(investigation_id)

    trail = []
    for cp in checkpoints:
        trail.append({"type": "state_transition", "state": cp.state, "iteration": cp.iteration, "payload": cp.payload, "timestamp": cp.created_at.isoformat()})
    for m in messages:
        trail.append({"type": "agent_message", "role": m.role, "content": m.content, "timestamp": m.created_at.isoformat()})
    for tc in tool_calls:
        trail.append({"type": "tool_call", "tool": tc.tool_name, "duration_ms": tc.duration_ms, "timestamp": tc.created_at.isoformat()})
    for d in decisions:
        trail.append({"type": "cleaning_decision", "operation": d.operation, "reason": d.reason, "delta": d.row_count_delta, "timestamp": d.created_at.isoformat()})
    trail.sort(key=lambda x: x["timestamp"])
    return {"investigation_id": investigation_id, "audit_trail": trail}


@router.get("/investigations/{investigation_id}/events")
async def get_investigation_events(
    investigation_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    db: Session = Depends(get_db),
):
    repo = InvestigationRepository(db)
    inv = repo.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    start_id = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0

    async def event_generator() -> AsyncGenerator[str, None]:
        current_seq = start_id
        # 1. Yield historical checkpoints and events
        checkpoints = repo.list_checkpoints(investigation_id)
        for cp in checkpoints:
            current_seq += 1
            event_payload = {
                "from": "PREV",
                "to": cp.state,
                "iteration": cp.iteration,
                "timestamp": cp.created_at.isoformat(),
            }
            yield f"id: {current_seq}\nevent: state_changed\ndata: {json.dumps(event_payload)}\n\n"

        # Check if already completed or failed
        refreshed = repo.get_investigation(investigation_id)
        if refreshed.status == "completed":
            current_seq += 1
            yield f"id: {current_seq}\nevent: completed\ndata: {{\"status\": \"completed\", \"output_version_id\": \"{refreshed.output_version_id}\"}}\n\n"
            return
        elif refreshed.status in ("failed", "partial"):
            current_seq += 1
            yield f"id: {current_seq}\nevent: failed\ndata: {{\"status\": \"{refreshed.status}\", \"error\": \"{refreshed.error}\"}}\n\n"
            return

        # 2. Live polling loop with 15-second heartbeat comment
        last_heartbeat = time.time()
        while True:
            if await request.is_disconnected():
                break

            await asyncio.sleep(1.0)
            now = time.time()
            if now - last_heartbeat >= 15.0:
                yield ": heartbeat\n\n"
                last_heartbeat = now

            inv_live = repo.get_investigation(investigation_id)
            if not inv_live:
                break

            if inv_live.status == "completed":
                current_seq += 1
                yield f"id: {current_seq}\nevent: completed\ndata: {{\"status\": \"completed\", \"output_version_id\": \"{inv_live.output_version_id}\"}}\n\n"
                break
            elif inv_live.status in ("failed", "partial"):
                current_seq += 1
                yield f"id: {current_seq}\nevent: failed\ndata: {{\"status\": \"{inv_live.status}\", \"error\": \"{inv_live.error}\"}}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# -----------------------------------------------------------------------------
# Reviews Endpoints
# -----------------------------------------------------------------------------
@router.get("/reviews", response_model=list[ReviewItem])
def list_pending_reviews(
    status: str = Query(default="pending"),
    db: Session = Depends(get_db),
):
    repo = InvestigationRepository(db)
    if status == "pending":
        reviews = repo.list_pending_reviews()
    else:
        reviews = db.query(HumanReview).filter(HumanReview.status == status).all()

    return [
        ReviewItem(
            review_id=r.id,
            investigation_id=r.investigation_id,
            proposal_id=r.proposal_id,
            status=r.status,
            proposal_summary=r.proposal_summary,
            parameters=r.parameters,
        )
        for r in reviews
    ]


@router.post("/reviews/{review_id}/decision")
def review_decision(
    review_id: str,
    req: ReviewDecisionRequest,
    db: Session = Depends(get_db),
):
    repo = InvestigationRepository(db)
    review = repo.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.decision = req.decision
    review.status = f"{req.decision}d" if req.decision != "edit" else "edited"
    if req.parameters:
        review.parameters = req.parameters
    db.commit()

    # Resume the investigation
    service = InvestigationService(db)
    inv = repo.get_investigation(review.investigation_id)
    if inv and inv.status == "awaiting_human":
        inv.status = "running"
        db.commit()
        try:
            run_investigation.delay(inv.id)
        except Exception:
            service.run(inv.id)

    return {"review_id": review_id, "status": review.status, "decision": req.decision}


# -----------------------------------------------------------------------------
# Watches Endpoints
# -----------------------------------------------------------------------------
@router.post("/watches", response_model=WatchResponse)
def create_watch(req: WatchCreateRequest, db: Session = Depends(get_db)):
    service = WatchService(db)
    watch = service.create_watch(
        dataset_id=req.dataset_id,
        schedule=req.schedule,
        drift_threshold=req.drift_threshold,
        enabled=req.enabled,
    )
    return WatchResponse(
        id=watch.id,
        dataset_id=watch.dataset_id,
        schedule=watch.schedule,
        drift_threshold=watch.drift_threshold,
        enabled=watch.enabled,
        last_checked_at=watch.last_checked_at.isoformat() if watch.last_checked_at else None,
        created_at=watch.created_at.isoformat(),
    )


@router.get("/watches", response_model=list[WatchResponse])
def list_watches(db: Session = Depends(get_db)):
    service = WatchService(db)
    watches = service.list_watches()
    return [
        WatchResponse(
            id=w.id,
            dataset_id=w.dataset_id,
            schedule=w.schedule,
            drift_threshold=w.drift_threshold,
            enabled=w.enabled,
            last_checked_at=w.last_checked_at.isoformat() if w.last_checked_at else None,
            created_at=w.created_at.isoformat(),
        )
        for w in watches
    ]


@router.delete("/watches/{watch_id}")
def delete_watch(watch_id: str, db: Session = Depends(get_db)):
    service = WatchService(db)
    success = service.delete_watch(watch_id)
    if not success:
        raise HTTPException(status_code=404, detail="Watch not found")
    return {"status": "deleted", "watch_id": watch_id}
