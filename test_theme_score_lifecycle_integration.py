from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_score.theme_score_models import ThemeScoreInput
from theme_intelligence.theme_score.theme_score_scorer import ThemeScoreScorer


def test_early_theme_with_strong_catalysts_and_low_crowding_scores_well() -> None:
    result = ThemeScoreScorer().score(
        ThemeScoreInput("Glass Substrate", 88, 86, 82, 18, "Early", 84, 92, 60, 70, 88, 90, 5)
    )

    assert result.ai_potential_score >= 85
    assert result.conviction_level in {"High Conviction", "Very High Conviction"}

