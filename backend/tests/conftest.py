from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, engine
import app.db.models  # noqa: F401


@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    # Ensure test database schema exists for pytest runs
    Base.metadata.create_all(bind=engine)
    yield
