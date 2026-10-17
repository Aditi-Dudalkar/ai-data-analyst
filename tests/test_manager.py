"""Unit tests for DatasetManager and DatasetValidator."""

from pathlib import Path
import pytest
import pandas as pd

from app.core.exceptions import (
    DatasetNotFoundError,
    DatasetSizeLimitExceededError,
    EmptyDatasetError,
    InvalidFileFormatError,
)
from app.datasets.manager import DatasetManager
from app.datasets.validator import DatasetValidator


@pytest.fixture
def manager(tmp_path: Path) -> DatasetManager:
    """Create a DatasetManager instance with a temporary directory."""
    return DatasetManager(upload_dir=tmp_path / "uploads")


@pytest.fixture
def sample_csv_content() -> bytes:
    """Provide sample CSV raw bytes."""
    return (
        b"id,name,amount\n"
        b"1,Widget,25.50\n"
        b"2,Gadget,45.00\n"
        b"3,Doohickey,12.75\n"
    )


def test_save_and_load_dataset(manager: DatasetManager, sample_csv_content: bytes) -> None:
    """Test saving a CSV dataset and subsequently loading its DataFrame."""
    metadata, profile = manager.save_dataset("test_items.csv", sample_csv_content)

    assert metadata.dataset_id.startswith("ds_")
    assert metadata.filename == "test_items.csv"
    assert metadata.rows == 3
    assert metadata.columns == 3
    assert metadata.file_size_bytes == len(sample_csv_content)
    assert Path(metadata.storage_path).exists()

    # Load dataframe
    df = manager.load_dataframe(metadata.dataset_id)
    assert len(df) == 3
    assert list(df.columns) == ["id", "name", "amount"]

    # Verify profile was created
    cached_profile = manager.get_profile(metadata.dataset_id)
    assert cached_profile.row_count == 3
    assert "amount" in cached_profile.columns
    assert cached_profile.columns["amount"].mean == 27.75


def test_list_and_delete_dataset(manager: DatasetManager, sample_csv_content: bytes) -> None:
    """Test listing datasets and deleting a dataset."""
    metadata, _ = manager.save_dataset("file_a.csv", sample_csv_content)
    dataset_id = metadata.dataset_id

    # Verify listing
    datasets = manager.list_datasets()
    assert any(d.dataset_id == dataset_id for d in datasets)

    # Delete dataset
    deleted = manager.delete_dataset(dataset_id)
    assert deleted is True
    assert not Path(metadata.storage_path).exists()

    # Verify deleted from registry
    with pytest.raises(DatasetNotFoundError):
        manager.get_metadata(dataset_id)


def test_reject_unsupported_file_format(manager: DatasetManager) -> None:
    """Test that uploading a non-CSV file raises InvalidFileFormatError."""
    with pytest.raises(InvalidFileFormatError):
        manager.save_dataset("data.xlsx", b"some binary data")

    with pytest.raises(InvalidFileFormatError):
        DatasetValidator.validate_filename("notes.txt")


def test_reject_empty_dataset(manager: DatasetManager) -> None:
    """Test that saving an empty file raises EmptyDatasetError."""
    with pytest.raises(EmptyDatasetError):
        manager.save_dataset("empty.csv", b"")

    with pytest.raises(EmptyDatasetError):
        manager.save_dataset("empty_rows.csv", b"col1,col2\n")


def test_reject_file_exceeding_size_limit(manager: DatasetManager) -> None:
    """Test that exceeding configured size limit raises DatasetSizeLimitExceededError."""
    with pytest.raises(DatasetSizeLimitExceededError):
        DatasetValidator.validate_file_size(size_bytes=1000, max_size_bytes=500)


def test_get_nonexistent_dataset(manager: DatasetManager) -> None:
    """Test that querying a nonexistent dataset raises DatasetNotFoundError."""
    with pytest.raises(DatasetNotFoundError):
        manager.get_metadata("ds_nonexistent")
