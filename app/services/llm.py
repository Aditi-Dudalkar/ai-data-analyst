"""LLM client abstraction layer with Mock and (future) Gemini implementations."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any


class BaseLLMClient(ABC):
    """Abstract base class defining the LLM client interface."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Send a prompt to the LLM and return the raw text response.

        Args:
            prompt: The user-facing message to send.
            system_prompt: Optional system context / instructions.

        Returns:
            The raw text response from the LLM.
        """

    def generate_json(self, prompt: str, system_prompt: str = "") -> dict[str, Any]:
        """
        Send a prompt to the LLM, returning a parsed JSON dict.

        Extracts the first JSON object found in the response in case the model
        wraps it in Markdown fences or adds extra text.

        Args:
            prompt: The user-facing message to send.
            system_prompt: Optional system context / instructions.

        Returns:
            Parsed JSON as a Python dict.

        Raises:
            ValueError: If no valid JSON object can be extracted.
        """
        raw = self.generate(prompt=prompt, system_prompt=system_prompt)
        return self._extract_json(raw)

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """Extract the first JSON object from a raw text string."""
        # Strip Markdown code fences if present
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1)

        # Find the first {...} block
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not brace_match:
            raise ValueError(f"No JSON object found in LLM response: {text!r}")

        return json.loads(brace_match.group(0))


class MockLLMClient(BaseLLMClient):
    """
    Deterministic mock LLM client for offline testing and development.

    Supports two modes:
    - ``responses``: A fixed sequence of raw text strings returned one-by-one
      on successive ``generate()`` calls. Once exhausted, the last entry repeats.
    - ``response_map``: A dict mapping prompt substrings to responses.

    If neither is configured, returns a sensible default aggregation plan.
    """

    def __init__(
        self,
        responses: list[str] | None = None,
        response_map: dict[str, str] | None = None,
    ) -> None:
        self._responses: list[str] = responses or []
        self._response_map: dict[str, str] = response_map or {}
        self._call_count: int = 0

    @property
    def call_count(self) -> int:
        """Number of times generate() has been called."""
        return self._call_count

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Return the next pre-configured response, or a default plan JSON."""
        self._call_count += 1

        # Sequence mode — cycle through responses list
        if self._responses:
            index = min(self._call_count - 1, len(self._responses) - 1)
            return self._responses[index]

        # Map mode — match prompt keywords
        combined = (system_prompt + " " + prompt).lower()
        for keyword, response in self._response_map.items():
            if keyword.lower() in combined:
                return response

        # Default fallback: generic aggregation plan
        return json.dumps({
            "question": "Default mock question",
            "operation": "aggregation",
            "metrics": [{"column": "revenue", "aggregation": "sum"}],
        })
