"""Unit tests for Structured Analysis Plan schemas, builder, and manual planner."""

import json
import pytest
from pydantic import ValidationError

from app.agent.manual_planner import ManualPlanner
from app.agent.plan_builder import AnalysisPlanBuilder
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
from app.core.exceptions import UnknownQuestionError


# ==========================================
# Schema Tests
# ==========================================


def test_analysis_plan_creation_and_serialization() -> None:
    """Test creating an AnalysisPlan matching Section 7 of DESIGN.md."""
    plan = AnalysisPlan(
        question="Which region generated the highest revenue?",
        operation=OperationType.AGGREGATION,
        group_by=["region"],
        metrics=[Metric(column="revenue", aggregation=AggregationType.SUM)],
        sort=SortSpec(column="revenue", direction=SortDirection.DESC),
        limit=5,
        visualization=VisualizationSpec(
            type=VisualizationType.BAR, x="region", y="revenue"
        ),
    )

    data = plan.to_dict()
    assert data["question"] == "Which region generated the highest revenue?"
    assert data["operation"] == "aggregation"
    assert data["group_by"] == ["region"]
    assert data["metrics"] == [{"column": "revenue", "aggregation": "sum"}]
    assert data["sort"] == {"column": "revenue", "direction": "desc"}
    assert data["limit"] == 5
    assert data["visualization"]["type"] == "bar"

    # Test JSON round-trip
    json_str = plan.to_json()
    parsed_json = json.loads(json_str)
    reconstructed = AnalysisPlan.model_validate(parsed_json)
    assert reconstructed.question == plan.question
    assert reconstructed.metrics[0].aggregation == AggregationType.SUM


def test_analysis_plan_with_filters() -> None:
    """Test creating an AnalysisPlan with filters matching Section 13 of DESIGN.md."""
    plan = AnalysisPlan(
        question="Which product category had the highest revenue last year?",
        operation=OperationType.AGGREGATION,
        group_by=["category"],
        metrics=[Metric(column="revenue", aggregation=AggregationType.SUM)],
        filters=[
            FilterCondition(
                column="order_date", operator=FilterOperator.YEAR, value=2025
            )
        ],
        sort=SortSpec(column="revenue", direction=SortDirection.DESC),
        limit=1,
    )

    assert plan.filters is not None
    assert len(plan.filters) == 1
    assert plan.filters[0].column == "order_date"
    assert plan.filters[0].operator == FilterOperator.YEAR
    assert plan.filters[0].value == 2025


def test_analysis_plan_validation_constraints() -> None:
    """Test validation constraints on AnalysisPlan."""
    # Limit must be >= 1
    with pytest.raises(ValidationError):
        AnalysisPlan(
            question="Invalid limit test",
            metrics=[Metric(column="revenue", aggregation=AggregationType.SUM)],
            limit=0,
        )

    # Empty list fields are cleaned to None
    plan = AnalysisPlan(
        question="Clean empty lists",
        group_by=[],
        filters=[],
    )
    assert plan.group_by is None
    assert plan.filters is None


def test_json_schema_for_llm() -> None:
    """Test JSON schema generation for LLM context steering."""
    schema_str = AnalysisPlan.json_schema_for_llm()
    schema = json.loads(schema_str)
    assert "properties" in schema
    assert "question" in schema["properties"]
    assert "operation" in schema["properties"]
    assert "metrics" in schema["properties"]


# ==========================================
# Plan Builder Tests
# ==========================================


def test_analysis_plan_builder_fluent() -> None:
    """Test fluent construction of an AnalysisPlan using AnalysisPlanBuilder."""
    plan = (
        AnalysisPlanBuilder("What is the total revenue by product?")
        .set_operation("aggregation")
        .group_by(["product"])
        .add_metric(column="revenue", aggregation="sum", alias="total_revenue")
        .add_filter(column="category", operator="eq", value="Electronics")
        .sort_by("total_revenue", direction="desc")
        .set_limit(10)
        .set_visualization("bar", x="product", y="total_revenue", title="Top Products")
        .build()
    )

    assert plan.question == "What is the total revenue by product?"
    assert plan.operation == OperationType.AGGREGATION
    assert plan.group_by == ["product"]
    assert len(plan.metrics) == 1
    assert plan.metrics[0].alias == "total_revenue"
    assert plan.filters is not None and plan.filters[0].value == "Electronics"
    assert plan.sort is not None and plan.sort.direction == SortDirection.DESC
    assert plan.limit == 10
    assert plan.visualization is not None and plan.visualization.type == VisualizationType.BAR


def test_analysis_plan_builder_single_string_group_by() -> None:
    """Test that group_by accepts a single string gracefully."""
    plan = (
        AnalysisPlanBuilder("Region revenue")
        .group_by("region")
        .add_metric(column="revenue", aggregation="sum")
        .build()
    )
    assert plan.group_by == ["region"]


# ==========================================
# Manual Planner Tests
# ==========================================


def test_manual_planner_canonical_questions() -> None:
    """Test that ManualPlanner resolves all canonical DESIGN.md benchmark questions."""
    planner = ManualPlanner()

    # 1. Region revenue
    plan1 = planner.generate_plan("Which region generated the highest revenue?")
    assert plan1.group_by == ["region"]
    assert plan1.metrics[0].column == "revenue"
    assert plan1.metrics[0].aggregation == AggregationType.SUM
    assert plan1.sort is not None and plan1.sort.direction == SortDirection.DESC

    # 2. Product category in 2025
    plan2 = planner.generate_plan(
        "Which product category generated the highest revenue in 2025?"
    )
    assert plan2.group_by == ["category"]
    assert plan2.filters is not None
    assert plan2.filters[0].column == "order_date"
    assert plan2.limit == 1

    # 3. Average order value by region
    plan3 = planner.generate_plan("What was the average order value by region?")
    assert plan3.group_by == ["region"]
    assert plan3.metrics[0].aggregation == AggregationType.AVG

    # 4. Monthly revenue trend
    plan4 = planner.generate_plan("Show monthly revenue for 2025.")
    assert plan4.operation == OperationType.TREND
    assert plan4.group_by == ["order_date"]
    assert plan4.visualization is not None and plan4.visualization.type == VisualizationType.LINE

    # 5. Top products by quantity sold
    plan5 = planner.generate_plan("Top 5 products by quantity sold.")
    assert plan5.group_by == ["product"]
    assert plan5.metrics[0].column == "quantity"
    assert plan5.limit == 5


def test_manual_planner_unrecognized_question_raises_error() -> None:
    """Test that unrecognized or arbitrary questions raise UnknownQuestionError."""
    planner = ManualPlanner()

    with pytest.raises(UnknownQuestionError) as exc_info:
        planner.generate_plan("Tell me something interesting about this dataset.")

    assert exc_info.value.code == "UNKNOWN_QUESTION"


def test_manual_planner_custom_registration() -> None:
    """Test registering a custom question and generating a plan."""
    planner = ManualPlanner()
    planner.register_plan(
        r"count active users",
        lambda q: (
            AnalysisPlanBuilder(q)
            .set_operation(OperationType.AGGREGATION)
            .add_metric(column="*", aggregation=AggregationType.COUNT, alias="active_users")
            .add_filter(column="status", operator=FilterOperator.EQ, value="active")
            .build()
        ),
    )

    custom_plan = planner.generate_plan("Please count active users")
    assert custom_plan.metrics[0].alias == "active_users"
    assert custom_plan.filters is not None and custom_plan.filters[0].value == "active"
