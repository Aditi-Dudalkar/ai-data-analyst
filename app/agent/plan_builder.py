"""Fluent builder for constructing structured AnalysisPlan objects."""

from typing import Any, Sequence
from app.agent.schemas import (
    AggregationType,
    AnalysisPlan,
    FilterCondition,
    FilterOperator,
    Metric,
    OperationType,
    SortDirection,
    SortSpec,
    VisualizationSpec,
    VisualizationType,
)


class AnalysisPlanBuilder:
    """Fluent API for programmatically building valid AnalysisPlan instances."""

    def __init__(self, question: str) -> None:
        self._question: str = question
        self._operation: OperationType = OperationType.AGGREGATION
        self._group_by: list[str] | None = None
        self._metrics: list[Metric] = []
        self._filters: list[FilterCondition] | None = None
        self._sort: SortSpec | None = None
        self._limit: int | None = None
        self._visualization: VisualizationSpec | None = None

    def set_operation(self, operation: OperationType | str) -> "AnalysisPlanBuilder":
        """Set the operation type."""
        self._operation = (
            operation
            if isinstance(operation, OperationType)
            else OperationType(operation.lower())
        )
        return self

    def group_by(self, columns: Sequence[str] | str) -> "AnalysisPlanBuilder":
        """Set group-by column(s)."""
        if isinstance(columns, str):
            cols = [columns]
        else:
            cols = list(columns)
        self._group_by = cols if cols else None
        return self

    def add_metric(
        self,
        column: str,
        aggregation: AggregationType | str,
        alias: str | None = None,
    ) -> "AnalysisPlanBuilder":
        """Add a metric calculation to the plan."""
        agg = (
            aggregation
            if isinstance(aggregation, AggregationType)
            else AggregationType(aggregation.lower())
        )
        self._metrics.append(Metric(column=column, aggregation=agg, alias=alias))
        return self

    def add_filter(
        self,
        column: str,
        operator: FilterOperator | str,
        value: Any,
    ) -> "AnalysisPlanBuilder":
        """Add a filter condition to the plan."""
        op = (
            operator
            if isinstance(operator, FilterOperator)
            else FilterOperator(operator.lower())
        )
        if self._filters is None:
            self._filters = []
        self._filters.append(FilterCondition(column=column, operator=op, value=value))
        return self

    def sort_by(
        self,
        column: str,
        direction: SortDirection | str = SortDirection.ASC,
    ) -> "AnalysisPlanBuilder":
        """Configure sorting for the query output."""
        dir_val = (
            direction
            if isinstance(direction, SortDirection)
            else SortDirection(direction.lower())
        )
        self._sort = SortSpec(column=column, direction=dir_val)
        return self

    def set_limit(self, limit: int | None) -> "AnalysisPlanBuilder":
        """Set maximum number of rows to return."""
        self._limit = limit
        return self

    def set_visualization(
        self,
        chart_type: VisualizationType | str,
        x: str,
        y: str | None = None,
        title: str | None = None,
        aggregation: str | None = None,
    ) -> "AnalysisPlanBuilder":
        """Configure a visualization specification."""
        t = (
            chart_type
            if isinstance(chart_type, VisualizationType)
            else VisualizationType(chart_type.lower())
        )
        self._visualization = VisualizationSpec(
            type=t, x=x, y=y, title=title, aggregation=aggregation
        )
        return self

    def build(self) -> AnalysisPlan:
        """Build and validate the final AnalysisPlan instance."""
        return AnalysisPlan(
            question=self._question,
            operation=self._operation,
            group_by=self._group_by,
            metrics=self._metrics,
            filters=self._filters,
            sort=self._sort,
            limit=self._limit,
            visualization=self._visualization,
        )
