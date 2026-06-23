from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def _service(tmp_path: Path) -> IndustrialGraphSnapshotService:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    return IndustrialGraphSnapshotService(repository)


def test_snapshot_activation_supersedes_prior_build_and_is_deterministic(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.build_and_activate()
    second = service.build_and_activate()

    assert first.build_version != second.build_version
    assert first.checksum == second.checksum
    assert second.status == "active"
    active = service.repository.get_active_snapshot()
    assert active is not None and active.build_version == second.build_version
    with service.repository.connect() as conn:
        prior_status = conn.execute(
            "SELECT status FROM graph_snapshots WHERE build_version=?", (first.build_version,)
        ).fetchone()[0]
        staged_edges = conn.execute(
            "SELECT COUNT(*) FROM graph_edges WHERE status='building'"
        ).fetchone()[0]
    assert prior_status == "superseded"
    assert staged_edges == 0


def test_snapshot_activation_rolls_back_on_failure(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)
    first = service.build_and_activate()
    staged = service.stage(IndustrialGraphBuilder(service.repository.repository).build())

    def fail_after_supersede(conn, build_version: str) -> None:
        conn.execute("UPDATE graph_snapshots SET status='superseded' WHERE status='active'")
        raise RuntimeError("forced activation failure")

    monkeypatch.setattr(service, "_activate_in_transaction", fail_after_supersede)
    with pytest.raises(RuntimeError, match="forced activation failure"):
        service.activate(staged.build_version)

    active = service.repository.get_active_snapshot()
    assert active is not None and active.build_version == first.build_version


def test_validation_failure_creates_no_snapshot(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)
    monkeypatch.setattr(service.builder, "build", lambda: type("Bad", (), {"nodes": (), "edges": (), "evidence": (), "edge_evidence": (), "source_watermark": ""})())
    with pytest.raises(Exception):
        service.build_and_activate()
    assert service.repository.get_active_snapshot() is None

