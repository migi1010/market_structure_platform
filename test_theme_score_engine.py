from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_score.theme_score_models import ThemeScoreInput
from theme_intelligence.theme_score.theme_score_scorer import ThemeScoreScorer


def test_theme_score_engine_uses_required_formulas() -> None:
    scorer = ThemeScoreScorer()
    data = ThemeScoreInput(
        theme_name="Glass Substrate",
        discovery_score=89,
        emerging_score=86,
        confidence_score=80,
        crowding_proxy=30,
        lifecycle_stage="Early",
        lifecycle_confidence=85,
        catalyst_strength=92,
        bottleneck_strength=70,
        resolution_probability=65,
        beneficiary_quality=90,
        beneficiary_research_importance=88,
        bubble_penalty=10,
    )

    result = scorer.score(data)

    assert result.ai_potential_score == 89.5
    assert result.research_importance == 84.84
    assert result.allocation_readiness == 70.38
    assert result.risk_adjusted_score == 100
    assert result.score_components["lifecycle_opportunity"] == 100
