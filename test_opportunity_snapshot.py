from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.storage.theme_repository import ThemeRepository


def test_opportunity_schema_is_additive(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "opportunity.sqlite3")
    repository.initialize()
    with sqlite3.connect(repository.db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "opportunity_snapshots",
            "opportunity_metrics",
            "opportunity_reasoning_paths",
        } <= tables
        snapshot_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(opportunity_snapshots)")
        }
        assert {
            "controller_snapshot_id",
            "graph_snapshot_id",
            "algorithm_version",
            "checksum",
            "status",
        } <= snapshot_columns
        metric_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(opportunity_metrics)")
        }
        assert {
            "configured_weights_json",
            "applied_weights_json",
            "availability_states_json",
            "source_records_json",
            "evidence_ids_json",
        } <= metric_columns


def test_opportunity_round_trip_preserves_unavailable_market_state(
    tmp_path: Path,
) -> None:
    from test_opportunity_builder import (
        add_cowos_market_inputs,
        build_controller_repository,
    )
    from theme_intelligence.industrial_graph.opportunity_engine import (
        OpportunityEngine,
    )

    repository, controller = build_controller_repository(tmp_path)
    add_cowos_market_inputs(repository, valuation=0.0, bubble=0.0)
    engine = OpportunityEngine(repository)
    engine.build_and_activate(controller.controller_version)
    row = next(
        item
        for item in engine.get_ranked_opportunities()
        if item.company_key == ("Company", "company:TSM")
    )
    assert row.valuation.availability_state == "unavailable"
    assert row.valuation.unavailable_reason == "ambiguous_zero"
    assert row.valuation.normalized_value is None
    assert row.applied_weights["valuation_component"] == 0
