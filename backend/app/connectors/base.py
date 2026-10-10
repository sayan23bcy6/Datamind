from abc import ABC, abstractmethod
import hashlib
from pathlib import Path
from typing import Any

import pandas as pd


class DataSource(ABC):
    """Abstract base class for dataset connectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the data source."""
        pass

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Load and return dataset as a pandas DataFrame."""
        pass

    @abstractmethod
    def fingerprint(self) -> str:
        """Compute and return a deterministic SHA-256 fingerprint of the data."""
        pass


class FileSource(DataSource):
    """Fully implemented file-based data source supporting CSV and Excel files."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    @property
    def name(self) -> str:
        return self.file_path.name

    def load(self) -> pd.DataFrame:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Source file does not exist: {self.file_path}")
        suffix = self.file_path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(self.file_path)
        return pd.read_csv(self.file_path)

    def fingerprint(self) -> str:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Source file does not exist: {self.file_path}")
        return hashlib.sha256(self.file_path.read_bytes()).hexdigest()


class PostgresSource(DataSource):
    """Roadmap seam for PostgreSQL table and query ingestion.
    Contract:
      - Initialize with connection_uri (str) and table_name (str) or sql_query (str).
      - load() connects via SQLAlchemy/psycopg, executing the query and returning DataFrame.
      - fingerprint() queries table row count + max updated timestamp or sha256 checksum.
    """

    def __init__(self, connection_uri: str, table_or_query: str):
        self.connection_uri = connection_uri
        self.table_or_query = table_or_query

    @property
    def name(self) -> str:
        return f"postgres:{self.table_or_query}"

    def load(self) -> pd.DataFrame:
        raise NotImplementedError(
            "PostgresSource connector is a roadmap seam and has not been implemented yet. "
            "Please use FileSource for active pipelines."
        )

    def fingerprint(self) -> str:
        raise NotImplementedError(
            "PostgresSource fingerprinting is a roadmap seam and has not been implemented yet."
        )
