from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.bottlenecks.bottleneck_ranker import BottleneckRanker
from theme_intelligence.bottlenecks.bottleneck_timeline import BottleneckTimeline


def _record(name: str, description: str, updated_at: str, strength: float = 75) -> BottleneckRecord:
    return BottleneckRecord(
        theme_name="HBM",
        bottleneck_name=name,
        bottleneck_type="Capacity Constraint",
        severity_score=strength,
        duration_score=strength,
        resolution_probability=45,
        impact_score=strength,
        bottleneck_strength=strength,
        controller_entities=[],
        beneficiaries=[],
        timeline_status="current",
        description=description,
        evidence=[],
        updated_at=updated_at,
    )


def test_bottleneck_timeline_assigns_past_current_and_future() -> None:
    timeline = BottleneckTimeline(now_iso="2026-06-05T00:00:00+00:00")
    rows = [
        _record("Past Capacity", "completed prior expansion", "2026-01-01T00:00:00+00:00"),
        _record("Current Capacity", "HBM capacity remains tight", "2026-06-01T00:00:00+00:00"),
        _record("Future Relief", "capacity relief expected in 2027", "2026-06-05T00:00:00+00:00"),
    ]

    statuses = {row.bottleneck_name: row.timeline_status for row in timeline.assign(rows)}

    assert statuses["Past Capacity"] == "past"
    assert statuses["Current Capacity"] == "current"
    assert statuses["Future Relief"] == "future"


def test_bottleneck_ranker_returns_primary_and_secondary_bottlenecks() -> None:
    summary = BottleneckRanker().rank(
        [
            _record("Yield", "Yield limits scaling", "2026-06-05T00:00:00+00:00", 88),
            _record("Equipment", "Packaging equipment is tight", "2026-06-05T00:00:00+00:00", 72),
        ]
    )

    assert summary["primary_bottleneck"]["name"] == "Yield"
    assert summary["secondary_bottlenecks"][0]["name"] == "Equipment"
    assert summary["why_it_matters"]

