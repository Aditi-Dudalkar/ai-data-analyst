"""Deterministic manual planning service matching analytical questions to AnalysisPlan instances."""

import re
from typing import Callable
from app.agent.plan_builder import AnalysisPlanBuilder
from app.agent.schemas import (
    AggregationType,
    AnalysisPlan,
    FilterOperator,
    OperationType,
    SortDirection,
    VisualizationType,
)
from app.core.exceptions import UnknownQuestionError


class ManualPlanner:
    """Generates structured analysis plans manually without an LLM for benchmark questions."""

    def __init__(self) -> None:
        self._registry: list[tuple[re.Pattern, Callable[[str], AnalysisPlan]]] = []
        self._register_default_plans()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize question text by stripping punctuation and lowercasing."""
        clean = re.sub(r"[^\w\s]", "", text.strip().lower())
        return re.sub(r"\s+", " ", clean)

    def register_plan(
        self,
        pattern: str,
        factory: Callable[[str], AnalysisPlan],
    ) -> None:
        """Register a custom question pattern and factory callable."""
        regex = re.compile(pattern, re.IGNORECASE)
        self._registry.append((regex, factory))

    def _register_default_plans(self) -> None:
        """Register benchmark question patterns defined in DESIGN.md."""

        # 1. "Which region generated the highest revenue?"
        self.register_plan(
            r"which region (generated|had|produced) the highest revenue",
            lambda q: (
                AnalysisPlanBuilder(q)
                .set_operation(OperationType.AGGREGATION)
                .group_by("region")
                .add_metric(column="revenue", aggregation=AggregationType.SUM)
                .sort_by("revenue", SortDirection.DESC)
                .set_limit(5)
                .set_visualization(VisualizationType.BAR, x="region", y="revenue")
                .build()
            ),
        )

        # 2. "Which product category generated the highest revenue in 2025?" / "had the highest revenue last year"
        self.register_plan(
            r"which product category (generated|had) the highest revenue (in \d{4}|last year)?",
            lambda q: (
                AnalysisPlanBuilder(q)
                .set_operation(OperationType.AGGREGATION)
                .group_by("category")
                .add_metric(column="revenue", aggregation=AggregationType.SUM)
                .add_filter(column="order_date", operator=FilterOperator.YEAR, value=2025)
                .sort_by("revenue", SortDirection.DESC)
                .set_limit(1)
                .set_visualization(VisualizationType.BAR, x="category", y="revenue")
                .build()
            ),
        )

        # 3. "What was the average order value by region?" / "average revenue by region"
        self.register_plan(
            r"(what was |what is )?the average (order value|revenue) by region",
            lambda q: (
                AnalysisPlanBuilder(q)
                .set_operation(OperationType.AGGREGATION)
                .group_by("region")
                .add_metric(
                    column="revenue",
                    aggregation=AggregationType.AVG,
                    alias="avg_order_value",
                )
                .sort_by("revenue", SortDirection.DESC)
                .set_visualization(VisualizationType.BAR, x="region", y="revenue")
                .build()
            ),
        )

        # 4. "Show monthly revenue for 2025."
        self.register_plan(
            r"(show |display )?monthly revenue( for \d{4})?",
            lambda q: (
                AnalysisPlanBuilder(q)
                .set_operation(OperationType.TREND)
                .group_by("order_date")
                .add_metric(column="revenue", aggregation=AggregationType.SUM)
                .add_filter(column="order_date", operator=FilterOperator.YEAR, value=2025)
                .sort_by("order_date", SortDirection.ASC)
                .set_visualization(VisualizationType.LINE, x="order_date", y="revenue")
                .build()
            ),
        )

        # 5. "Top 5 products by quantity sold."
        self.register_plan(
            r"top (\d+) products by quantity( sold)?",
            lambda q: (
                AnalysisPlanBuilder(q)
                .set_operation(OperationType.RANKING)
                .group_by("product")
                .add_metric(column="quantity", aggregation=AggregationType.SUM)
                .sort_by("quantity", SortDirection.DESC)
                .set_limit(5)
                .set_visualization(VisualizationType.BAR, x="product", y="quantity")
                .build()
            ),
        )

    def generate_plan(self, question: str) -> AnalysisPlan:
        """Match question against registered patterns and generate an AnalysisPlan."""
        norm_q = self._normalize_text(question)

        for pattern, factory in self._registry:
            if pattern.search(norm_q) or pattern.search(question):
                return factory(question)

        raise UnknownQuestionError(question)

    def list_supported_questions(self) -> list[str]:
        """List canonical questions supported by the default manual planner."""
        return [
            "Which region generated the highest revenue?",
            "Which product category generated the highest revenue in 2025?",
            "What was the average order value by region?",
            "Show monthly revenue for 2025.",
            "Top 5 products by quantity sold.",
        ]
