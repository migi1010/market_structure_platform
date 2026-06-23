from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.bottlenecks.bottleneck_scorer import BottleneckScorer


def test_bottleneck_strength_uses_required_weighted_formula() -> None:
    scorer = BottleneckScorer()
    record = BottleneckRecord(
        theme_name="Glass Substrate",
        bottleneck_name="Yield",
        bottleneck_type="Yield Constraint",
        severity_score=90,
        duration_score=80,
        resolution_probability=60,
        impact_score=70,
        bottleneck_strength=0,
        controller_entities=[],
        beneficiaries=[],
        timeline_status="current",
        description="Yield limits scalable adoption.",
        evidence=[],
        updated_at="2026-06-05T00:00:00+00:00",
    )

    scored = scorer.score(record)

    expected = 90 * 0.35 + 80 * 0.25 + 70 * 0.25 + (100 - 60) * 0.15
    assert scored.bottleneck_strength == round(expected, 2)
    assert 0 <= scored.bottleneck_strength <= 100

