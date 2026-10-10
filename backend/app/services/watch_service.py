from __future__ import annotations

from app.db.repositories.investigation_repository import InvestigationRepository


class WatchService:
    def __init__(self, db):
        self.db = db
        self.repo = InvestigationRepository(db)

    def create_watch(self, dataset_id: str, schedule: str = "@daily", drift_threshold: str = "0.10", enabled: bool = True):
        return self.repo.get_or_create_watch(dataset_id, schedule=schedule, drift_threshold=drift_threshold, enabled=enabled)

    def list_watches(self, dataset_id: str | None = None):
        return self.repo.list_watches(dataset_id)
