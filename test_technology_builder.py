from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_builder_adds_evidence_backed_theme_technology_edges(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)

    build = IndustrialGraphBuilder(repository).build()
    edges = {edge.base_identity_key for edge in build.edges}

    assert (
        ("Theme", "hbm"),
        "USES_TECHNOLOGY",
        ("Technology", "technology:tsv"),
    ) in edges
    assert (
        ("Theme", "glass_substrate"),
        "USES_TECHNOLOGY",
        ("Technology", "technology:glass_core_technology"),
    ) in edges
    assert (
        ("Theme", "cpo_photonics"),
        "USES_TECHNOLOGY",
        ("Technology", "technology:co_packaged_optics"),
    ) in edges
    assert all(
        any(link.edge_key == edge.base_identity_key for link in build.edge_evidence)
        for edge in build.edges
    )
