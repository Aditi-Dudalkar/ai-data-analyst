"""Pydantic schemas for dataset metadata and profiles."""

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    """Detailed profile information for a single column."""

    name: str = Field(description="Column name")
    data_type: str = Field(
        description="Simplified data type: 'integer', 'float', 'string', 'boolean', or 'datetime'"
    )
    null_count: int = Field(ge=0, description="Total number of null / NaN values in column")
    null_percentage: float = Field(
        ge=0.0, le=100.0, description="Percentage of null / NaN values in column (0.0 to 100.0)"
    )
    unique_count: int = Field(ge=0, description="Count of distinct non-null values")
    sample_values: list[Any] = Field(
        default_factory=list, description="Sample of distinct non-null values"
    )

    # Numerical statistics (None if not numerical)
    mean: Optional[float] = Field(default=None, description="Arithmetic mean")
    median: Optional[float] = Field(default=None, description="Median value")
    min: Optional[Any] = Field(default=None, description="Minimum value")
    max: Optional[Any] = Field(default=None, description="Maximum value")
    std_dev: Optional[float] = Field(default=None, description="Standard deviation")

    # Categorical statistics (None if numerical or not applicable)
    top_values: Optional[dict[str, int]] = Field(
        default=None, description="Most frequent values with their frequency counts"
    )


class DatasetProfile(BaseModel):
    """Comprehensive statistical profile of a dataset."""

    dataset_id: str = Field(description="Unique identifier for the dataset")
    filename: str = Field(description="Original filename of the dataset")
    row_count: int = Field(ge=0, description="Total number of rows")
    column_count: int = Field(ge=0, description="Total number of columns")
    duplicate_rows: int = Field(ge=0, description="Number of duplicate rows")
    total_missing_cells: int = Field(ge=0, description="Total missing cells across the entire dataset")
    columns: dict[str, ColumnProfile] = Field(
        description="Dictionary mapping column name to ColumnProfile"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the profile was generated",
    )

    def to_llm_context_str(self) -> str:
        """Generate a concise string representation for LLM prompt context."""
        lines = [
            f"Dataset: {self.filename}",
            f"Rows: {self.row_count:,}",
            f"Columns: {self.column_count}",
            "",
        ]
        # Calculate padding for clean column alignment
        max_name_len = max((len(col_name) for col_name in self.columns), default=10)
        padding = max(max_name_len + 4, 16)

        for col_name, col_profile in self.columns.items():
            lines.append(f"{col_name.ljust(padding)}{col_profile.data_type}")

        return "\n".join(lines)


class DatasetMetadata(BaseModel):
    """Metadata record for a stored dataset."""

    dataset_id: str = Field(description="Unique dataset identifier")
    filename: str = Field(description="Original uploaded filename")
    rows: int = Field(ge=0, description="Number of rows in the dataset")
    columns: int = Field(ge=0, description="Number of columns in the dataset")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Dataset creation timestamp",
    )
    storage_path: str = Field(description="File system path where the dataset is stored")
    file_size_bytes: int = Field(ge=0, description="Size of the raw file in bytes")
