from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_builder import ThemeScoutBuilder
from theme_intelligence.industrial_graph.theme_scout_models import (
    ScoutEvidence,
    ThemeCandidateInfluence,
    ThemeScoutProposal,
    ThemeScoutProposalCandidate,
    ThemeScoutSignalCluster,
)
import pytest


def _evidence(index: int, domain: str, cluster: str) -> ScoutEvidence:
    return ScoutEvidence(
        evidence_id=f"research:{index}",
        source_table="research_records",
        source_record_id=str(index),
        source_type=f"source-{index}",
        source_timestamp=f"2026-06-0{index}T00:00:00+00:00",
        source_identifier=f"record-{index}",
        citation=f"Research record {index}",
        domain_type=domain,
        cluster_key=cluster,
        source_value={"text": f"observation {index}"},
    )


def test_builder_ranks_bottleneck_before_novelty() -> None:
    evidence = (
        _evidence(1, "Constraint", "capacity"),
        _evidence(2, "Technology", "capacity"),
        _evidence(3, "Process", "infrastructure"),
        _evidence(4, "Company", "infrastructure"),
    )
    proposal = ThemeScoutProposal(
        provider_name="fixed",
        provider_model="test",
        prompt_version="v1",
        candidates=(
            ThemeScoutProposalCandidate(
                name="High Novelty",
                description="Candidate",
                evidence_ids=tuple(row.evidence_id for row in evidence),
                signal_clusters=(
                    ThemeScoutSignalCluster("capacity", "Capacity", ("research:1", "research:2")),
                    ThemeScoutSignalCluster("infrastructure", "Infrastructure", ("research:3", "research:4")),
                ),
                bottleneck_evidence_ids=(),
            ),
            ThemeScoutProposalCandidate(
                name="Future Bottleneck",
                description="Candidate",
                evidence_ids=tuple(row.evidence_id for row in evidence),
                signal_clusters=(
                    ThemeScoutSignalCluster("capacity", "Capacity", ("research:1", "research:2")),
                    ThemeScoutSignalCluster("infrastructure", "Infrastructure", ("research:3", "research:4")),
                ),
                bottleneck_evidence_ids=("research:1",),
                influence_map=(
                    ThemeCandidateInfluence(
                        target_type="Constraint",
                        target_label="Capacity",
                        evidence_ids=("research:1",),
                        cluster_keys=("capacity",),
                    ),
                ),
            ),
        ),
    )
    build = ThemeScoutBuilder().build(evidence, proposal, "2026-06-10T00:00:00+00:00")
    assert build.candidates[0].name == "Future Bottleneck"
    assert build.candidates[0].metrics.bottleneck > build.candidates[1].metrics.bottleneck


def test_duplicate_evidence_does_not_increase_counts() -> None:
    first = _evidence(1, "Technology", "a")
    proposal = ThemeScoutProposal(
        provider_name="fixed",
        provider_model="test",
        prompt_version="v1",
        candidates=(
            ThemeScoutProposalCandidate(
                name="Candidate",
                description="Candidate",
                evidence_ids=(first.evidence_id, first.evidence_id),
            ),
        ),
    )
    build = ThemeScoutBuilder().build((first, first), proposal, "2026-06-10T00:00:00+00:00")
    assert build.candidates[0].evidence_count == 1


def test_unknown_evidence_reference_is_rejected() -> None:
    proposal = ThemeScoutProposal(
        provider_name="fixed",
        provider_model="test",
        prompt_version="v1",
        candidates=(
            ThemeScoutProposalCandidate(
                name="Candidate",
                description="Candidate",
                evidence_ids=("graph_evidence:missing",),
            ),
        ),
    )
    with pytest.raises(ValueError, match="unknown proposal evidence"):
        ThemeScoutBuilder().build((), proposal, "2026-06-10T00:00:00+00:00")


def test_novelty_is_unavailable_and_has_zero_weight() -> None:
    evidence = (
        _evidence(1, "Constraint", "power"),
        _evidence(2, "Company", "power"),
    )
    proposal = ThemeScoutProposal(
        provider_name="manual-curated",
        provider_model="offline",
        prompt_version="manual-v1",
        candidates=(
            ThemeScoutProposalCandidate(
                name="AI Infrastructure Constraint Watch",
                description="Workflow validation candidate.",
                evidence_ids=tuple(row.evidence_id for row in evidence),
            ),
        ),
    )
    build = ThemeScoutBuilder().build(
        evidence, proposal, "2026-06-10T00:00:00+00:00"
    )
    metrics = build.candidates[0].metrics
    assert metrics.novelty == 0
    assert metrics.raw_values["novelty_availability_state"] == "unavailable"
    assert metrics.raw_values["novelty_methodology_state"] == "pending_methodology"
    assert metrics.applied_weights["novelty"] == 0


def test_ranking_ignores_unavailable_novelty() -> None:
    evidence = (
        _evidence(1, "Constraint", "a"),
        _evidence(2, "Company", "b"),
    )
    proposal = ThemeScoutProposal(
        provider_name="manual-curated",
        provider_model="offline",
        prompt_version="manual-v1",
        candidates=(
            ThemeScoutProposalCandidate(
                name="Z Candidate",
                description="Candidate",
                evidence_ids=tuple(row.evidence_id for row in evidence),
            ),
            ThemeScoutProposalCandidate(
                name="A Candidate",
                description="Candidate",
                evidence_ids=tuple(row.evidence_id for row in evidence),
            ),
        ),
    )
    build = ThemeScoutBuilder().build(
        evidence, proposal, "2026-06-10T00:00:00+00:00"
    )
    assert [row.name for row in build.candidates] == ["A Candidate", "Z Candidate"]
