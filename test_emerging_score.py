from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.models import ThemeMention
from theme_intelligence.scoring.emerging_score import compute_emerging_score


def test_emerging_score_rewards_recent_acceleration() -> None:
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    mentions = [
        ThemeMention("Glass Substrate", "finnhub", "GLW", "glass core substrate demand", "2026-06-05T00:00:00+00:00", 70),
        ThemeMention("Glass Substrate", "fmp", "INTC", "panel level packaging", "2026-06-04T00:00:00+00:00", 68),
        ThemeMention("Glass Substrate", "sec_filings", "INTC", "advanced packaging substrate", "2026-06-03T00:00:00+00:00", 66),
        ThemeMention("Glass Substrate", "finnhub", "GLW", "glass substrate", "2026-05-10T00:00:00+00:00", 58),
    ]

    result = compute_emerging_score(mentions, now=now)

    assert result.score > 70
    assert result.recent_count == 3
    assert result.baseline_count == 1


def test_emerging_score_stays_low_without_mentions() -> None:
    result = compute_emerging_score([])

    assert result.score == 0
    assert result.recent_count == 0
