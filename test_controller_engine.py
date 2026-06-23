from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.controller_engine import ControllerEngine
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def _engine(tmp_path: Path) -> tuple[ControllerEngine, object]:
    repository = ThemeRepository(tmp_path / "controller.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    graph_snapshot = IndustrialGraphSnapshotService(repository).build_and_activate()
    return ControllerEngine(repository), graph_snapshot


def test_controller_activation_is_deterministic_and_graph_independent(tmp_path: Path) -> None:
    engine, graph_snapshot = _engine(tmp_path)
    first = engine.build_and_activate()
    second = engine.build_and_activate()
    assert first.controller_version != second.controller_version
    assert first.checksum == second.checksum
    assert engine.repository.get_active_snapshot() == graph_snapshot
    ranked = engine.get_ranked_controllers(limit=5)
    assert ranked == sorted(ranked, key=lambda row: (row.rank, row.company_key))


def test_controller_activation_rolls_back(tmp_path: Path, monkeypatch) -> None:
    engine, _ = _engine(tmp_path)
    first = engine.build_and_activate()
    staged = engine.stage(engine.build())

    def fail(conn, controller_version: str) -> None:
        conn.execute("UPDATE controller_snapshots SET status='superseded' WHERE status='active'")
        raise RuntimeError("forced controller activation failure")

    monkeypatch.setattr(engine, "_activate_in_transaction", fail)
    with pytest.raises(RuntimeError, match="forced controller"):
        engine.activate(staged.controller_version)
    assert engine.repository.get_active_controller_snapshot().controller_version == first.controller_version


def test_controller_activation_rejects_checksum_mismatch(tmp_path: Path) -> None:
    engine, _ = _engine(tmp_path)
    staged = engine.stage(engine.build())
    with engine.repository.connect() as conn:
        conn.execute(
            "UPDATE controller_snapshots SET checksum='tampered' WHERE controller_version=?",
            (staged.controller_version,),
        )
        conn.commit()
    with pytest.raises(ValueError, match="checksum mismatch"):
        engine.activate(staged.controller_version)
