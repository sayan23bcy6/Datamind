from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.db.models.dataset import Dataset, DatasetVersion
from app.db.repositories.dataset_repository import DatasetRepository
from app.schemas.dataset import (
    DemoDatasetResponse,
    ProfileResponse,
    UploadResponse,
)
from app.services.demo_dataset import generate_demo_dataset
from app.storage.local_storage import LocalStorage
from app.tools.detectors import profile_dataset

router = APIRouter(prefix="/api/v1", tags=["datasets"])
settings = get_settings()
storage = LocalStorage(settings.storage_root)


def _read_dataset_frame(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    ext = Path(file_name).suffix.lower()
    if ext == ".csv":
        return pd.read_csv(io.BytesIO(file_bytes))
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(io.BytesIO(file_bytes))
    raise HTTPException(
        status_code=400,
        detail="Only .csv, .xlsx, and .xls files are supported.",
    )


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    repository = DatasetRepository(db)
    datasets = repository.list_datasets()
    return [
        {
            "id": dataset.id,
            "name": dataset.name,
            "created_at": dataset.created_at.isoformat(),
        }
        for dataset in datasets
    ]


@router.get("/datasets/{dataset_id}/versions")
def list_versions(dataset_id: str, db: Session = Depends(get_db)):
    repository = DatasetRepository(db)
    dataset = repository.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return [
        {
            "id": version.id,
            "version_number": version.version_number,
            "parent_version_id": version.parent_version_id,
            "source_name": version.source_name,
            "row_count": version.row_count,
            "column_count": version.column_count,
            "file_size_bytes": version.file_size_bytes,
            "sha256": version.sha256,
            "is_original": version.is_original,
            "created_at": version.created_at.isoformat(),
        }
        for version in repository.get_versions_for_dataset(dataset_id)
    ]


@router.post("/datasets/upload", response_model=UploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_name: str = Form(default=""),
    db: Session = Depends(get_db),
):
    filename = file.filename or "upload.csv"
    ext = Path(filename).suffix.lower()
    if ext not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed extensions: .csv, .xlsx, .xls",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    frame = _read_dataset_frame(filename, file_bytes)
    repository = DatasetRepository(db)
    name = dataset_name.strip() if dataset_name and dataset_name.strip() else Path(filename).stem
    dataset = repository.create_dataset(name)

    destination, digest = storage.save_uploaded_dataset(dataset.id, filename, file_bytes)
    version = repository.create_version(
        dataset.id,
        source_name=filename,
        stored_path=str(destination),
        file_size_bytes=len(file_bytes),
        sha256=digest,
        row_count=int(frame.shape[0]),
        column_count=int(frame.shape[1]),
        is_original=True,
    )

    return UploadResponse(
        dataset_id=dataset.id,
        version_id=version.id,
        dataset_name=dataset.name,
        file_name=filename,
        row_count=int(frame.shape[0]),
        column_count=int(frame.shape[1]),
        sha256=digest,
    )


@router.post("/datasets/demo", response_model=DemoDatasetResponse)
def create_demo_dataset(db: Session = Depends(get_db)):
    output_dir = Path(settings.storage_root) / "demo"
    meta = generate_demo_dataset(output_dir=output_dir, name="demo_customer_data.csv")
    csv_path = Path(meta["path"])
    file_bytes = csv_path.read_bytes()
    digest = hashlib.sha256(file_bytes).hexdigest()

    # Check if a dataset version with the same SHA-256 already exists
    existing = db.query(DatasetVersion).filter(DatasetVersion.sha256 == digest).first()
    if existing:
        return DemoDatasetResponse(
            dataset_id=existing.dataset_id,
            version_id=existing.id,
            message="Existing demo dataset found.",
            created=False,
        )

    repository = DatasetRepository(db)
    dataset = repository.create_dataset("Demo Customer & Transactions Dataset")
    version = repository.create_version(
        dataset.id,
        source_name=csv_path.name,
        stored_path=str(csv_path),
        file_size_bytes=len(file_bytes),
        sha256=digest,
        row_count=int(meta["rows"]),
        column_count=int(meta["columns"]),
        is_original=True,
    )

    return DemoDatasetResponse(
        dataset_id=dataset.id,
        version_id=version.id,
        message="Demo dataset created successfully.",
        created=True,
    )


@router.get("/versions/{version_id}/profile", response_model=ProfileResponse)
def get_version_profile(version_id: str, db: Session = Depends(get_db)):
    version = db.query(DatasetVersion).filter(DatasetVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    file_path = Path(version.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Version file not found on disk")

    if file_path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)

    prof = profile_dataset(df)
    return ProfileResponse(
        row_count=prof["row_count"],
        column_count=prof["column_count"],
        columns=prof["columns"],
        dimensions=prof["dimensions"],
    )


@router.get("/versions/{version_id}/download")
def download_version(version_id: str, db: Session = Depends(get_db)):
    version = db.query(DatasetVersion).filter(DatasetVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    file_path = Path(version.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Version file not found on disk")

    media_type = "text/csv"
    if file_path.suffix.lower() == ".xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif file_path.suffix.lower() == ".xls":
        media_type = "application/vnd.ms-excel"

    return FileResponse(
        path=str(file_path),
        filename=version.source_name,
        media_type=media_type,
    )
