from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.controller_engine import ControllerEngine
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.opportunity_builder import OpportunityBuilder
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def build_controller_repository(tmp_path: Path) -> tuple[ThemeRepository, object]:
    repository = ThemeRepository(tmp_path / "opportunity.sqlite3")
    ThemeSeedLoader(repository=repository).load(
        recompute=False, build_industrial_graph=False
    )
    IndustrialGraphSnapshotService(repository).build_and_activate()
    controller = ControllerEngine(repository).build_and_activate()
    return repository, controller


def add_cowos_market_inputs(
    repository: ThemeRepository,
    *,
    crowding: float = 40.0,
    valuation: float = 20.0,
    bubble: float = 30.0,
) -> None:
    timestamp = "2026-06-12T00:00:00+00:00"
    with repository._connect() as conn:
        conn.execute(
            """
            INSERT INTO theme_discovery_scores (
                theme_name, theme_id, name_zh, discovery_score, emerging_score,
                catalyst_score, entity_strength_score, confidence_score,
                crowding_proxy, final_ai_score, lifecycle_stage,
                lifecycle_confidence, expected_next_stage, lifecycle_reason,
                time_window, key_catalysts_json, beneficiaries_json, brief_json,
                updated_at
            ) VALUES (
                'CoWoS', 'cowos', '', 0, 0, 0, 0, 0, ?, 0, 'emerging',
                0, 'accelerating', '', '', '[]', '[]', '{}', ?
            )
            ON CONFLICT(theme_name) DO UPDATE SET
                crowding_proxy=excluded.crowding_proxy,
                updated_at=excluded.updated_at
            """,
            (crowding, timestamp),
        )
        conn.execute(
            """
            UPDATE theme_beneficiary_scores
            SET valuation_penalty=?, bubble_penalty=?, updated_at=?
            WHERE theme_name='CoWoS' AND ticker='TSM'
            """,
            (valuation, bubble, timestamp),
        )
        conn.commit()


def test_opportunity_build_is_deterministic(tmp_path: Path) -> None:
    repository, controller = build_controller_repository(tmp_path)
    add_cowos_market_inputs(repository)
    builder = OpportunityBuilder(repository)
    first = builder.build(controller.controller_version)
    second = builder.build(controller.controller_version)
    assert first == second
    assert first.controller_snapshot_id == controller.id
    assert first.graph_snapshot_id == controller.graph_snapshot_id
    assert all(row.evidence_ids for row in first.opportunities)


def test_ambiguous_zero_is_unavailable_and_weights_renormalize(
    tmp_path: Path,
) -> None:
    repository, controller = build_controller_repository(tmp_path)
    add_cowos_market_inputs(repository, valuation=0.0, bubble=0.0)
    row = next(
        item
        for item in OpportunityBuilder(repository).build(
            controller.controller_version
        ).opportunities
        if item.company_key == ("Company", "company:TSM")
    )
    assert row.market_attention.availability_state == "available"
    assert row.valuation.availability_state == "unavailable"
    assert row.valuation.unavailable_reason == "ambiguous_zero"
    assert row.bubble_risk.availability_state == "unavailable"
    assert row.applied_weights["valuation_component"] == 0
    assert row.applied_weights["bubble_risk_component"] == 0
    assert sum(row.applied_weights.values()) == 1.0
    assert row.coverage_component == 90.0


def test_positive_penalties_are_admitted_with_source_provenance(
    tmp_path: Path,
) -> None:
    repository, controller = build_controller_repository(tmp_path)
    add_cowos_market_inputs(repository, valuation=20.0, bubble=30.0)
    row = next(
        item
        for item in OpportunityBuilder(repository).build(
            controller.controller_version
        ).opportunities
        if item.company_key == ("Company", "company:TSM")
    )
    assert row.valuation.normalized_value == 80.0
    assert row.bubble_risk.normalized_value == 70.0
    assert row.valuation.source_records[0].source_table == "theme_beneficiary_scores"
    assert row.valuation.source_records[0].source_timestamp
    assert row.coverage_component == 100.0
