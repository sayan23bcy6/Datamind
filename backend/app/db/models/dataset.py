from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    source_name = Column(String(255), nullable=False)
    stored_path = Column(String(1024), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(128), nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    column_count = Column(Integer, nullable=False, default=0)
    is_original = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    parent_version_id = Column(String(36), ForeignKey("dataset_versions.id"), nullable=True)

    dataset = relationship("Dataset", back_populates="versions")
    parent = relationship("DatasetVersion", remote_side="DatasetVersion.id", backref="children")
