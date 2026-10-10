from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DatasetItem(BaseModel):
    id: str
    name: str
    created_at: str


class VersionItem(BaseModel):
    id: str
    version_number: int
    parent_version_id: Optional[str] = None
    source_name: str
    row_count: int
    column_count: int
    file_size_bytes: Optional[int] = None
    sha256: str
    is_original: bool
    created_at: str


class UploadResponse(BaseModel):
    dataset_id: str
    version_id: str
    dataset_name: str
    file_name: str
    row_count: int
    column_count: int
    sha256: str


class DemoDatasetResponse(BaseModel):
    dataset_id: str
    version_id: str
    message: str
    created: bool


class ColumnProfileItem(BaseModel):
    name: str
    dtype: str
    missing_count: int
    missing_rate: float
    unique_count: int
    sample_values: list[Any]


class DimensionScores(BaseModel):
    completeness: float
    uniqueness: float
    consistency: float
    validity: float
    accuracy: float
    overall: float


class ProfileResponse(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnProfileItem]
    dimensions: DimensionScores
