from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_networkx_export_supports_equipment_paths_and_supplier_tracing(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    service.build_and_activate()
    graph = service.repository.export_to_networkx(relationship_types={
        "USES_TECHNOLOGY", "REQUIRES_PROCESS", "TECHNOLOGY_ENABLES_PROCESS",
        "PROCESS_REQUIRES_EQUIPMENT", "EQUIPMENT_PRODUCED_BY",
        "THEME_DEPENDS_ON_EQUIPMENT",
    })
    assert isinstance(graph, nx.MultiDiGraph)
    assert nx.has_path(graph, ("Theme", "hbm"), ("Company", "company:AMAT"))
    assert nx.has_path(graph, ("Theme", "cpo_photonics"), ("Company", "company:TER"))
