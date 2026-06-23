from __future__ import annotations

from pathlib import Path

import pytest

from test_opportunity_builder import build_controller_repository

from theme_intelligence.industrial_graph.opportunity_engine import OpportunityEngine


def test_opportunity_activation_is_deterministic_and_independent(
    tmp_path: Path,
) -> None:
    repository, controller = build_controller_repository(tmp_path)
    engine = OpportunityEngine(repository)
    first = engine.build_and_activate(controller.controller_version)
    second = engine.build_and_activate(controller.controller_version)
    assert first.opportunity_version != second.opportunity_version
    assert first.checksum == second.checksum
    assert engine.repository.get_active_controller_snapshot() == controller
    assert (
        engine.repository.get_active_opportunity_snapshot().opportunity_version
        == second.opportunity_version
    )
    assert engine.get_ranked_opportunities() == sorted(
        engine.get_ranked_opportunities(),
        key=lambda row: (row.rank, row.company_key),
    )


def test_opportunity_activation_rolls_back(tmp_path: Path, monkeypatch) -> None:
    repository, controller = build_controller_repository(tmp_path)
    engine = OpportunityEngine(repository)
    first = engine.build_and_activate(controller.controller_version)
    staged = engine.stage(engine.build(controller.controller_version))

    def fail(conn, opportunity_version: str) -> None:
        conn.execute(
            "UPDATE opportunity_snapshots SET status='superseded' WHERE status='active'"
        )
        raise RuntimeError("forced opportunity activation failure")

    monkeypatch.setattr(engine, "_activate_in_transaction", fail)
    with pytest.raises(RuntimeError, match="forced opportunity"):
        engine.activate(staged.opportunity_version)
    assert (
        engine.repository.get_active_opportunity_snapshot().opportunity_version
        == first.opportunity_version
    )


def test_opportunity_activation_rejects_checksum_mismatch(
    tmp_path: Path,
) -> None:
    repository, controller = build_controller_repository(tmp_path)
    engine = OpportunityEngine(repository)
    staged = engine.stage(engine.build(controller.controller_version))
    with engine.repository.connect() as conn:
        conn.execute(
            """
            UPDATE opportunity_snapshots
            SET checksum='tampered'
            WHERE opportunity_version=?
            """,
            (staged.opportunity_version,),
        )
        conn.commit()
    with pytest.raises(ValueError, match="checksum mismatch"):
        engine.activate(staged.opportunity_version)
