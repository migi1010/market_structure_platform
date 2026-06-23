from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_score.theme_score_models import ThemeFinalScore
from theme_intelligence.theme_score.theme_score_ranker import ThemeScoreRanker


def _score(name: str, risk: float, research: float, ai: float, conviction: str) -> ThemeFinalScore:
    return ThemeFinalScore(name, ai, research, 70, risk, conviction, score_components={})


def test_theme_score_ranker_supports_required_views() -> None:
    ranker = ThemeScoreRanker()
    rows = [
        _score("Glass Substrate", 84, 95, 91, "High Conviction"),
        _score("HBM", 90, 82, 88, "Very High Conviction"),
        _score("Quantum", 45, 70, 72, "Watchlist"),
    ]

    ranked = ranker.rank(rows)

    assert ranked["top_ai_themes"][0]["theme"] == "Glass Substrate"
    assert ranked["highest_research_priority"][0]["theme"] == "Glass Substrate"
    assert ranked["best_risk_adjusted"][0]["theme"] == "HBM"
    assert ranked["highest_conviction"][0]["conviction_level"] == "Very High Conviction"

