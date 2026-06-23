from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.catalysts.catalyst_models import CatalystEvent
from theme_intelligence.catalysts.catalyst_scorer import CatalystScorer


def test_catalyst_strength_uses_weighted_formula_and_bounds() -> None:
    scorer = CatalystScorer()
    event = CatalystEvent(
        theme_name="HBM",
        catalyst_name="NVIDIA Blackwell Product Launch",
        catalyst_type="Product Launch",
        source="finnhub",
        description="Blackwell ramp evidence.",
        impact_score=90,
        confidence_score=80,
        novelty_score=70,
        duration_score=60,
        stage_relevance=50,
        created_at="2026-06-05T00:00:00+00:00",
        updated_at="2026-06-05T00:00:00+00:00",
    )

    scored = scorer.score(event, lifecycle_stage="Growth")

    expected = 90 * 0.35 + 80 * 0.25 + scored.novelty_score * 0.20 + scored.duration_score * 0.15 + scored.stage_relevance * 0.05
    assert scored.catalyst_strength == round(expected, 2)
    assert 0 <= scored.catalyst_strength <= 100

