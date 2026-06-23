from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_networkx_export_filters_relationships_for_supply_chain_paths(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    service.build_and_activate()

    graph = service.repository.export_to_networkx(
        relationship_types={"PART_OF_SUPPLY_CHAIN", "SUPPLY_CHAIN_ROLE"},
    )

    assert isinstance(graph, nx.MultiDiGraph)
    assert set(nx.get_edge_attributes(graph, "relationship_type").values()) == {
        "PART_OF_SUPPLY_CHAIN",
        "SUPPLY_CHAIN_ROLE",
    }
    assert nx.has_path(graph, ("Theme", "hbm"), ("Company", "company:MU"))


def test_dependency_path_rejects_endpoint_outside_active_snapshot(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    service.build_and_activate()

    with pytest.raises(ValueError, match="invalid traversal endpoint"):
        service.repository.get_dependency_paths(
            ("Theme", "missing"),
            ("Company", "company:MU"),
        )
