from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.discovery.discovery_ranking import rank_discovery_themes
from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeMention


def test_discovery_ranking_prioritizes_accelerating_catalyst_backed_theme() -> None:
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    mentions = [
        ThemeMention("Glass Substrate", "finnhub", "GLW", "glass core substrate", "2026-06-05T00:00:00+00:00", 72),
        ThemeMention("Glass Substrate", "fmp", "INTC", "panel level packaging", "2026-06-04T00:00:00+00:00", 70),
        ThemeMention("Glass Substrate", "sec_filings", "INTC", "advanced packaging substrate", "2026-06-03T00:00:00+00:00", 68),
        ThemeMention("AI Infrastructure", "market", "QQQ", "AI infrastructure", "2026-05-15T00:00:00+00:00", 61),
        ThemeMention("AI Infrastructure", "market", "SMH", "AI infrastructure", "2026-05-14T00:00:00+00:00", 61),
    ]
    catalysts = [CatalystRecord("Glass Substrate", "Intel Packaging", "technology_breakthrough", "sec_filings", 82, 78)]
    beneficiaries = [ThemeBeneficiary("Glass Substrate", "GLW", "Corning Inc.", 82, 80)]

    ranked = rank_discovery_themes(mentions, catalysts, [], beneficiaries, now=now)

    assert ranked[0].name == "Glass Substrate"
    assert ranked[0].final_ai_score > ranked[-1].final_ai_score
    assert ranked[0].brief.why_now
    assert ranked[0].final_ai_score != 93
