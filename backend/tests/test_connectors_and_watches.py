from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from app.connectors.base import DataSource, FileSource, PostgresSource
from app.core.database import SessionLocal
from app.db.repositories.dataset_repository import DatasetRepository
from app.services.watch_service import WatchService


def test_datasource_abstract_contract() -> None:
    with pytest.raises(TypeError):
        DataSource()  # Cannot instantiate abstract class


def test_filesource_and_postgressource(tmp_path: Path) -> None:
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

    source = FileSource(csv_file)
    assert source.name == "sample.csv"
    df = source.load()
    assert len(df) == 2
    fp = source.fingerprint()
    assert len(fp) == 64

    # PostgresSource roadmap seam raises NotImplementedError
    pg = PostgresSource("postgresql://user:pass@localhost/db", "customers")
    assert "customers" in pg.name
    with pytest.raises(NotImplementedError):
        pg.load()
    with pytest.raises(NotImplementedError):
        pg.fingerprint()


def test_watch_drift_above_and_below_threshold(tmp_path: Path) -> None:
    db = SessionLocal()
    try:
        d_repo = DatasetRepository(db)
        dataset = d_repo.create_dataset("Watch Test Dataset")

        # Baseline Version 1
        df_v1 = pd.DataFrame({"score": [10.0, 12.0, 11.0, 13.0, 12.5, 10.5, 11.5, 12.0]})
        path_v1 = tmp_path / "v1.csv"
        df_v1.to_csv(path_v1, index=False)
        v1 = d_repo.create_version(
            dataset.id,
            source_name="v1.csv",
            stored_path=str(path_v1),
            file_size_bytes=len(path_v1.read_bytes()),
            sha256="sha-v1",
            row_count=len(df_v1),
            column_count=1,
            is_original=True,
        )

        # Version 2 with negligible / low drift
        df_v2 = pd.DataFrame({"score": [10.1, 12.1, 11.1, 12.9, 12.4, 10.6, 11.4, 12.1]})
        path_v2 = tmp_path / "v2.csv"
        df_v2.to_csv(path_v2, index=False)
        v2 = d_repo.create_version(
            dataset.id,
            source_name="v2.csv",
            stored_path=str(path_v2),
            file_size_bytes=len(path_v2.read_bytes()),
            sha256="sha-v2",
            row_count=len(df_v2),
            column_count=1,
            is_original=False,
            parent_version_id=v1.id,
        )

        watch_service = WatchService(db)
        # Watch with higher drift threshold (0.80) -> drift below threshold
        watch = watch_service.create_watch(dataset.id, drift_threshold="0.80", enabled=True)
        res_below = watch_service.check_watch(watch.id)
        assert res_below["status"] == "drift_within_threshold"
        assert "investigation_id" not in res_below

        # Now test when drift exceeds threshold (drift_threshold="0.01")
        watch.drift_threshold = "0.01"
        db.commit()

        # Version 3 with massive distribution shift (e.g. scores from 100 to 500)
        df_v3 = pd.DataFrame({"score": [200.0, 350.0, 420.0, 500.0, 310.0, 450.0, 290.0, 380.0]})
        path_v3 = tmp_path / "v3.csv"
        df_v3.to_csv(path_v3, index=False)
        v3 = d_repo.create_version(
            dataset.id,
            source_name="v3.csv",
            stored_path=str(path_v3),
            file_size_bytes=len(path_v3.read_bytes()),
            sha256="sha-v3",
            row_count=len(df_v3),
            column_count=1,
            is_original=False,
            parent_version_id=v2.id,
        )

        from unittest.mock import patch

        with patch("app.celery_app.run_investigation.delay") as mock_delay:
            res_above = watch_service.check_watch(watch.id)
            assert res_above["status"] == "investigation_created"
            assert "investigation_id" in res_above
            mock_delay.assert_called_once()
    finally:
        db.close()
