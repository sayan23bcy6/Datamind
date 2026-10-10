from __future__ import annotations

import os
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from alembic import command
from alembic.config import Config
import sqlalchemy as sa

from app.core.config import get_settings
from app.core.database import Base
from app.agents.providers import GeminiProvider, MockProvider
from app.services.investigation_service import InvestigationService
from app.services.demo_dataset import generate_demo_dataset
from app.db.repositories.dataset_repository import DatasetRepository
from app.db.repositories.investigation_repository import InvestigationRepository


def test_schema_migration_syncs_all_model_columns_on_empty_and_old_database():
    """Verify alembic upgrade head on an empty database AND on an old database (202410100002)

    syncs all missing columns (status, reviewer, action, payload, etc.) to match model metadata.
    """
    root = Path(__file__).resolve().parent.parent.parent
    alembic_ini = str(root / "backend" / "alembic.ini")
    script_loc = str(root / "backend" / "alembic")

    # 1. Test empty database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "empty.db"
        db_url = f"sqlite:///{db_path}"
        os.environ["DATABASE_URL"] = db_url

        cfg = Config(alembic_ini)
        cfg.set_main_option("script_location", script_loc)
        command.upgrade(cfg, "head")

        eng = sa.create_engine(db_url)
        insp = sa.inspect(eng)
        for t_name, table in Base.metadata.tables.items():
            assert insp.has_table(t_name), f"Table {t_name} missing from database"
            live_cols = {c["name"] for c in insp.get_columns(t_name)}
            model_cols = {c.name for c in table.columns}
            missing = model_cols - live_cols
            assert not missing, f"Table {t_name} is missing columns {missing} on empty upgrade"
        eng.dispose()

    # 2. Test old database with missing human_reviews columns at 202410100002
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "old.db"
        db_url = f"sqlite:///{db_path}"
        os.environ["DATABASE_URL"] = db_url

        cfg = Config(alembic_ini)
        cfg.set_main_option("script_location", script_loc)

        # Upgrade to 202410100001
        command.upgrade(cfg, "202410100001")

        # Create pre-existing legacy human_reviews table (which only had id, investigation_id, created_at)
        eng = sa.create_engine(db_url)
        with eng.connect() as conn:
            conn.execute(sa.text("""
                CREATE TABLE human_reviews (
                    id VARCHAR(36) PRIMARY KEY,
                    investigation_id VARCHAR(36) NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """))
            conn.commit()
        eng.dispose()

        # Upgrade to pre-fix 202410100002
        command.upgrade(cfg, "202410100002")
        eng = sa.create_engine(db_url)
        insp = sa.inspect(eng)
        cols_pre_fix = {c["name"] for c in insp.get_columns("human_reviews")}
        # Verify status, reviewer, action, payload were missing before 202410100003
        assert "status" not in cols_pre_fix
        assert "reviewer" not in cols_pre_fix
        eng.dispose()

        # Upgrade to head (runs 202410100003)
        command.upgrade(cfg, "head")
        eng = sa.create_engine(db_url)
        insp = sa.inspect(eng)
        cols_post_fix = {c["name"] for c in insp.get_columns("human_reviews")}
        assert "status" in cols_post_fix
        assert "reviewer" in cols_post_fix
        assert "action" in cols_post_fix
        assert "payload" in cols_post_fix

        # Assert every model column exists on every table
        for t_name, table in Base.metadata.tables.items():
            assert insp.has_table(t_name), f"Table {t_name} missing from database"
            live_cols = {c["name"] for c in insp.get_columns(t_name)}
            model_cols = {c.name for c in table.columns}
            missing = model_cols - live_cols
            assert not missing, f"Table {t_name} is missing columns {missing} on upgraded database"
        eng.dispose()


def test_gemini_provider_embed_uses_config_and_validates_dimension():
    """Unit test: GeminiProvider.embed uses configured model and output_dimensionality,

    and validates vector dimension and handles 404/not supported errors properly.
    """
    settings = get_settings()

    with patch.dict(os.environ, {"GOOGLE_API_KEY": "mock-test-key", "EMBEDDING_MODEL": "gemini-embedding-001", "EMBEDDING_DIMENSION": "768"}):
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            provider = GeminiProvider()

            # 1. Success case: returns 768-dim embeddings
            mock_embedding = MagicMock()
            mock_embedding.values = [0.1] * 768
            mock_result = MagicMock()
            mock_result.embeddings = [mock_embedding]
            mock_client.models.embed_content.return_value = mock_result

            vectors = provider.embed(["sample text to embed"])
            assert len(vectors) == 1
            assert len(vectors[0]) == 768

            # Verify call args used configured model and output_dimensionality
            mock_client.models.embed_content.assert_called_once()
            call_kwargs = mock_client.models.embed_content.call_args.kwargs
            assert call_kwargs["model"] == "gemini-embedding-001"
            assert call_kwargs["config"].output_dimensionality == 768

            # 2. Wrong length vector raises RuntimeError
            wrong_embedding = MagicMock()
            wrong_embedding.values = [0.1] * 512
            mock_result.embeddings = [wrong_embedding]
            with pytest.raises(RuntimeError, match="does not match configured EMBEDDING_DIMENSION"):
                provider.embed(["sample text"])

            # 3. 404 / not supported error raises RuntimeError naming model and EMBEDDING_MODEL
            mock_client.models.embed_content.side_effect = Exception("404 models/gemini-embedding-001 is not found for API version v1beta")
            with pytest.raises(RuntimeError) as exc_info:
                provider.embed(["sample text"])
            err_msg = str(exc_info.value)
            assert "gemini-embedding-001" in err_msg
            assert "EMBEDDING_MODEL" in err_msg


def test_investigation_workflow_marks_failed_on_embedding_error():
    """Unit test: When the embedding call fails during investigation workflow,

    the investigation is marked status == 'failed' with error containing the model name.
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        dataset_repo = DatasetRepository(db)
        inv_repo = InvestigationRepository(db)

        import hashlib

        # Create demo dataset
        meta = generate_demo_dataset()
        csv_path = Path(meta["path"])
        file_bytes = csv_path.read_bytes()
        digest = hashlib.sha256(file_bytes).hexdigest()

        dataset = dataset_repo.create_dataset(name="Embedding Failure Test")
        version = dataset_repo.create_version(
            dataset_id=dataset.id,
            source_name="demo_customer_data.csv",
            stored_path=str(csv_path),
            file_size_bytes=len(file_bytes),
            sha256=digest,
            row_count=meta["rows"],
            column_count=meta["columns"],
            is_original=True,
        )

        service = InvestigationService(db)
        inv = service.create_investigation(dataset.id, version.id)

        # Force provider.embed to fail with a model not found error
        def failing_embed(texts):
            raise RuntimeError(
                "Embedding model 'gemini-embedding-001' was not found or is not supported for embedContent. "
                "Check EMBEDDING_MODEL: 404 Not Found"
            )

        service.provider.embed = failing_embed

        with pytest.raises(RuntimeError):
            service.run(inv.id)

        # Reload investigation from database and assert status and error
        failed_inv = inv_repo.get_investigation(inv.id)
        assert failed_inv is not None
        assert failed_inv.status == "failed"
        assert failed_inv.state == "FAILED"
        assert failed_inv.error is not None
        assert "gemini-embedding-001" in failed_inv.error
    finally:
        db.close()
