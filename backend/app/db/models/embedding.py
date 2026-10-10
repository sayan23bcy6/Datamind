from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, String

from app.core.config import get_settings
from app.core.database import Base

_settings = get_settings()


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    kind = Column(String(64), nullable=False)  # "column_profile" or "investigation_summary"
    ref_id = Column(String(255), nullable=False, index=True)
    model = Column(String(128), nullable=False)
    vector = Column(Vector(_settings.embedding_dimension), nullable=True)
    text_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
