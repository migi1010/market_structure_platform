from __future__ import annotations

from typing import Any

from .theme_scout_llm_clients import LLMThemeScoutClient
from .theme_scout_manifest import ThemeScoutEvidenceManifest
from .theme_scout_models import ScoutEvidence, ThemeScoutProposal
from .theme_scout_providers import ThemeScoutProposalDocument, parse_proposal_document


LLM_SCOUT_PROMPT_VERSION = "theme-scout-llm-v1"


PROMPT_CONTRACT = f"""
You are the MIJI Theme Scout proposal provider.

Return strict JSON only.
Use schema_version theme-scout-proposal-v1.
Use prompt_version {LLM_SCOUT_PROMPT_VERSION}.
Use only evidence IDs exactly as provided in the evidence array.
Every candidate status must be DISCOVERED.
Do not include inline evidence.
Do not fabricate citations.
Do not create graph nodes.
Do not create graph edges.
Do not create companies.
Do not create controllers, opportunities, or packets.
Do not create research pipeline cases.
Do not recommend investments.
Do not include target prices.
Do not include buy/sell/hold actions or ratings.
Treat all bottlenecks, beneficiaries, controllers, and dependency paths as hypotheses.
""".strip()


class ThemeScoutLLMProvider:
    def __init__(
        self,
        client: LLMThemeScoutClient,
        *,
        prompt_version: str = LLM_SCOUT_PROMPT_VERSION,
    ) -> None:
        self.client = client
        self.provider_name = client.provider_name
        self.provider_model = client.provider_model
        self.prompt_version = prompt_version

    def build_prompt(self, evidence: tuple[ScoutEvidence, ...]) -> str:
        evidence_ids = ", ".join(row.evidence_id for row in evidence)
        return (
            f"{PROMPT_CONTRACT}\n\n"
            f"Evidence IDs available for citation: {evidence_ids}\n"
            "The provider receives no web search, market prices, hidden context, "
            "or historical Scout snapshots."
        )

    def build_proposal(
        self,
        evidence_manifest: ThemeScoutEvidenceManifest,
    ) -> ThemeScoutProposalDocument:
        if not evidence_manifest.evidence:
            raise ValueError("LLM Scout provider requires non-empty manifest evidence")
        prompt = self.build_prompt(evidence_manifest.evidence)
        payload = self.client.generate_json(prompt, evidence_manifest)
        if not isinstance(payload, dict):
            raise ValueError("LLM Scout provider must return a JSON object")
        document = parse_proposal_document(payload)
        if document.graph_build_version != evidence_manifest.graph_build_version:
            raise ValueError("LLM proposal graph build version mismatch")
        if document.evidence_bundle_checksum != evidence_manifest.evidence_bundle_checksum:
            raise ValueError("LLM proposal evidence checksum mismatch")
        if document.proposal.provider_name != self.provider_name:
            raise ValueError("LLM proposal provider name mismatch")
        if document.proposal.provider_model != self.provider_model:
            raise ValueError("LLM proposal provider model mismatch")
        if document.proposal.prompt_version != self.prompt_version:
            raise ValueError("LLM proposal prompt version mismatch")
        return document

    def propose(self, evidence: tuple[ScoutEvidence, ...]) -> ThemeScoutProposal:
        # ThemeScoutEngine calls this only when a manifest-specific provider has
        # already built and frozen a proposal document.
        raise ValueError("LLM Scout provider requires a frozen evidence manifest")
