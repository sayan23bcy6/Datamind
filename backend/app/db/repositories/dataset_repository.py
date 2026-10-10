from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.dataset import Dataset, DatasetVersion


class DatasetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_dataset(self, name: str) -> Dataset:
        dataset = Dataset(name=name)
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def list_datasets(self) -> List[Dataset]:
        return self.db.query(Dataset).order_by(Dataset.created_at.desc()).all()

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        return self.db.query(Dataset).filter(Dataset.id == dataset_id).first()

    def get_versions_for_dataset(self, dataset_id: str) -> List[DatasetVersion]:
        return (
            self.db.query(DatasetVersion)
            .filter(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.desc())
            .all()
        )

    def create_version(
        self,
        dataset_id: str,
        *,
        source_name: str,
        stored_path: str,
        file_size_bytes: int,
        sha256: str,
        row_count: int,
        column_count: int,
        is_original: bool,
        parent_version_id: str | None = None,
    ) -> DatasetVersion:
        version_number = (
            self.db.query(func.max(DatasetVersion.version_number))
            .filter(DatasetVersion.dataset_id == dataset_id)
            .scalar()
            or 0
        ) + 1

        version = DatasetVersion(
            dataset_id=dataset_id,
            version_number=version_number,
            source_name=source_name,
            stored_path=stored_path,
            file_size_bytes=file_size_bytes,
            sha256=sha256,
            row_count=row_count,
            column_count=column_count,
            is_original=is_original,
            parent_version_id=parent_version_id,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version
