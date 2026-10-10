from datetime import datetime

from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    id: str
    name: str
    created_at: datetime


class DatasetVersionSummary(BaseModel):
    id: str
    dataset_id: str
    version_number: int
    source_name: str
    stored_path: str
    file_size_bytes: int | None = None
    sha256: str
    row_count: int
    column_count: int
    is_original: bool = False
    created_at: datetime
    parent_version_id: str | None = None


class UploadResult(BaseModel):
    dataset_id: str
    version_id: str
    dataset_name: str
    row_count: int = Field(..., ge=0)
    column_count: int = Field(..., ge=0)
    file_name: str
    stored_path: str
    sha256: str
