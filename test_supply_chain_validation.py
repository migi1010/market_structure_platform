from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.industrial_graph.graph_models import (
    IndustrialGraphBuild,
    IndustrialGraphNode,
)
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator
from theme_intelligence.seeds import TARGET_SEED_THEMES, ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_unknown_seed_role_fails_validation() -> None:
    invalid = replace(
        TARGET_SEED_THEMES[0],
        supply_chain_roles={"invented_role": TARGET_SEED_THEMES[0].supply_chain_roles["equipment"]},
    )

    with pytest.raises(GraphValidationError, match="unknown supply-chain role"):
        GraphValidator().validate_supply_chain_roles((invalid,))


def test_missing_or_orphan_supply_chain_role_fails_validation() -> None:
    theme = IndustrialGraphNode("Theme", "hbm", "HBM")
    missing_role = IndustrialGraphNode(
        "Industry",
        "supply_chain:hbm:invented",
        "Invented Role",
    )

    with pytest.raises(GraphValidationError, match="missing supply-chain role"):
        GraphValidator().validate(
            IndustrialGraphBuild(nodes=(theme, missing_role))
        )

    orphan_role = IndustrialGraphNode(
        "Industry",
        "supply_chain:hbm:packaging",
        "Packaging",
    )
    with pytest.raises(GraphValidationError, match="orphan supply-chain node"):
        GraphValidator().validate(
            IndustrialGraphBuild(nodes=(theme, orphan_role))
        )


def test_snapshot_activation_rollback_preserves_active_supply_chain(tmp_path: Path, monkeypatch) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    active = service.build_and_activate()
    staged = service.stage(IndustrialGraphBuilder(repository).build())

    def fail_activation(conn, build_version: str) -> None:
        conn.execute("UPDATE graph_snapshots SET status='superseded' WHERE status='active'")
        raise RuntimeError("supply-chain activation failure")

    monkeypatch.setattr(service, "_activate_in_transaction", fail_activation)
    with pytest.raises(RuntimeError, match="supply-chain activation failure"):
        service.activate(staged.build_version)

    current = service.repository.get_active_snapshot()
    assert current is not None
    assert current.build_version == active.build_version
