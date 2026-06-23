from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_networkx_export_supports_constraint_dependency_and_company_tracing(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    service.build_and_activate()
    graph = service.repository.export_to_networkx(relationship_types={
        "THEME_LIMITED_BY_CONSTRAINT", "PROCESS_LIMITED_BY_CONSTRAINT",
        "EQUIPMENT_LIMITED_BY_CONSTRAINT", "CONSTRAINT_DEPENDS_ON_PROCESS",
        "CONSTRAINT_DEPENDS_ON_EQUIPMENT", "CONSTRAINT_RESOLVED_BY_COMPANY",
        "COMPANY_EXPOSED_TO_CONSTRAINT",
    })
    assert isinstance(graph, nx.MultiDiGraph)
    assert nx.has_path(graph, ("Theme", "glass_substrate"), ("Process", "process:glass_processing"))
    assert nx.has_path(graph, ("Constraint", "constraint:cowos_capacity"), ("Company", "company:TSM"))
