"""Pydantic schemas and enums defining the Structured Analysis Plan contract."""

from enum import Enum
import json
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class OperationType(str, Enum):
    """Supported analytical operations."""

    AGGREGATION = "aggregation"
    FILTERING = "filtering"
    RANKING = "ranking"
    SUMMARY = "summary"
    TREND = "trend"


class AggregationType(str, Enum):
    """Supported aggregation functions."""

    SUM = "sum"
    AVG = "avg"
    MEAN = "mean"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"


class Metric(BaseModel):
    """Specification of an aggregate metric to compute."""

    column: str = Field(description="Column to aggregate, or '*' for row count")
    aggregation: AggregationType = Field(description="Aggregation function to apply")
    alias: Optional[str] = Field(default=None, description="Optional alias for the computed result")


class FilterOperator(str, Enum):
    """Supported filter comparison operators."""

    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"
    YEAR = "year"
    MONTH = "month"


class FilterCondition(BaseModel):
    """Filter condition applied to a dataset."""

    column: str = Field(description="Target column name to filter")
    operator: FilterOperator = Field(description="Comparison operator")
    value: Any = Field(description="Filter comparison value (scalar, list, or dict)")


class SortDirection(str, Enum):
    """Direction for sorting results."""

    ASC = "asc"
    DESC = "desc"


class SortSpec(BaseModel):
    """Sorting configuration for query results."""

    column: str = Field(description="Column to sort by")
    direction: SortDirection = Field(default=SortDirection.ASC, description="Sort order: 'asc' or 'desc'")


class VisualizationType(str, Enum):
    """Supported visualization chart types."""

    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    PIE = "pie"


class VisualizationSpec(BaseModel):
    """Specification for generating a chart from analysis results."""

    type: VisualizationType = Field(description="Type of chart to produce")
    x: str = Field(description="Column for horizontal axis")
    y: Optional[str] = Field(default=None, description="Column for vertical axis (optional for histograms)")
    title: Optional[str] = Field(default=None, description="Chart title")
    aggregation: Optional[str] = Field(default=None, description="Optional aggregation hint for chart")


class AnalysisPlan(BaseModel):
    """Structured Analysis Plan representing the contract between question and execution."""

    question: str = Field(description="The user's analytical question")
    operation: OperationType = Field(
        default=OperationType.AGGREGATION,
        description="Core operation: aggregation, filtering, ranking, summary, or trend",
    )
    group_by: Optional[list[str]] = Field(
        default=None, description="Columns to group by"
    )
    metrics: list[Metric] = Field(
        default_factory=list, description="Computed metrics"
    )
    filters: Optional[list[FilterCondition]] = Field(
        default=None, description="Filter conditions to apply"
    )
    sort: Optional[SortSpec] = Field(
        default=None, description="Sorting specification"
    )
    limit: Optional[int] = Field(
        default=None, ge=1, description="Maximum number of rows to return"
    )
    visualization: Optional[VisualizationSpec] = Field(
        default=None, description="Suggested visualization specification"
    )

    @model_validator(mode="after")
    def validate_plan_coherence(self) -> "AnalysisPlan":
        """Validate logical consistency of the analysis plan."""
        # Clean group_by if empty list
        if self.group_by is not None and len(self.group_by) == 0:
            self.group_by = None

        # Clean filters if empty list
        if self.filters is not None and len(self.filters) == 0:
            self.filters = None

        return self

    def to_dict(self, exclude_none: bool = True) -> dict[str, Any]:
        """Convert analysis plan to a dictionary, omitting unset optional fields."""
        return self.model_dump(mode="json", exclude_none=exclude_none)

    def to_json(self, indent: int = 2) -> str:
        """Convert analysis plan to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def json_schema_for_llm(cls) -> str:
        """Generate JSON schema to be used in LLM system prompts for Milestone 3."""
        return json.dumps(cls.model_json_schema(), indent=2)
