from __future__ import annotations

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_models import (
    DEFAULT_SCOUT_WEIGHTS,
    ScoutEvidence,
    ThemeCandidateInfluence,
    ThemeScoutCandidate,
    ThemeScoutMetrics,
    ThemeScoutReadiness,
    canonical_candidate_key,
    candidate_checksum,
)


def test_candidate_key_is_deterministic() -> None:
    assert canonical_candidate_key("AI Power Grid") == "candidate:ai-power-grid"


def test_influence_map_is_explicitly_hypothetical() -> None:
    influence = ThemeCandidateInfluence(
        target_type="Constraint",
        target_label="Transformer Supply",
        evidence_ids=("research:1",),
        cluster_keys=("power",),
    )
    assert influence.hypothesis_state == "hypothesis"


def test_candidate_scores_are_bounded() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        ThemeScoutMetrics(
            confidence=101,
            novelty=50,
            velocity=50,
            breadth=50,
            capital=50,
            bottleneck=50,
            serendipity=50,
            theme_score=50,
            coverage=50,
            raw_values={},
            normalized_values={},
            applied_weights=DEFAULT_SCOUT_WEIGHTS,
        )


def test_candidate_checksum_ignores_database_identity() -> None:
    evidence = ScoutEvidence(
        evidence_id="research:1",
        source_table="research_records",
        source_record_id="1",
        source_type="research",
        source_timestamp="2026-06-01T00:00:00+00:00",
        source_identifier="research-1",
        citation="Research record 1",
        domain_type="Technology",
        cluster_key="power",
        source_value={"text": "Grid equipment demand"},
    )
    metrics = ThemeScoutMetrics(
        confidence=50,
        novelty=50,
        velocity=50,
        breadth=50,
        capital=50,
        bottleneck=50,
        serendipity=50,
        theme_score=50,
        coverage=50,
        raw_values={},
        normalized_values={},
        applied_weights=DEFAULT_SCOUT_WEIGHTS,
    )
    readiness = ThemeScoutReadiness.from_evidence((evidence,))
    first = ThemeScoutCandidate(
        candidate_key="candidate:ai-power-grid",
        name="AI Power Grid",
        description="Candidate",
        status="DISCOVERED",
        metrics=metrics,
        readiness=readiness,
        evidence=(evidence,),
        signal_clusters=(),
        paths=(),
        influence_map=(),
        rank=1,
    )
    second = ThemeScoutCandidate(**{**first.__dict__, "id": 99, "created_at": "later"})
    assert candidate_checksum(first) == candidate_checksum(second)
