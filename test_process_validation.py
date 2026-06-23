from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.industrial_graph.graph_models import IndustrialGraphBuild, IndustrialGraphNode
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator
from theme_intelligence.seeds import TARGET_SEED_THEMES, ThemeSeedLoader
from theme_intelligence.seeds.theme_seed_models import (
    SeedProcess,
    SeedProcessConstraintLink,
    SeedProcessResolutionLink,
)
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_duplicate_and_orphan_process_nodes_are_rejected() -> None:
    process = IndustrialGraphNode("Process", "process:validation", "Validation")
    with pytest.raises(GraphValidationError, match="duplicate canonical node"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(process, process)))
    with pytest.raises(GraphValidationError, match="orphan process"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(process,)))


@pytest.mark.parametrize(
    ("process", "message"),
    [
        (
            SeedProcess(
                key="wafer_bonding",
                name="Wafer Bonding",
                citation="Approved process.",
                constraint_links=(SeedProcessConstraintLink("Missing Constraint", "Evidence."),),
            ),
            "unknown constraint",
        ),
        (
            SeedProcess(
                key="wafer_bonding",
                name="Wafer Bonding",
                citation="Approved process.",
                resolution_links=(SeedProcessResolutionLink("MISSING", "Evidence."),),
            ),
            "unknown ticker",
        ),
        (
            SeedProcess(
                key="wafer_bonding",
                name="Wafer Bonding",
                citation="Approved process.",
                constraint_links=(SeedProcessConstraintLink("Stacking Yield", ""),),
            ),
            "missing citation",
        ),
    ],
)
def test_explicit_process_links_validate_references_and_citations(process, message: str) -> None:
    hbm = next(theme for theme in TARGET_SEED_THEMES if theme.theme_id == "hbm")
    invalid = replace(hbm, processes=(process,))

    with pytest.raises(GraphValidationError, match=message):
        GraphValidator().validate_technology_process_seeds((invalid,))


def test_snapshot_activation_remains_transactional(tmp_path: Path, monkeypatch) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    active = service.build_and_activate()
    staged = service.stage(IndustrialGraphBuilder(repository).build())

    def fail_activation(conn, build_version: str) -> None:
        conn.execute("UPDATE graph_snapshots SET status='superseded' WHERE status='active'")
        raise RuntimeError("process activation failure")

    monkeypatch.setattr(service, "_activate_in_transaction", fail_activation)
    with pytest.raises(RuntimeError, match="process activation failure"):
        service.activate(staged.build_version)

    current = service.repository.get_active_snapshot()
    assert current is not None and current.build_version == active.build_version
