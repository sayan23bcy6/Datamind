import hashlib
import io
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.db.repositories.dataset_repository import DatasetRepository
from app.schemas.dataset import UploadResult
from app.services.demo_dataset import generate_demo_dataset
from app.storage.local_storage import LocalStorage

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])
settings = get_settings()
storage = LocalStorage(settings.storage_root)


def _read_dataset_frame(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    if file_name.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_bytes))
    if file_name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_bytes))
    raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported for upload.")


@router.get("")
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


@router.get("/{dataset_id}/versions")
def list_versions(dataset_id: str, db: Session = Depends(get_db)):
    repository = DatasetRepository(db)
    dataset = repository.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return [
        {
            "id": version.id,
            "dataset_id": version.dataset_id,
            "version_number": version.version_number,
            "source_name": version.source_name,
            "stored_path": version.stored_path,
            "file_size_bytes": version.file_size_bytes,
            "sha256": version.sha256,
            "row_count": version.row_count,
            "column_count": version.column_count,
            "is_original": version.is_original,
            "created_at": version.created_at.isoformat(),
            "parent_version_id": version.parent_version_id,
        }
        for version in repository.get_versions_for_dataset(dataset_id)
    ]


@router.post("/upload", response_model=UploadResult)
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_name: str = Form(default=""),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    frame = _read_dataset_frame(file.filename or "uploaded.csv", file_bytes)
    repository = DatasetRepository(db)
    dataset = repository.create_dataset(dataset_name or file.filename or "dataset")

    destination, digest = storage.save_uploaded_dataset(dataset.id, file.filename or "uploaded.csv", file_bytes)
    version = repository.create_version(
        dataset.id,
        source_name=file.filename or "uploaded.csv",
        stored_path=str(destination),
        file_size_bytes=len(file_bytes),
        sha256=digest,
        row_count=int(frame.shape[0]),
        column_count=int(frame.shape[1]),
        is_original=True,
    )

    return UploadResult(
        dataset_id=dataset.id,
        version_id=version.id,
        dataset_name=dataset.name,
        row_count=int(frame.shape[0]),
        column_count=int(frame.shape[1]),
        file_name=file.filename or "uploaded.csv",
        stored_path=str(destination),
        sha256=digest,
    )


@router.post("/demo")
def create_demo_dataset(db: Session = Depends(get_db)):
    output_dir = Path(settings.storage_root) / "demo"
    metadata = generate_demo_dataset(output_dir=output_dir, name="demo_customer_data.csv")

    repository = DatasetRepository(db)
    dataset = repository.create_dataset("Demo customer dataset")
    file_bytes = (Path(metadata["path"]).read_bytes())
    digest = hashlib.sha256(file_bytes).hexdigest()
    version = repository.create_version(
        dataset.id,
        source_name="demo_customer_data.csv",
        stored_path=str(Path(metadata["path"])),
        file_size_bytes=len(file_bytes),
        sha256=digest,
        row_count=int(metadata["rows"]),
        column_count=int(metadata["columns"]),
        is_original=True,
    )

    return {
        "dataset_id": dataset.id,
        "version_id": version.id,
        "message": "Demo dataset created successfully.",
        "metadata": metadata,
    }
