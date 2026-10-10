from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Protocol, runtime_checkable

import numpy as np
from pydantic import ValidationError

from app.core.config import get_settings


@runtime_checkable
class LLMProvider(Protocol):
    def generate_structured(self, schema: Any, prompt: str, tools: list[str] | None = None) -> Any:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class MockProvider:
    """Deterministic mock provider used by default in unit tests and local development.
    Produces a reject-then-approve path and an escalation path so every workflow route is testable.
    """

    def __init__(self, mode: str = "default") -> None:
        self.calls = 0
        self.critique_calls = 0
        self.proposal_critiques: dict[str, int] = {}
        self.mode = mode

    def generate_structured(self, schema: Any, prompt: str, tools: list[str] | None = None) -> Any:
        self.calls += 1
        prompt_lower = (prompt or "").lower()

        # Critique / Verdict generation
        if "critic" in prompt_lower or "critique" in prompt_lower or "verdict" in prompt_lower:
            self.critique_calls += 1
            if "escalate" in prompt_lower or self.mode == "escalate":
                payload = {
                    "verdict": "ESCALATE_TO_HUMAN",
                    "reasons": ["Discrepancy exceeds automated resolution bounds; human judgment required."],
                    "unsupported_assumptions": ["Customer identifier semantics are context-dependent."],
                    "requested_checks": ["manual_review"],
                }
            else:
                p_match = re.search(r'"proposal_id":\s*"([^"]+)"', prompt)
                if p_match:
                    pid = p_match.group(1)
                    count = self.proposal_critiques.get(pid, 0) + 1
                    self.proposal_critiques[pid] = count
                    is_reject = (count == 1)
                else:
                    is_reject = (self.critique_calls % 2 == 1)

                if is_reject:
                    payload = {
                        "verdict": "REJECT",
                        "reasons": ["The proposal is too aggressive for the initial evidence bounds."],
                        "unsupported_assumptions": ["Assumed all duplicates stem from ingestion replay."],
                        "requested_checks": ["detect_duplicates", "detect_missing"],
                    }
                else:
                    payload = {
                        "verdict": "APPROVE",
                        "reasons": ["The proposal matches observed duplicate rows and verified tolerance bounds."],
                        "unsupported_assumptions": [],
                        "requested_checks": [],
                    }

            if hasattr(schema, "model_validate"):
                return schema.model_validate(payload)
            return payload

        # Investigation Proposals generation
        proposals = [
            {
                "proposal_id": "prop-dedup-1",
                "operation": "deduplicate",
                "target_columns": ["customer_id"],
                "parameters": {"keep": "first"},
                "rationale": "Exact duplicate rows detected across multiple customer records.",
                "expected_effect": "Remove exact duplicate rows while preserving record order.",
                "verification_check": "detect_duplicates",
                "confidence": "high",
                "confidence_basis": "Exact hash and customer key matches confirmed in profile.",
            },
            {
                "proposal_id": "prop-fmt-2",
                "operation": "standardize_format",
                "target_columns": ["country", "signup_date", "annual_revenue"],
                "parameters": {"columns": ["country", "signup_date", "annual_revenue"]},
                "rationale": "Inconsistent date representations, currency formats, and state casing variants.",
                "expected_effect": "Standardize dates to ISO 8601, strip currency symbols, and canonicalize state names.",
                "verification_check": "detect_format_inconsistencies",
                "confidence": "high",
                "confidence_basis": "Mixed date patterns and NY/New York casing variations found.",
            },
        ]

        if hasattr(schema, "model_validate"):
            if isinstance(proposals, list):
                return [schema.model_validate(p) for p in proposals]
            return schema.model_validate(proposals)
        return proposals

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return deterministic 768-dimension vectors derived from a hash of the input text."""
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(digest[:8], byteorder="big")
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(768)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append([float(x) for x in vec])
        return vectors


class GeminiProvider:
    """Gemini API provider using google-genai client."""

    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.google_api_key or not self.settings.google_api_key.strip():
            raise RuntimeError("GOOGLE_API_KEY is required when LLM_PROVIDER is configured to 'gemini'")
        from google import genai

        self.client = genai.Client(api_key=self.settings.google_api_key)
        self.model = self.settings.gemini_model or "gemini-2.0-flash"

    def generate_structured(self, schema: Any, prompt: str, tools: list[str] | None = None) -> Any:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema if hasattr(schema, "model_json_schema") else None,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            raw_text = response.text or "{}"
            data = json.loads(raw_text)
            if hasattr(schema, "model_validate"):
                if isinstance(data, list):
                    return [schema.model_validate(item) for item in data]
                return schema.model_validate(data)
            return data
        except (ValidationError, Exception) as err:
            retry_prompt = f"{prompt}\n\nNote: The previous attempt failed schema validation: {err}. Please return strictly conforming JSON."
            try:
                retry_response = self.client.models.generate_content(
                    model=self.model,
                    contents=retry_prompt,
                    config=config,
                )
                raw_text = retry_response.text or "{}"
                data = json.loads(raw_text)
                if hasattr(schema, "model_validate"):
                    if isinstance(data, list):
                        return [schema.model_validate(item) for item in data]
                    return schema.model_validate(data)
                return data
            except Exception as retry_err:
                raise RuntimeError(f"Step failed schema validation after retry: {retry_err}") from retry_err

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self.client.models.embed_content(
            model="text-embedding-004",
            contents=texts,
        )
        return [[float(val) for val in embedding.values] for embedding in result.embeddings]


def get_provider() -> LLMProvider:
    settings = get_settings()
    provider_name = (settings.llm_provider or "mock").lower().strip()
    if provider_name == "gemini":
        return GeminiProvider()
    return MockProvider()
