"""Agent Service: orchestrates LLM calls, prompt building, validation, and retries."""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.agent.prompts import build_plan_prompt, build_retry_prompt, build_system_prompt
from app.agent.schemas import AnalysisPlan
from app.core.config import settings
from app.core.exceptions import PlanGenerationError
from app.datasets.schemas import DatasetProfile
from app.services.llm import BaseLLMClient, MockLLMClient

logger = logging.getLogger(__name__)


class AgentService:
    """
    Generates a validated AnalysisPlan from a natural-language question and dataset profile.

    Workflow:
        1. Build system + user prompts from the question and profile.
        2. Call the LLM client.
        3. Extract and parse the JSON response into an AnalysisPlan.
        4. On failure, send a retry prompt with the error and previous output.
        5. Raise PlanGenerationError if all attempts are exhausted.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.llm_client: BaseLLMClient = llm_client or self._create_default_client()
        # max_retries = number of retries AFTER the initial attempt.
        # Total attempts = max_retries + 1.
        self.max_retries: int = (
            max_retries if max_retries is not None else settings.MAX_PLAN_RETRIES
        )
        self._system_prompt: str = build_system_prompt()

    def generate_plan(self, question: str, profile: DatasetProfile) -> AnalysisPlan:
        """
        Generate a validated AnalysisPlan for the given question and dataset.

        Args:
            question: Natural-language analytical question from the user.
            profile: DatasetProfile produced by the DatasetProfiler.

        Returns:
            A validated AnalysisPlan instance.

        Raises:
            PlanGenerationError: If a valid plan cannot be produced within the
                                 allowed number of attempts.
        """
        user_prompt = build_plan_prompt(question=question, profile=profile)
        last_error: str = ""
        last_raw: str = ""
        total_attempts = self.max_retries + 1  # e.g. 2 retries → 3 total

        for attempt in range(1, total_attempts + 1):
            prompt = (
                user_prompt
                if attempt == 1
                else build_retry_prompt(
                    error_message=last_error,
                    previous_output=last_raw,
                )
            )

            logger.info("AgentService: attempt %d / %d", attempt, total_attempts)

            raw = self.llm_client.generate(
                prompt=prompt,
                system_prompt=self._system_prompt,
            )
            last_raw = raw

            # 1. Try to extract and parse JSON from the raw response
            try:
                data = BaseLLMClient._extract_json(raw)
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = f"JSON parse error: {exc}"
                logger.warning("Attempt %d JSON parse failed: %s", attempt, last_error)
                continue

            # 2. Validate parsed dict against the AnalysisPlan schema
            try:
                # Ensure "question" is always populated from the user's original question
                data.setdefault("question", question)
                plan = AnalysisPlan.model_validate(data)
                logger.info("AgentService: valid plan generated on attempt %d", attempt)
                return plan
            except ValidationError as exc:
                last_error = str(exc)
                logger.warning(
                    "Attempt %d schema validation failed: %s", attempt, last_error
                )
                continue

        raise PlanGenerationError(attempts=total_attempts, last_error=last_error)

    @staticmethod
    def _create_default_client() -> BaseLLMClient:
        """Instantiate the appropriate LLM client based on LLM_PROVIDER config."""
        provider = settings.LLM_PROVIDER.lower()

        if provider == "mock":
            return MockLLMClient()

        # Placeholder for future Gemini integration (Milestone 3+)
        if provider == "gemini":
            raise NotImplementedError(
                "Gemini client is not yet implemented. Set LLM_PROVIDER=mock for now."
            )

        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. Supported: 'mock', 'gemini'."
        )
