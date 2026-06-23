from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.models import ThemeEntity, ThemeMention
from theme_intelligence.scoring.theme_score import score_themes


def test_theme_scores_are_generated_and_bounded() -> None:
    mentions = [
        ThemeMention("HBM", "finnhub", "NVDA", "NVIDIA Blackwell demand drives HBM growth", "2026-06-05T00:00:00+00:00", 74),
        ThemeMention("HBM", "fmp", "MU", "HBM capacity expansion accelerates", "2026-06-05T00:00:00+00:00", 70),
        ThemeMention("Glass Substrate", "sec_filings", "INTC", "Intel Packaging mentions glass substrate", "2026-06-05T00:00:00+00:00", 62),
    ]
    entities = [
        ThemeEntity("HBM", "company", "NVIDIA Corporation", "NVDA", 92),
        ThemeEntity("Glass Substrate", "company", "Corning Inc.", "GLW", 81),
    ]
    rows = {row.theme_name: row for row in score_themes(mentions, entities)}

    assert rows["HBM"].total_score > rows["Quantum"].total_score
    for row in rows.values():
        assert 0 <= row.news_velocity <= 100
        assert 0 <= row.capital_flow_score <= 100
        assert 0 <= row.attention_score <= 100
        assert 0 <= row.sentiment_score <= 100
        assert 0 <= row.total_score <= 100
