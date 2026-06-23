from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.seeds import TARGET_SEED_THEMES, ThemeSeedLoader
from theme_intelligence.seeds.theme_seed_models import SeedSupplyChainConnection
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_builder_adds_evidence_backed_theme_role_company_paths(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)

    build = IndustrialGraphBuilder(repository).build()
    edge_keys = {edge.base_identity_key for edge in build.edges}

    assert (
        ("Theme", "hbm"),
        "PART_OF_SUPPLY_CHAIN",
        ("Industry", "supply_chain:hbm:manufacturing"),
    ) in edge_keys
    assert (
        ("Industry", "supply_chain:hbm:manufacturing"),
        "SUPPLY_CHAIN_ROLE",
        ("Company", "company:MU"),
    ) in edge_keys
    relationships = {edge.relationship_type for edge in build.edges}
    assert {"CONTROLS", "ENABLES"} <= relationships
    assert {"LIMITS", "RESOLVES"}.isdisjoint(relationships)
    assert all(
        any(link.edge_key == edge.base_identity_key for link in build.edge_evidence)
        for edge in build.edges
    )


def test_builder_emits_company_edges_only_from_explicit_curated_connections(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    hbm = next(theme for theme in TARGET_SEED_THEMES if theme.theme_id == "hbm")
    connected_hbm = replace(
        hbm,
        supply_chain_connections=(
            SeedSupplyChainConnection(
                source_ticker="MU",
                relationship_type="SUPPLIES",
                target_ticker="NVDA",
                citation="Curated test evidence: Micron supplies HBM to NVIDIA.",
            ),
        ),
    )

    baseline = IndustrialGraphBuilder(repository).build()
    enriched = IndustrialGraphBuilder(repository, themes=(connected_hbm,)).build()

    assert not any(edge.relationship_type == "SUPPLIES" for edge in baseline.edges)
    assert (
        ("Company", "company:MU"),
        "SUPPLIES",
        ("Company", "company:NVDA"),
    ) in {edge.base_identity_key for edge in enriched.edges}
    assert not any(
        edge.source_key == ("Theme", "hbm")
        and edge.target_key == ("Company", "company:TSM")
        for edge in baseline.edges
    )
