from __future__ import annotations

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_builder import ThemeScoutBuilder
from theme_intelligence.industrial_graph.theme_scout_models import (
    ScoutEvidence,
    ThemeScoutProposal,
    ThemeScoutProposalCandidate,
)
from theme_intelligence.industrial_graph.theme_scout_validator import ThemeScoutValidator


def test_validator_rejects_unsupported_influence_evidence() -> None:
    evidence = ScoutEvidence(
        evidence_id="research:1",
        source_table="research_records",
        source_record_id="1",
        source_type="research",
        source_timestamp="2026-06-01T00:00:00+00:00",
        source_identifier="record-1",
        citation="Citation",
        domain_type="Technology",
        cluster_key="technology",
        source_value={"text": "observation"},
    )
    proposal = ThemeScoutProposal(
        provider_name="fixed",
        provider_model="test",
        prompt_version="v1",
        candidates=(
            ThemeScoutProposalCandidate(
                name="Candidate",
                description="Candidate",
                evidence_ids=(evidence.evidence_id,),
            ),
        ),
    )
    build = ThemeScoutBuilder().build((evidence,), proposal, "2026-06-10T00:00:00+00:00")
    ThemeScoutValidator().validate(build)


def test_provider_candidate_cannot_start_approved() -> None:
    with pytest.raises(ValueError, match="DISCOVERED"):
        ThemeScoutProposalCandidate(
            name="Candidate",
            description="Candidate",
            evidence_ids=(),
            status="APPROVED",
        )
