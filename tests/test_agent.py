"""Unit tests for AgentService, LLM client, and prompt engineering. Fully offline — no API keys needed."""

from __future__ import annotations

import json
import pytest

from app.agent.agent import AgentService
from app.agent.prompts import build_plan_prompt, build_retry_prompt, build_system_prompt
from app.agent.schemas import AggregationType, AnalysisPlan, OperationType, SortDirection, VisualizationType
from app.core.exceptions import PlanGenerationError
from app.datasets.schemas import ColumnProfile, DatasetProfile
from app.services.llm import MockLLMClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_profile() -> DatasetProfile:
    """Minimal DatasetProfile matching data/sample/sales.csv structure."""
    columns = {
        "customer_id": ColumnProfile(
            name="customer_id", data_type="integer", null_count=0,
            null_percentage=0.0, unique_count=20, sample_values=[1001, 1002],
            min=1001, max=1020,
        ),
        "order_date": ColumnProfile(
            name="order_date", data_type="datetime", null_count=0,
            null_percentage=0.0, unique_count=19, sample_values=["2025-01-15"],
        ),
        "product": ColumnProfile(
            name="product", data_type="string", null_count=0,
            null_percentage=0.0, unique_count=19, sample_values=["Wireless Mouse"],
            top_values={"Wireless Mouse": 2},
        ),
        "category": ColumnProfile(
            name="category", data_type="string", null_count=0,
            null_percentage=0.0, unique_count=3, sample_values=["Electronics"],
            top_values={"Electronics": 7, "Clothing": 7, "Furniture": 6},
        ),
        "quantity": ColumnProfile(
            name="quantity", data_type="integer", null_count=0,
            null_percentage=0.0, unique_count=5, sample_values=[1, 2, 3],
            min=1, max=5, mean=1.8, median=2.0, std_dev=0.95,
        ),
        "price": ColumnProfile(
            name="price", data_type="float", null_count=0,
            null_percentage=0.0, unique_count=18, sample_values=[25.5, 180.0],
            min=8.0, max=350.0, mean=71.3, median=55.0, std_dev=87.2,
        ),
        "region": ColumnProfile(
            name="region", data_type="string", null_count=1,
            null_percentage=5.0, unique_count=4, sample_values=["North", "South"],
            top_values={"North": 5, "South": 5, "West": 5, "East": 4},
        ),
        "revenue": ColumnProfile(
            name="revenue", data_type="float", null_count=0,
            null_percentage=0.0, unique_count=18, sample_values=[51.0, 180.0],
            min=40.0, max=350.0, mean=103.25, median=80.0, std_dev=89.5,
        ),
    }
    return DatasetProfile(
        dataset_id="ds_test",
        filename="sales.csv",
        row_count=20,
        column_count=8,
        duplicate_rows=1,
        total_missing_cells=1,
        columns=columns,
    )


def _make_plan_json(**kwargs) -> str:
    """Helper to produce a valid AnalysisPlan JSON string from keyword arguments."""
    base: dict = {
        "question": "Test question",
        "operation": "aggregation",
        "metrics": [{"column": "revenue", "aggregation": "sum"}],
    }
    base.update(kwargs)
    return json.dumps(base)


# ── System prompt tests ────────────────────────────────────────────────────────

def test_system_prompt_contains_schema() -> None:
    """System prompt must embed the AnalysisPlan JSON schema."""
    prompt = build_system_prompt()
    assert "AnalysisPlan" in prompt or "properties" in prompt
    assert "aggregation" in prompt
    assert "operation" in prompt


# ── User prompt tests ──────────────────────────────────────────────────────────

def test_plan_prompt_contains_question_and_columns(sample_profile: DatasetProfile) -> None:
    """Plan prompt must include user question and all column names."""
    question = "Which region generated the highest revenue?"
    prompt = build_plan_prompt(question=question, profile=sample_profile)

    assert question in prompt
    assert "revenue" in prompt
    assert "region" in prompt
    assert "category" in prompt
    assert "sales.csv" in prompt


def test_retry_prompt_contains_error_and_previous_output() -> None:
    """Retry prompt must embed both the error message and the previous LLM output."""
    error = "Field 'operation' is required."
    previous = '{"metrics": [{"column": "revenue"}]}'
    prompt = build_retry_prompt(error_message=error, previous_output=previous)

    assert error in prompt
    assert previous in prompt


# ── MockLLMClient tests ────────────────────────────────────────────────────────

def test_mock_client_sequence_mode() -> None:
    """MockLLMClient returns responses in sequence, repeating last when exhausted."""
    client = MockLLMClient(responses=["first", "second"])
    assert client.generate("any") == "first"
    assert client.generate("any") == "second"
    assert client.generate("any") == "second"  # repeats last
    assert client.call_count == 3


def test_mock_client_response_map_mode() -> None:
    """MockLLMClient returns keyword-matched response from map."""
    client = MockLLMClient(response_map={"revenue": '{"matched": true}'})
    result = client.generate("show me total revenue by region")
    assert result == '{"matched": true}'


def test_mock_client_json_extraction_strips_fences() -> None:
    """BaseLLMClient._extract_json strips Markdown fences from LLM output."""
    from app.services.llm import BaseLLMClient

    fenced = '```json\n{"operation": "aggregation"}\n```'
    parsed = BaseLLMClient._extract_json(fenced)
    assert parsed == {"operation": "aggregation"}


def test_mock_client_json_extraction_no_json_raises() -> None:
    """BaseLLMClient._extract_json raises ValueError when no JSON is present."""
    from app.services.llm import BaseLLMClient

    with pytest.raises(ValueError, match="No JSON object found"):
        BaseLLMClient._extract_json("Sorry, I cannot answer that question.")


# ── AgentService happy-path tests ──────────────────────────────────────────────

def test_agent_generates_aggregation_plan(sample_profile: DatasetProfile) -> None:
    """Agent produces a valid aggregation AnalysisPlan on first attempt."""
    response = _make_plan_json(
        question="Which region had the highest revenue?",
        operation="aggregation",
        group_by=["region"],
        metrics=[{"column": "revenue", "aggregation": "sum"}],
        sort={"column": "revenue", "direction": "desc"},
        limit=5,
        visualization={"type": "bar", "x": "region", "y": "revenue"},
    )
    client = MockLLMClient(responses=[response])
    agent = AgentService(llm_client=client, max_retries=2)

    plan = agent.generate_plan(
        question="Which region had the highest revenue?",
        profile=sample_profile,
    )

    assert isinstance(plan, AnalysisPlan)
    assert plan.operation == OperationType.AGGREGATION
    assert plan.group_by == ["region"]
    assert plan.metrics[0].aggregation == AggregationType.SUM
    assert plan.sort is not None and plan.sort.direction == SortDirection.DESC
    assert plan.visualization is not None and plan.visualization.type == VisualizationType.BAR
    assert client.call_count == 1


def test_agent_generates_ranking_plan(sample_profile: DatasetProfile) -> None:
    """Agent produces a valid ranking AnalysisPlan."""
    response = _make_plan_json(
        question="Top 5 products by quantity sold.",
        operation="ranking",
        group_by=["product"],
        metrics=[{"column": "quantity", "aggregation": "sum"}],
        sort={"column": "quantity", "direction": "desc"},
        limit=5,
    )
    client = MockLLMClient(responses=[response])
    agent = AgentService(llm_client=client, max_retries=2)

    plan = agent.generate_plan("Top 5 products by quantity sold.", sample_profile)

    assert plan.operation == OperationType.RANKING
    assert plan.group_by == ["product"]
    assert plan.limit == 5
    assert client.call_count == 1


def test_agent_generates_trend_plan(sample_profile: DatasetProfile) -> None:
    """Agent produces a valid trend AnalysisPlan."""
    response = _make_plan_json(
        question="Show monthly revenue for 2025.",
        operation="trend",
        group_by=["order_date"],
        metrics=[{"column": "revenue", "aggregation": "sum"}],
        filters=[{"column": "order_date", "operator": "year", "value": 2025}],
        visualization={"type": "line", "x": "order_date", "y": "revenue"},
    )
    client = MockLLMClient(responses=[response])
    agent = AgentService(llm_client=client, max_retries=2)

    plan = agent.generate_plan("Show monthly revenue for 2025.", sample_profile)

    assert plan.operation == OperationType.TREND
    assert plan.filters is not None and plan.filters[0].value == 2025
    assert plan.visualization is not None and plan.visualization.type == VisualizationType.LINE
    assert client.call_count == 1


# ── AgentService retry tests ───────────────────────────────────────────────────

def test_agent_retries_on_malformed_json(sample_profile: DatasetProfile) -> None:
    """Agent retries after receiving malformed JSON and succeeds on second attempt."""
    valid_response = _make_plan_json(
        question="Which category had the highest revenue?",
        operation="aggregation",
        group_by=["category"],
        metrics=[{"column": "revenue", "aggregation": "sum"}],
    )
    client = MockLLMClient(responses=[
        "this is not JSON at all!",   # attempt 1: malformed
        valid_response,                # attempt 2: valid
    ])
    agent = AgentService(llm_client=client, max_retries=2)

    plan = agent.generate_plan("Which category had the highest revenue?", sample_profile)

    assert plan.operation == OperationType.AGGREGATION
    assert plan.group_by == ["category"]
    assert client.call_count == 2  # retried once


def test_agent_retries_on_schema_validation_failure(sample_profile: DatasetProfile) -> None:
    """Agent retries after receiving JSON that fails Pydantic schema validation."""
    invalid_schema = json.dumps({
        "operation": "aggregation",
        # metrics is missing — this should fail validation
        "limit": -5,   # also invalid: must be >= 1
    })
    valid_response = _make_plan_json(
        question="Total revenue by region.",
        operation="aggregation",
        group_by=["region"],
        metrics=[{"column": "revenue", "aggregation": "sum"}],
    )
    client = MockLLMClient(responses=[invalid_schema, valid_response])
    agent = AgentService(llm_client=client, max_retries=2)

    plan = agent.generate_plan("Total revenue by region.", sample_profile)

    assert plan.operation == OperationType.AGGREGATION
    assert client.call_count == 2


def test_agent_raises_plan_generation_error_after_all_retries(
    sample_profile: DatasetProfile,
) -> None:
    """Agent raises PlanGenerationError when all attempts produce invalid output."""
    client = MockLLMClient(responses=[
        "not json",         # attempt 1
        "still not json",   # attempt 2 (retry 1)
        "never json",       # attempt 3 (retry 2)
    ])
    agent = AgentService(llm_client=client, max_retries=2)

    with pytest.raises(PlanGenerationError) as exc_info:
        agent.generate_plan("Show me something.", sample_profile)

    assert exc_info.value.code == "PLAN_GENERATION_FAILED"
    assert exc_info.value.attempts == 3  # 1 initial + 2 retries
    assert client.call_count == 3


def test_agent_uses_three_total_attempts(sample_profile: DatasetProfile) -> None:
    """Verify total attempts = max_retries (2) + initial (1) = 3."""
    client = MockLLMClient(responses=["bad"] * 10)
    agent = AgentService(llm_client=client, max_retries=2)

    with pytest.raises(PlanGenerationError) as exc_info:
        agent.generate_plan("Any question.", sample_profile)

    assert exc_info.value.attempts == 3
    assert client.call_count == 3
