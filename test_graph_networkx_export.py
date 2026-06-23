from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_networkx_export_returns_active_multidigraph(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    snapshot = service.build_and_activate()

    graph = service.repository.export_to_networkx()

    assert isinstance(graph, nx.MultiDiGraph)
    assert graph.number_of_nodes() == snapshot.node_count
    assert graph.number_of_edges() == snapshot.edge_count
    assert all("relationship_type" in attrs for _, _, _, attrs in graph.edges(keys=True, data=True))
    assert all("confidence_score" in attrs for _, _, _, attrs in graph.edges(keys=True, data=True))


def test_networkx_export_empty_database(tmp_path: Path) -> None:
    repository = IndustrialGraphRepository(ThemeRepository(tmp_path / "empty.sqlite3"))
    graph = repository.export_to_networkx()
    assert isinstance(graph, nx.MultiDiGraph)
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0

