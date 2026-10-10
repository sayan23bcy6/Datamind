from __future__ import annotations

from typing import Any

from app.agents.providers import LLMProvider, get_provider
from app.schemas.investigation import CleaningProposal, CriticVerdict, ProposalList


class InvestigationAgent:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_provider()

    def generate_proposals(self, profile: dict[str, Any]) -> list[CleaningProposal]:
        prompt = (
            "Review the profile and propose a set of cleaning operations as a JSON object with a 'proposals' array of at least one proposal. "
            f"Rows={profile.get('row_count')}, columns={profile.get('column_count')}. "
            f"Missing={profile.get('missing_counts', {})}."
        )
        raw = self.provider.generate_structured(
            ProposalList,
            prompt,
            tools=["profile_dataset", "detect_duplicates", "detect_missing"],
        )
        if isinstance(raw, ProposalList):
            proposals = raw.proposals
        elif isinstance(raw, dict) and "proposals" in raw:
            validated = ProposalList.model_validate(raw)
            proposals = validated.proposals
        elif isinstance(raw, list):
            proposals = [CleaningProposal.model_validate(item) for item in raw]
        else:
            raise ValueError(f"Investigation agent returned unsupported response type: {type(raw).__name__}")

        if not proposals:
            raise ValueError("Investigation agent produced an empty list of proposals")
        return proposals


class CriticAgent:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_provider()

    def review(self, proposal: CleaningProposal, evidence: dict[str, Any]) -> CriticVerdict:
        prompt = (
            "Critique the proposal against the raw tool outputs. "
            f"Proposal={proposal.model_dump_json()} Evidence={evidence}"
        )
        raw = self.provider.generate_structured(
            CriticVerdict,
            prompt,
            tools=["detect_duplicates", "detect_missing", "detect_format_inconsistencies"],
        )
        if isinstance(raw, CriticVerdict):
            return raw
        if isinstance(raw, dict):
            return CriticVerdict.model_validate(raw)
        raise ValueError(f"Critic returned unparseable output for proposal {proposal.proposal_id}")
