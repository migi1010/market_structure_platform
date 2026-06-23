from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_registry.theme_registry_builder import ThemeRegistryBuilder
from theme_intelligence.theme_registry.theme_registry_models import ThemeRegistryEntry


def _entry(
    theme_id: str,
    source: str,
    status: str,
    rank: float,
    updated_at: str,
    *,
    name: str | None = None,
) -> ThemeRegistryEntry:
    return ThemeRegistryEntry(
        theme_id=theme_id,
        theme_name=name or theme_id.replace("_", " ").title(),
        status=status,
        source=source,
        theme_type="INDUSTRIAL",
        rank=rank,
        research_case_count=0,
        graph_snapshot_count=1 if source == "GRAPH" else 0,
        controller_count=0,
        opportunity_count=0,
        updated_at=updated_at,
    )


def test_builder_deduplicates_by_source_priority_and_keeps_graph_entry() -> None:
    rows = ThemeRegistryBuilder().build(
        graph_entries=(_entry("hbm", "GRAPH", "ACTIVE", 90, "2026-06-20T01:00:00+00:00", name="HBM"),),
        scout_entries=(_entry("hbm", "SCOUT", "DISCOVERED", 100, "2026-06-20T02:00:00+00:00", name="HBM Scout"),),
        pipeline_entries=(),
    )

    assert len(rows) == 1
    assert rows[0].source == "GRAPH"
    assert rows[0].theme_name == "HBM"


def test_builder_sorts_status_then_rank_then_updated_at() -> None:
    rows = ThemeRegistryBuilder().build(
        graph_entries=(
            _entry("lower_active", "GRAPH", "ACTIVE", 10, "2026-06-20T03:00:00+00:00"),
            _entry("higher_active", "GRAPH", "ACTIVE", 90, "2026-06-20T01:00:00+00:00"),
        ),
        scout_entries=(
            _entry("discovered", "SCOUT", "DISCOVERED", 100, "2026-06-20T04:00:00+00:00"),
        ),
        pipeline_entries=(
            _entry("archived", "MANUAL", "ARCHIVED", 1000, "2026-06-20T05:00:00+00:00"),
        ),
    )

    assert [row.theme_id for row in rows] == [
        "higher_active",
        "lower_active",
        "discovered",
        "archived",
    ]


def test_entry_exports_theme_type_for_future_compatibility() -> None:
    payload = _entry("ai_infrastructure", "GRAPH", "ACTIVE", 50, "2026-06-20T01:00:00+00:00").to_dict()
    assert payload["theme_type"] == "INDUSTRIAL"
