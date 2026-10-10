from __future__ import annotations

import hashlib
from typing import Any, Protocol, runtime_checkable

from app.core.config import get_settings


@runtime_checkable
class LLMProvider(Protocol):
    def generate_structured(self, schema: Any, prompt: str, tools: list[str] | None = None) -> Any:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class MockProvider:
    """Deterministic mock provider used by default in unit tests and local development."""

    def __init__(self) -> None:
        self.calls = 0

    def generate_structured(self, schema: Any, prompt: str, tools: list[str] | None = None) -> Any:
        self.calls += 1
        prompt_lower = (prompt or "").lower()
        if "critic" in prompt_lower or "critique" in prompt_lower or "verdict" in prompt_lower:
            payload = {
                "verdict": "REJECT",
                "reasons": ["This proposal is too broad for the current evidence."],
                "unsupported_assumptions": ["The duplicate rows are not tied to a single root cause."],
                "requested_checks": ["detect_duplicates", "detect_missing"],
            }
            if self.calls % 2 == 0:
                payload = {
                    "verdict": "APPROVE",
                    "reasons": ["The proposal matches the observed duplicate rows and missingness pattern."],
                    "unsupported_assumptions": [],
                    "requested_checks": [],
                }
            if hasattr(schema, "model_validate"):
                return schema.model_validate(payload)
            return payload

        if "duplicate" in prompt_lower or "missing" in prompt_lower or "clean" in prompt_lower:
            if self.calls == 1:
                return [
                    {
                        "operation": "deduplicate",
                        "target_columns": ["customer_id"],
                        "parameters": {"keep": "first"},
                        "rationale": "The sample has exact duplicate records.",
                        "expected_effect": "Remove duplicate rows without affecting file integrity.",
                        "verification_check": "detect_duplicates",
                        "confidence": "high",
                        "basis": "Exact duplicate matches were detected in the raw data.",
                    }
                ]
            return [
                {
                    "operation": "standardize_format",
                    "target_columns": ["country"],
                    "parameters": {"column": "country"},
                    "rationale": "Country labels are inconsistent across values.",
                    "expected_effect": "Normalize state names to canonical values.",
                    "verification_check": "detect_format_inconsistencies",
                    "confidence": "medium",
                    "basis": "Label variants like NY and New York were observed.",
                }
            ]

        return []

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append([float(value) / 255.0 for value in digest[:3]])
        return vectors


class GeminiProvider:
    """Thin adapter for the Gemini API. It is selected only when the provider is configured to gemini."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.google_api_key

    def generate_structured(self, schema: Any, prompt: str, tools: list[str] | None = None) -> Any:
        if not self.api_key or self.api_key == "replace-me-local-only":
            raise RuntimeError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        if hasattr(schema, "model_validate"):
            return schema.model_validate({})
        return {}

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key or self.api_key == "replace-me-local-only":
            raise RuntimeError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        return [[0.0, 0.0, 0.0] for _ in texts]


def get_provider() -> LLMProvider:
    settings = get_settings()
    provider_name = (settings.llm_provider or "mock").lower()
    if provider_name == "gemini":
        return GeminiProvider()
    return MockProvider()
