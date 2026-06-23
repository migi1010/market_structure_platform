from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.controller_builder import ControllerBuilder
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def _prepared(tmp_path: Path):
    repository = ThemeRepository(tmp_path / "controller.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    snapshot = service.build_and_activate()
    return repository, service, snapshot


def test_controller_source_graph_keeps_evidence_and_snapshot_identity(tmp_path: Path) -> None:
    _, service, snapshot = _prepared(tmp_path)
    graph = service.repository.export_controller_source_graph(snapshot.build_version)
    assert graph.graph["graph_snapshot_id"] == snapshot.id
    assert graph.graph["graph_build_version"] == snapshot.build_version
    assert all(data["evidence_ids"] for *_, data in graph.edges(keys=True, data=True))


def test_projection_reverses_explicit_anchors_and_excludes_manual_labels(tmp_path: Path) -> None:
    repository, _, _ = _prepared(tmp_path)
    projection = ControllerBuilder(repository).build_projection()
    assert projection.has_edge(("Company", "company:AMAT"), ("Equipment", "equipment:advanced_etch"))
    assert projection.has_edge(("Company", "company:TSM"), ("Constraint", "constraint:cowos_capacity"))
    excluded = {"CONTROLS", "ENABLES", "COMPANY_EXPOSED_TO_CONSTRAINT"}
    assert all(excluded.isdisjoint(data["relationship_types"]) for *_, data in projection.edges(data=True))
