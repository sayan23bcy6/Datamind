from __future__ import annotations

from celery import Celery

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.db.models.investigation import Watch
from app.services.investigation_service import InvestigationService
from app.services.watch_service import WatchService

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
    broker_connection_retry_on_startup=True,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-scheduled-watches": {
            "task": "datamind.check_all_watches",
            "schedule": 60.0,
        },
    },
)


@celery_app.task(name="datamind.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="datamind.run_investigation")
def run_investigation(investigation_id: str):
    db = SessionLocal()
    try:
        service = InvestigationService(db)
        investigation = service.run(investigation_id)
        return {
            "investigation_id": str(investigation.id),
            "status": investigation.status,
        }
    except Exception as exc:
        try:
            inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
            if inv and inv.status != "failed":
                inv.status = "failed"
                inv.state = "FAILED"
                inv.error = str(exc)
                inv.finished_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


@celery_app.task(name="datamind.run_watch_check")
def run_watch_check(watch_id: str):
    db = SessionLocal()
    try:
        service = WatchService(db)
        return service.check_watch(watch_id)
    finally:
        db.close()


@celery_app.task(name="datamind.check_all_watches")
def check_all_watches():
    db = SessionLocal()
    try:
        watches = db.query(Watch).filter(Watch.enabled == True).all()
        for watch in watches:
            run_watch_check.delay(watch.id)
        return len(watches)
    finally:
        db.close()
