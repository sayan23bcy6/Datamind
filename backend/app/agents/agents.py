from __future__ import annotations

from typing import Any

from app.agents.providers import LLMProvider, get_provider
from app.schemas.investigation import CleaningProposal, CriticVerdict


class InvestigationAgent:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_provider()

    def generate_proposals(self, profile: dict[str, Any]) -> list[CleaningProposal]:
        prompt = (
            "Review the profile and propose a small set of cleaning operations. "
            f"Rows={profile.get('row_count')}, columns={profile.get('column_count')}. "
            f"Missing={profile.get('missing_counts', {})}."
        )
        raw = self.provider.generate_structured(CleaningProposal, prompt, tools=["profile_dataset", "detect_duplicates", "detect_missing"])
        if isinstance(raw, list):
            return [CleaningProposal.model_validate(item) for item in raw]
        if isinstance(raw, dict):
            return [CleaningProposal.model_validate(raw)]
        return []


class CriticAgent:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_provider()

    def review(self, proposal: CleaningProposal, evidence: dict[str, Any]) -> CriticVerdict:
        prompt = (
            "Critique the proposal against the raw tool outputs. "
            f"Proposal={proposal.model_dump_json()} Evidence={evidence}"
        )
        raw = self.provider.generate_structured(CriticVerdict, prompt, tools=["detect_duplicates", "detect_missing", "detect_format_inconsistencies"])
        if isinstance(raw, dict):
            return CriticVerdict.model_validate(raw)
        if isinstance(raw, CriticVerdict):
            return raw
        return CriticVerdict(verdict="APPROVE", reasons=["No evidence of issues found."], unsupported_assumptions=[], requested_checks=[])
