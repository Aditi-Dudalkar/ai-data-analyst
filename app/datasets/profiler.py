"""Dataset profiler that generates comprehensive column and dataset-level statistics."""

from datetime import datetime, timezone
import math
import re
from typing import Any
import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.exceptions import EmptyDatasetError
from app.datasets.schemas import ColumnProfile, DatasetProfile


class DatasetProfiler:
    """Computes deterministic column profiles and dataset-level summary statistics."""

    def __init__(
        self,
        sample_values_count: int | None = None,
        top_categorical_limit: int | None = None,
    ) -> None:
        self.sample_values_count = (
            sample_values_count or settings.SAMPLE_VALUES_COUNT
        )
        self.top_categorical_limit = (
            top_categorical_limit or settings.TOP_CATEGORICAL_LIMIT
        )

    def profile(
        self,
        df: pd.DataFrame,
        dataset_id: str = "ds_unknown",
        filename: str = "dataset.csv",
    ) -> DatasetProfile:
        """Generate a complete DatasetProfile from a Pandas DataFrame."""
        if df.empty or len(df) == 0:
            raise EmptyDatasetError("Cannot profile an empty dataset.")

        row_count = len(df)
        column_count = len(df.columns)
        duplicate_rows = int(df.duplicated().sum())
        total_missing_cells = int(df.isna().sum().sum())

        column_profiles: dict[str, ColumnProfile] = {}
        for col_name in df.columns:
            series = df[col_name]
            col_profile = self._profile_column(str(col_name), series, row_count)
            column_profiles[str(col_name)] = col_profile

        return DatasetProfile(
            dataset_id=dataset_id,
            filename=filename,
            row_count=row_count,
            column_count=column_count,
            duplicate_rows=duplicate_rows,
            total_missing_cells=total_missing_cells,
            columns=column_profiles,
            created_at=datetime.now(timezone.utc),
        )

    def _profile_column(
        self, col_name: str, series: pd.Series, total_rows: int
    ) -> ColumnProfile:
        """Compute profiling statistics for a single column."""
        null_count = int(series.isna().sum())
        null_percentage = (
            round((null_count / total_rows) * 100.0, 2) if total_rows > 0 else 0.0
        )
        non_null_series = series.dropna()

        unique_count = int(non_null_series.nunique())
        data_type = self._infer_data_type(col_name, series, non_null_series)

        # Extract sample values (distinct non-null values up to sample_values_count)
        samples = self._extract_samples(non_null_series, self.sample_values_count)

        mean_val = None
        median_val = None
        min_val = None
        max_val = None
        std_val = None
        top_values = None

        if data_type in ("integer", "float"):
            numeric_series = pd.to_numeric(non_null_series, errors="coerce").dropna()
            if not numeric_series.empty:
                mean_raw = numeric_series.mean()
                median_raw = numeric_series.median()
                min_raw = numeric_series.min()
                max_raw = numeric_series.max()
                std_raw = numeric_series.std() if len(numeric_series) > 1 else None

                mean_val = round(float(mean_raw), 4) if pd.notna(mean_raw) and not math.isinf(mean_raw) else None
                median_val = round(float(median_raw), 4) if pd.notna(median_raw) and not math.isinf(median_raw) else None
                min_val = self._sanitize_scalar(min_raw)
                max_val = self._sanitize_scalar(max_raw)
                std_val = round(float(std_raw), 4) if std_raw is not None and pd.notna(std_raw) and not math.isinf(std_raw) else None
        else:
            # For categorical, string, boolean, compute top values
            if not non_null_series.empty:
                val_counts = non_null_series.value_counts().head(self.top_categorical_limit)
                top_values = {
                    str(k): int(v) for k, v in val_counts.items()
                }

        return ColumnProfile(
            name=col_name,
            data_type=data_type,
            null_count=null_count,
            null_percentage=null_percentage,
            unique_count=unique_count,
            sample_values=samples,
            mean=mean_val,
            median=median_val,
            min=min_val,
            max=max_val,
            std_dev=std_val,
            top_values=top_values,
        )

    def _infer_data_type(
        self, col_name: str, series: pd.Series, non_null_series: pd.Series
    ) -> str:
        """Infer simplified data type: integer, float, boolean, datetime, string."""
        if non_null_series.empty:
            return "string"

        # Check boolean first
        if pd.api.types.is_bool_dtype(series):
            return "boolean"

        # Check datetime dtype
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        # Check integer dtype
        if pd.api.types.is_integer_dtype(series):
            return "integer"

        # Check float dtype
        if pd.api.types.is_float_dtype(series):
            col_lower = col_name.lower()
            int_indicators = ("id", "count", "num", "quantity", "qty", "year", "month", "day")
            if any(col_lower == ind or col_lower.endswith(f"_{ind}") for ind in int_indicators):
                try:
                    if (non_null_series % 1 == 0).all():
                        return "integer"
                except (TypeError, ValueError):
                    pass
            return "float"

        # Check string or object series
        # 1. Could it be boolean values represented as strings?
        if self._is_boolean_series(non_null_series):
            return "boolean"

        # 2. Could it be datetime represented as strings?
        if self._is_datetime_series(col_name, non_null_series):
            return "datetime"

        # 3. Could it be numeric stored as object/string?
        if self._is_numeric_series(non_null_series):
            # Check if all can be integers
            try:
                numeric_vals = pd.to_numeric(non_null_series)
                if (numeric_vals % 1 == 0).all():
                    return "integer"
                return "float"
            except (ValueError, TypeError):
                pass

        return "string"

    def _is_boolean_series(self, non_null_series: pd.Series) -> bool:
        """Check if series contains solely boolean representations."""
        unique_vals = set(non_null_series.astype(str).str.strip().str.lower().unique())
        boolean_pairs = [
            {"true", "false"},
            {"t", "f"},
            {"yes", "no"},
            {"1", "0"},
        ]
        return any(unique_vals.issubset(pair) for pair in boolean_pairs)

    def _is_datetime_series(self, col_name: str, non_null_series: pd.Series) -> bool:
        """Check if series contains datetime values without falsely classifying pure numbers."""
        sample = non_null_series.head(20).astype(str).str.strip()

        # If sample contains pure numbers or short text, don't parse as date
        if any(s.isdigit() and len(s) < 8 for s in sample):
            return False

        # Check for typical date separator patterns: YYYY-MM-DD, DD/MM/YYYY, etc.
        date_pattern = re.compile(
            r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}|^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"
        )
        matches = [bool(date_pattern.search(s)) for s in sample]

        # If majority matches date pattern or column name indicates a date
        col_lower = col_name.lower()
        has_date_name = any(k in col_lower for k in ("date", "time", "timestamp", "created_at", "updated_at"))

        if sum(matches) >= len(sample) * 0.8 or (has_date_name and sum(matches) > 0):
            try:
                parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().sum() >= len(sample) * 0.8:
                    return True
            except Exception:
                return False

        return False

    def _is_numeric_series(self, non_null_series: pd.Series) -> bool:
        """Check if all non-null values can be safely converted to numbers."""
        sample = non_null_series.head(50)
        try:
            converted = pd.to_numeric(sample, errors="coerce")
            return bool(converted.notna().all())
        except Exception:
            return False

    def _extract_samples(self, non_null_series: pd.Series, count: int) -> list[Any]:
        """Extract up to `count` distinct non-null sample values in native Python types."""
        samples: list[Any] = []
        for val in non_null_series.unique():
            cleaned = self._sanitize_scalar(val)
            if cleaned is not None and cleaned not in samples:
                samples.append(cleaned)
            if len(samples) >= count:
                break
        return samples

    def _sanitize_scalar(self, val: Any) -> Any:
        """Convert numpy/pandas scalars into JSON-serializable Python native types."""
        if pd.isna(val):
            return None
        if isinstance(val, (np.integer, int)):
            return int(val)
        if isinstance(val, (np.floating, float)):
            if math.isnan(val) or math.isinf(val):
                return None
            return round(float(val), 4) if float(val) % 1 != 0 else int(val)
        if isinstance(val, (np.bool_, bool)):
            return bool(val)
        if isinstance(val, (pd.Timestamp, datetime)):
            return val.isoformat()
        return str(val)
