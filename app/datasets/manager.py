"""Dataset Manager for file uploads, storage, loading, and metadata persistence."""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import uuid
import pandas as pd

from app.core.config import settings
from app.core.exceptions import (
    CorruptDatasetError,
    DatasetNotFoundError,
    EmptyDatasetError,
)
from app.datasets.profiler import DatasetProfiler
from app.datasets.schemas import DatasetMetadata, DatasetProfile
from app.datasets.validator import DatasetValidator


class DatasetManager:
    """Manages CSV dataset lifecycle: validation, storage, retrieval, and profiling."""

    def __init__(
        self,
        upload_dir: Path | None = None,
        profiler: DatasetProfiler | None = None,
    ) -> None:
        self.upload_dir = upload_dir or settings.UPLOAD_DIR
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir = self.upload_dir / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.upload_dir / "datasets_registry.json"
        self.profiler = profiler or DatasetProfiler()
        self._registry: dict[str, DatasetMetadata] = self._load_registry()

    def _load_registry(self) -> dict[str, DatasetMetadata]:
        """Load persisted dataset metadata registry from disk."""
        if not self.registry_file.exists():
            return {}
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    k: DatasetMetadata(**item)
                    for k, item in data.items()
                }
        except Exception:
            return {}

    def _save_registry(self) -> None:
        """Persist dataset metadata registry to disk."""
        data = {
            k: item.model_dump(mode="json")
            for k, item in self._registry.items()
        }
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _generate_dataset_id(self) -> str:
        """Generate unique dataset identifier prefix with 'ds_'."""
        return f"ds_{uuid.uuid4().hex[:8]}"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize raw filename for secure disk storage."""
        clean = Path(filename).name
        # Remove any path traversal or unsafe characters
        clean = re.sub(r"[^\w\.-]", "_", clean)
        return clean or "dataset.csv"

    def save_dataset(
        self,
        filename: str,
        content: bytes | Path | str,
    ) -> tuple[DatasetMetadata, DatasetProfile]:
        """Validate, store, and profile an uploaded CSV dataset."""
        # 1. Validate & parse CSV into DataFrame
        df = DatasetValidator.validate_and_parse_csv(content, filename=filename)

        # 2. Generate identifiers & safe paths
        dataset_id = self._generate_dataset_id()
        safe_name = self._sanitize_filename(filename)
        storage_filename = f"{dataset_id}_{safe_name}"
        storage_path = self.upload_dir / storage_filename

        # 3. Save raw file to storage
        if isinstance(content, (bytes, bytearray)):
            storage_path.write_bytes(content)
        elif isinstance(content, Path):
            storage_path.write_bytes(content.read_bytes())
        elif isinstance(content, str):
            path_obj = Path(content)
            if path_obj.exists() and path_obj.is_file():
                storage_path.write_bytes(path_obj.read_bytes())
            else:
                storage_path.write_text(content, encoding="utf-8")

        file_size_bytes = storage_path.stat().st_size

        # 4. Generate metadata
        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            filename=safe_name,
            rows=len(df),
            columns=len(df.columns),
            created_at=datetime.now(timezone.utc),
            storage_path=str(storage_path.resolve()),
            file_size_bytes=file_size_bytes,
        )

        # 5. Generate and persist dataset profile
        profile = self.profiler.profile(df, dataset_id=dataset_id, filename=safe_name)
        profile_file = self.profiles_dir / f"{dataset_id}_profile.json"
        profile_file.write_text(profile.model_dump_json(indent=2), encoding="utf-8")

        # 6. Update registry
        self._registry[dataset_id] = metadata
        self._save_registry()

        return metadata, profile

    def get_metadata(self, dataset_id: str) -> DatasetMetadata:
        """Retrieve metadata for a dataset by ID."""
        if dataset_id not in self._registry:
            raise DatasetNotFoundError(dataset_id)
        return self._registry[dataset_id]

    def get_profile(self, dataset_id: str) -> DatasetProfile:
        """Retrieve the cached profile for a dataset, or recompute if missing."""
        self.get_metadata(dataset_id)  # Validate existence
        profile_file = self.profiles_dir / f"{dataset_id}_profile.json"
        if profile_file.exists():
            try:
                return DatasetProfile.model_validate_json(
                    profile_file.read_text(encoding="utf-8")
                )
            except Exception:
                pass

        # Recompute if profile file was missing or corrupt
        df = self.load_dataframe(dataset_id)
        meta = self.get_metadata(dataset_id)
        profile = self.profiler.profile(df, dataset_id=dataset_id, filename=meta.filename)
        profile_file.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return profile

    def load_dataframe(self, dataset_id: str) -> pd.DataFrame:
        """Load stored dataset into a Pandas DataFrame."""
        metadata = self.get_metadata(dataset_id)
        path = Path(metadata.storage_path)
        if not path.exists():
            raise CorruptDatasetError(f"Dataset file at '{path}' is missing.")

        try:
            return pd.read_csv(path)
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="latin-1")
        except Exception as err:
            raise CorruptDatasetError(f"Failed to load dataset: {err}") from err

    def list_datasets(self) -> list[DatasetMetadata]:
        """List all stored datasets."""
        return list(self._registry.values())

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset file, profile, and metadata."""
        if dataset_id not in self._registry:
            raise DatasetNotFoundError(dataset_id)

        meta = self._registry.pop(dataset_id)
        self._save_registry()

        storage_path = Path(meta.storage_path)
        if storage_path.exists():
            storage_path.unlink()

        profile_path = self.profiles_dir / f"{dataset_id}_profile.json"
        if profile_path.exists():
            profile_path.unlink()

        return True
