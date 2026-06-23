from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_builder_adds_process_links_dependencies_and_explicit_resolution_edges(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)

    build = IndustrialGraphBuilder(repository).build()
    edges = {edge.base_identity_key for edge in build.edges}

    assert (
        ("Technology", "technology:tsv"),
        "REQUIRES_PROCESS",
        ("Process", "process:tsv_etching"),
    ) in edges
    assert (
        ("Process", "process:wafer_bonding"),
        "PROCESS_PRECEDES_PROCESS",
        ("Process", "process:yield_inspection"),
    ) in edges
    assert (
        ("Process", "process:glass_processing"),
        "PROCESS_DEPENDS_ON_PROCESS",
        ("Process", "process:qualification"),
    ) in edges
    assert (
        ("Process", "process:wafer_bonding"),
        "PROCESS_LIMITED_BY_CONSTRAINT",
        ("Constraint", "constraint:hbm_stacking_yield"),
    ) in edges
    assert (
        ("Process", "process:wafer_bonding"),
        "PROCESS_RESOLVED_BY_COMPANY",
        ("Company", "company:LRCX"),
    ) in edges


def test_builder_does_not_infer_process_links_from_theme_level_records(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)

    build = IndustrialGraphBuilder(repository).build()
    process_edges = [
        edge for edge in build.edges if edge.source_key[0] == "Process"
    ]

    assert not any(
        edge.relationship_type == "PROCESS_RESOLVED_BY_COMPANY"
        and edge.target_key == ("Company", "company:AMAT")
        and edge.source_key == ("Process", "process:wafer_bonding")
        for edge in process_edges
    )
