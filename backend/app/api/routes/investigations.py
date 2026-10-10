from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.celery_app import run_investigation
from app.core.database import get_db
from app.db.models.investigation import HumanReview
from app.db.repositories.dataset_repository import DatasetRepository
from app.db.repositories.investigation_repository import InvestigationRepository
from app.services.investigation_service import InvestigationService

router = APIRouter(prefix="/api/v1", tags=["investigations"])


@router.post("/datasets/{dataset_id}/investigations")
def create_investigation(dataset_id: str, db: Session = Depends(get_db)):
    repository = DatasetRepository(db)
    latest = repository.get_latest_version_for_dataset(dataset_id)
    if latest is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    service = InvestigationService(db)
    investigation = service.create_investigation(dataset_id, latest.id)
    try:
        run_investigation.delay(investigation.id)
    except Exception:
        service.run(investigation.id)
    else:
        service.run(investigation.id)
    investigation = service.repo.get_investigation(investigation.id)
    return {"investigation_id": investigation.id, "status": investigation.status, "state": investigation.state}


@router.get("/investigations/{investigation_id}")
def get_investigation(investigation_id: str, db: Session = Depends(get_db)):
    investigation = InvestigationRepository(db).get_investigation(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return {
        "id": investigation.id,
        "dataset_id": investigation.dataset_id,
        "dataset_version_id": investigation.dataset_version_id,
        "status": investigation.status,
        "state": investigation.state,
        "iteration": investigation.iteration,
        "cost_used": investigation.cost_used,
        "cost_budget": investigation.cost_budget,
    }


@router.get("/investigations/{investigation_id}/events")
def get_investigation_events(investigation_id: str, db: Session = Depends(get_db)):
    repository = InvestigationRepository(db)

    def event_stream():
        checkpoints = repository.list_checkpoints(investigation_id)
        messages = repository.list_messages(investigation_id)
        events = []
        for checkpoint in checkpoints:
            events.append({"type": "checkpoint", "payload": checkpoint.payload, "state": checkpoint.state, "iteration": checkpoint.iteration})
        for message in messages:
            events.append({"type": "message", "role": message.role, "content": message.content})
        if not events:
            events.append({"type": "heartbeat", "message": "Waiting for the investigation to begin."})
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: {\"type\": \"heartbeat\", \"message\": \"still running\"}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/investigations/{investigation_id}/report")
def get_investigation_report(investigation_id: str, format: str = "json", db: Session = Depends(get_db)):
    repo = InvestigationRepository(db)
    report = repo.get_reports(investigation_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    chosen = next((item for item in report if item.kind == format), None)
    if chosen is None:
        chosen = report[0]
    return {"investigation_id": investigation_id, "format": format, "path": chosen.path}


@router.get("/investigations/{investigation_id}/reviews")
def get_reviews(investigation_id: str, db: Session = Depends(get_db)):
    reviews = db.query(HumanReview).filter(HumanReview.investigation_id == investigation_id).order_by(HumanReview.created_at.asc()).all()
    return [{"id": review.id, "action": review.action, "payload": review.payload, "reviewer": review.reviewer} for review in reviews]


@router.post("/reviews/{review_id}/decision")
def decision(review_id: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    repo = InvestigationRepository(db)
    investigation_id = payload.get("investigation_id")
    action = payload.get("action", "approve")
    if investigation_id:
        repo.add_review(investigation_id, action, payload)
    return {"review_id": review_id, "status": "ok"}
