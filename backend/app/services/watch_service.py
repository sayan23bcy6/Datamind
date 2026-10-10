from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.connectors.base import FileSource
from app.db.models.dataset import DatasetVersion
from app.db.models.investigation import Watch
from app.db.repositories.dataset_repository import DatasetRepository
from app.db.repositories.investigation_repository import InvestigationRepository
from app.services.investigation_service import InvestigationService
from app.tools.detectors import detect_drift


class WatchService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InvestigationRepository(db)
        self.dataset_repo = DatasetRepository(db)

    def create_watch(
        self,
        dataset_id: str,
        schedule: str = "@daily",
        drift_threshold: str = "0.10",
        enabled: bool = True,
    ) -> Watch:
        watch = Watch(
            dataset_id=dataset_id,
            schedule=schedule,
            drift_threshold=drift_threshold,
            enabled=enabled,
        )
        self.db.add(watch)
        self.db.commit()
        self.db.refresh(watch)
        return watch

    def list_watches(self, dataset_id: str | None = None) -> list[Watch]:
        return self.repo.list_watches(dataset_id)

    def delete_watch(self, watch_id: str) -> bool:
        watch = self.db.query(Watch).filter(Watch.id == watch_id).first()
        if not watch:
            return False
        self.db.delete(watch)
        self.db.commit()
        return True

    def check_watch(self, watch_id: str) -> dict[str, Any]:
        watch = self.db.query(Watch).filter(Watch.id == watch_id).first()
        if not watch:
            return {"status": "not_found", "watch_id": watch_id}
        if not watch.enabled:
            return {"status": "disabled", "watch_id": watch_id}

        versions = (
            self.db.query(DatasetVersion)
            .filter(DatasetVersion.dataset_id == watch.dataset_id)
            .order_by(DatasetVersion.version_number.desc())
            .all()
        )

        watch.last_checked_at = datetime.utcnow()
        self.db.commit()

        if len(versions) < 2:
            return {
                "status": "no_previous_version",
                "watch_id": watch_id,
                "version_count": len(versions),
            }

        latest_version = versions[0]
        previous_version = versions[1]

        latest_df = FileSource(latest_version.stored_path).load()
        previous_df = FileSource(previous_version.stored_path).load()

        drift_results = detect_drift(previous_df, latest_df)
        statistics = [
            float(r["statistic"])
            for r in drift_results.get("results", [])
            if r.get("statistic") is not None
        ]
        max_drift = max(statistics) if statistics else 0.0

        threshold = float(watch.drift_threshold)
        if max_drift > threshold:
            # Drift exceeds threshold -> Create investigation
            inv_service = InvestigationService(self.db)
            investigation = inv_service.create_investigation(
                watch.dataset_id, latest_version.id
            )
            try:
                from app.celery_app import run_investigation

                run_investigation.delay(investigation.id)
            except Exception:
                inv_service.run(investigation.id)

            return {
                "status": "investigation_created",
                "watch_id": watch_id,
                "investigation_id": investigation.id,
                "max_drift": max_drift,
                "drift_threshold": threshold,
            }

        return {
            "status": "drift_within_threshold",
            "watch_id": watch_id,
            "max_drift": max_drift,
            "drift_threshold": threshold,
        }
