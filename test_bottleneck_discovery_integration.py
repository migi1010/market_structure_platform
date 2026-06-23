from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.discovery.discovery_ranking import rank_discovery_themes
from theme_intelligence.models import ThemeBeneficiary, ThemeMention


def test_discovery_penalizes_severe_low_resolution_bottleneck_conservatively() -> None:
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    mentions = [
        ThemeMention("Glass Substrate", "finnhub", "GLW", "glass substrate yield improves", "2026-06-05T00:00:00+00:00", 70),
        ThemeMention("Glass Substrate", "fmp", "INTC", "glass substrate demand", "2026-06-04T00:00:00+00:00", 68),
    ]
    beneficiaries = [ThemeBeneficiary("Glass Substrate", "GLW", "Corning Inc.", 82, 80)]
    bottlenecks = [
        BottleneckRecord(
            theme_name="Glass Substrate",
            bottleneck_name="Yield",
            bottleneck_type="Yield Constraint",
            severity_score=92,
            duration_score=84,
            resolution_probability=25,
            impact_score=88,
            bottleneck_strength=88,
            controller_entities=[],
            beneficiaries=[],
            timeline_status="current",
            description="Yield limits scalable adoption.",
            evidence=[{"source": "finnhub"}, {"source": "fmp"}],
            updated_at="2026-06-05T00:00:00+00:00",
        )
    ]

    without_bottleneck = rank_discovery_themes(mentions, [], [], beneficiaries, now=now)[0]
    with_bottleneck = rank_discovery_themes(mentions, [], [], beneficiaries, bottlenecks=bottlenecks, now=now)[0]

    assert with_bottleneck.final_ai_score < without_bottleneck.final_ai_score
    assert with_bottleneck.crowding_proxy >= without_bottleneck.crowding_proxy
    assert with_bottleneck.primary_bottleneck["name"] == "Yield"

