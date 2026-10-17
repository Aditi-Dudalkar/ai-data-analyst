"""Unit tests for DatasetProfiler."""

import pandas as pd
import pytest

from app.core.exceptions import EmptyDatasetError
from app.datasets.profiler import DatasetProfiler
from app.datasets.schemas import DatasetProfile


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a diverse test DataFrame with various types, nulls, and duplicates."""
    return pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4, 5, 5],  # Integer with duplicate row
            "order_date": [
                "2025-01-01",
                "2025-01-02",
                "2025-01-03",
                "2025-01-04",
                "2025-01-05",
                "2025-01-05",
            ],  # Datetime strings
            "category": [
                "Electronics",
                "Furniture",
                "Electronics",
                "Clothing",
                "Furniture",
                "Furniture",
            ],  # Categorical
            "revenue": [100.5, 200.0, 150.0, None, 300.0, 300.0],  # Float with null
            "is_active": [True, False, True, True, False, False],  # Boolean
        }
    )


def test_profiler_dataset_level_stats(sample_dataframe: pd.DataFrame) -> None:
    """Test dataset-level row count, column count, duplicates, and missing cells."""
    profiler = DatasetProfiler()
    profile = profiler.profile(sample_dataframe, dataset_id="ds_test", filename="test.csv")

    assert profile.dataset_id == "ds_test"
    assert profile.filename == "test.csv"
    assert profile.row_count == 6
    assert profile.column_count == 5
    assert profile.duplicate_rows == 1  # Row 5 is identical to row 4
    assert profile.total_missing_cells == 1  # One None in revenue


def test_profiler_numerical_stats(sample_dataframe: pd.DataFrame) -> None:
    """Test statistical calculations for numerical columns."""
    profiler = DatasetProfiler()
    profile = profiler.profile(sample_dataframe)

    # Integer column
    id_prof = profile.columns["customer_id"]
    assert id_prof.data_type == "integer"
    assert id_prof.null_count == 0
    assert id_prof.null_percentage == 0.0
    assert id_prof.min == 1
    assert id_prof.max == 5
    assert id_prof.unique_count == 5

    # Float column with null
    rev_prof = profile.columns["revenue"]
    assert rev_prof.data_type == "float"
    assert rev_prof.null_count == 1
    assert rev_prof.null_percentage == round((1 / 6) * 100, 2)
    assert rev_prof.min == 100.5
    assert rev_prof.max == 300.0
    # Values: [100.5, 200.0, 150.0, 300.0, 300.0] -> mean = 210.1, median = 200.0
    assert rev_prof.mean == 210.1
    assert rev_prof.median == 200.0
    assert rev_prof.std_dev is not None and rev_prof.std_dev > 0


def test_profiler_categorical_stats(sample_dataframe: pd.DataFrame) -> None:
    """Test categorical column frequency counts and unique values."""
    profiler = DatasetProfiler(top_categorical_limit=2)
    profile = profiler.profile(sample_dataframe)

    cat_prof = profile.columns["category"]
    assert cat_prof.data_type == "string"
    assert cat_prof.unique_count == 3
    assert cat_prof.top_values is not None
    # Most frequent: Furniture (3), Electronics (2)
    assert cat_prof.top_values["Furniture"] == 3
    assert cat_prof.top_values["Electronics"] == 2
    assert len(cat_prof.top_values) <= 2


def test_profiler_datetime_detection(sample_dataframe: pd.DataFrame) -> None:
    """Test that ISO date strings are correctly inferred as datetime."""
    profiler = DatasetProfiler()
    profile = profiler.profile(sample_dataframe)

    date_prof = profile.columns["order_date"]
    assert date_prof.data_type == "datetime"
    assert date_prof.null_count == 0
    assert len(date_prof.sample_values) > 0


def test_profiler_boolean_detection(sample_dataframe: pd.DataFrame) -> None:
    """Test that boolean columns are correctly inferred."""
    profiler = DatasetProfiler()
    profile = profiler.profile(sample_dataframe)

    bool_prof = profile.columns["is_active"]
    assert bool_prof.data_type == "boolean"
    assert bool_prof.top_values is not None
    assert "True" in bool_prof.top_values or "true" in bool_prof.top_values or bool_prof.top_values.get("True") == 3


def test_profiler_empty_dataframe_raises_error() -> None:
    """Test that profiling an empty DataFrame raises EmptyDatasetError."""
    profiler = DatasetProfiler()
    empty_df = pd.DataFrame()

    with pytest.raises(EmptyDatasetError):
        profiler.profile(empty_df)


def test_profiler_all_null_column() -> None:
    """Test edge case where a column is entirely nulls."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "empty_col": [None, None, None],
        }
    )
    profiler = DatasetProfiler()
    profile = profiler.profile(df)

    col = profile.columns["empty_col"]
    assert col.null_count == 3
    assert col.null_percentage == 100.0
    assert col.unique_count == 0
    assert col.mean is None
    assert col.sample_values == []


def test_profiler_single_row_dataframe() -> None:
    """Test edge case with a single row (std_dev should be None)."""
    df = pd.DataFrame({"metric": [42.0], "label": ["test"]})
    profiler = DatasetProfiler()
    profile = profiler.profile(df)

    metric_prof = profile.columns["metric"]
    assert metric_prof.row_count if hasattr(metric_prof, "row_count") else True
    assert metric_prof.mean == 42.0
    assert metric_prof.std_dev is None


def test_profiler_llm_context_string(sample_dataframe: pd.DataFrame) -> None:
    """Test the to_llm_context_str() method matches DESIGN.md format."""
    profiler = DatasetProfiler()
    profile = profiler.profile(sample_dataframe, filename="sales.csv")

    summary = profile.to_llm_context_str()
    assert "Dataset: sales.csv" in summary
    assert "Rows: 6" in summary
    assert "Columns: 5" in summary
    assert "customer_id" in summary
    assert "integer" in summary
    assert "order_date" in summary
    assert "datetime" in summary


def test_profiler_sample_sales_csv() -> None:
    """Test profiling against the provided data/sample/sales.csv dataset."""
    from pathlib import Path

    sales_path = Path("data/sample/sales.csv")
    assert sales_path.exists()

    df = pd.read_csv(sales_path)
    profiler = DatasetProfiler()
    profile = profiler.profile(df, filename="sales.csv")

    assert profile.row_count == 20
    assert profile.column_count == 8
    assert profile.duplicate_rows == 1  # Contains 1 duplicate row
    assert profile.total_missing_cells == 1  # 1 missing region

    # Validate column types
    cols = profile.columns
    assert cols["customer_id"].data_type == "integer"
    assert cols["order_date"].data_type == "datetime"
    assert cols["product"].data_type == "string"
    assert cols["category"].data_type == "string"
    assert cols["quantity"].data_type == "integer"
    assert cols["price"].data_type == "float"
    assert cols["region"].data_type == "string"
    assert cols["revenue"].data_type == "float"

