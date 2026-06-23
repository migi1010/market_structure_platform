from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_score.theme_score_models import ThemeScoreInput
from theme_intelligence.theme_score.theme_score_scorer import ThemeScoreScorer


def test_unresolved_bottleneck_lowers_risk_adjusted_but_raises_research_importance() -> None:
    scorer = ThemeScoreScorer()
    base = ThemeScoreInput("AI Infrastructure", 80, 75, 75, 30, "Growth", 80, 75, 20, 80, 75, 70, 5)
    constrained = ThemeScoreInput("AI Infrastructure", 80, 75, 75, 30, "Growth", 80, 75, 90, 20, 75, 70, 5)

    base_score = scorer.score(base)
    constrained_score = scorer.score(constrained)

    assert constrained_score.risk_adjusted_score < base_score.risk_adjusted_score
    assert constrained_score.research_importance > base_score.research_importance


def test_mature_crowded_theme_cannot_get_top_conviction_from_discovery_alone() -> None:
    result = ThemeScoreScorer().score(
        ThemeScoreInput("Mature AI", 95, 50, 70, 85, "Mature", 80, 40, 20, 90, 35, 45, 50)
    )

    assert result.conviction_level in {"Watchlist", "Avoid", "Medium Conviction"}

