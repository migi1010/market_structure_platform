from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.catalysts.catalyst_models import CatalystEvent
from theme_intelligence.catalysts.catalyst_ranker import CatalystRanker
from theme_intelligence.catalysts.catalyst_timeline import CatalystTimeline


def _event(name: str, description: str, created_at: str, strength: float = 80, polarity: str = "positive") -> CatalystEvent:
    return CatalystEvent(
        theme_name="HBM",
        catalyst_name=name,
        catalyst_type="Product Launch",
        source="finnhub",
        description=description,
        impact_score=strength,
        confidence_score=strength,
        novelty_score=strength,
        duration_score=strength,
        stage_relevance=strength,
        catalyst_strength=strength,
        timeline_status="current",
        polarity=polarity,
        created_at=created_at,
        updated_at=created_at,
    )


def test_timeline_assigns_past_current_and_future() -> None:
    timeline = CatalystTimeline(now_iso="2026-06-05T00:00:00+00:00")
    events = [
        _event("Past Expansion", "completed Micron HBM expansion", "2026-01-01T00:00:00+00:00"),
        _event("Current Ramp", "NVIDIA Blackwell ramp", "2026-06-01T00:00:00+00:00"),
        _event("Future Adoption", "HBM4 adoption expected in 2027", "2026-06-05T00:00:00+00:00"),
    ]

    bucketed = {event.catalyst_name: event.timeline_status for event in timeline.assign(events)}

    assert bucketed["Past Expansion"] == "past"
    assert bucketed["Current Ramp"] == "current"
    assert bucketed["Future Adoption"] == "future"


def test_ranker_returns_required_catalyst_buckets() -> None:
    ranker = CatalystRanker()
    events = [
        _event("Current Ramp", "NVIDIA Blackwell ramp", "2026-06-01T00:00:00+00:00", 92),
        _event("Future Adoption", "HBM4 adoption expected", "2026-06-05T00:00:00+00:00", 81),
        _event("Yield Risk", "yield risk remains a blocker", "2026-06-05T00:00:00+00:00", 77, "risk"),
    ]
    events[1] = events[1].with_updates(timeline_status="future")

    summary = ranker.rank(events)

    assert summary["top_catalysts"][0]["name"] == "Current Ramp"
    assert summary["top_positive_catalysts"][0]["name"] == "Current Ramp"
    assert summary["top_future_catalysts"][0]["name"] == "Future Adoption"
    assert summary["key_blockers"][0]["name"] == "Yield Risk"

