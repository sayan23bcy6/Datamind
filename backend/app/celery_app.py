from __future__ import annotations

from celery import Celery

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.db.models.investigation import Watch
from app.db.repositories.investigation_repository import InvestigationRepository
from app.services.investigation_service import InvestigationService

settings = get_settings()
celery_app = Celery(
    "datamind",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="datamind.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="datamind.run_investigation")
def run_investigation(investigation_id: str):
    db = SessionLocal()
    try:
        service = InvestigationService(db)
        return service.run(investigation_id)
    finally:
        db.close()


@celery_app.task(name="datamind.run_watch_check")
def run_watch_check(watch_id: str):
    db = SessionLocal()
    try:
        repo = InvestigationRepository(db)
        watch = db.query(Watch).filter(Watch.id == watch_id).first()
        return {"status": "ok", "watch_id": watch_id, "enabled": bool(watch.enabled) if watch else False}
    finally:
        db.close()
