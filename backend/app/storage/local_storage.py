from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    def save_original(self, dataset_id: str, filename: str, content: bytes) -> tuple[Path, str]:
        ...

    def save_version(self, dataset_id: str, version_id: str, filename: str, content: bytes) -> tuple[Path, str]:
        ...

    def open(self, path: str):
        ...

    def path_for(self, dataset_id: str, version_id: str | None = None, *, filename: str | None = None) -> Path:
        ...


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _unique_path(self, directory: Path, filename: str) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        candidate = directory / filename
        if not candidate.exists():
            return candidate
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        index = 1
        while True:
            candidate = directory / f"{stem}_{index}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    def save_original(self, dataset_id: str, filename: str, content: bytes) -> tuple[Path, str]:
        dataset_dir = self.root / "datasets" / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        destination = self._unique_path(dataset_dir, filename)
        destination.write_bytes(content)
        return destination, sha256(content).hexdigest()

    def save_uploaded_dataset(self, dataset_id: str, filename: str, content: bytes) -> tuple[Path, str]:
        return self.save_original(dataset_id, filename, content)

    def save_version(self, dataset_id: str, version_id: str, filename: str, content: bytes) -> tuple[Path, str]:
        version_dir = self.root / "datasets" / dataset_id / "versions" / version_id
        version_dir.mkdir(parents=True, exist_ok=True)
        destination = self._unique_path(version_dir, filename)
        destination.write_bytes(content)
        return destination, sha256(content).hexdigest()

    def save_cleaned_version(self, dataset_id: str, version_id: str, filename: str, content: bytes) -> Path:
        path, _ = self.save_version(dataset_id, version_id, filename, content)
        return path

    def open(self, path: str):
        return Path(path).open("rb")

    def path_for(self, dataset_id: str, version_id: str | None = None, *, filename: str | None = None) -> Path:
        if version_id:
            base = self.root / "datasets" / dataset_id / "versions" / version_id
        else:
            base = self.root / "datasets" / dataset_id
        if filename:
            return base / filename
        return base
