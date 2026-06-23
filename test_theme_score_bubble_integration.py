from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_score.theme_score_models import ThemeScoreInput
from theme_intelligence.theme_score.theme_score_scorer import ThemeScoreScorer


def test_high_bubble_penalty_lowers_allocation_readiness() -> None:
    scorer = ThemeScoreScorer()
    low_bubble = scorer.score(ThemeScoreInput("HBM", 85, 80, 80, 30, "Growth", 85, 82, 45, 70, 88, 85, 5))
    high_bubble = scorer.score(ThemeScoreInput("HBM", 85, 80, 80, 30, "Growth", 85, 82, 45, 70, 88, 85, 75))

    assert high_bubble.allocation_readiness < low_bubble.allocation_readiness
    assert high_bubble.conviction_level != "Very High Conviction"
