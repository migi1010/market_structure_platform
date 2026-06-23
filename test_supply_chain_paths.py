from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.seeds import TARGET_SEED_THEMES, ThemeSeedLoader
from theme_intelligence.seeds.theme_seed_models import SeedSupplyChainConnection
from theme_intelligence.storage.theme_repository import ThemeRepository


def _repository(tmp_path: Path):
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    service.build_and_activate()
    return service.repository


def test_supply_chain_path_traversal_is_deterministic_and_bounded(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source = ("Theme", "hbm")
    target = ("Company", "company:MU")

    first = repository.get_dependency_paths(source, target, max_depth=2)
    second = repository.get_dependency_paths(source, target, max_depth=2)

    assert first == second == [(
        ("Theme", "hbm"),
        ("Industry", "supply_chain:hbm:manufacturing"),
        ("Company", "company:MU"),
    )]
    assert repository.get_dependency_paths(source, target, max_depth=1) == []


def test_upstream_and_downstream_company_traversal_succeeds(tmp_path: Path) -> None:
    theme_repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=theme_repository).load(
        recompute=False,
        build_industrial_graph=False,
    )
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
    service = IndustrialGraphSnapshotService(theme_repository)
    service.activate(
        service.stage(
            IndustrialGraphBuilder(
                theme_repository,
                themes=(connected_hbm,),
            ).build()
        ).build_version
    )
    repository = service.repository

    downstream = repository.get_downstream_companies(("Company", "company:MU"), max_depth=1)
    upstream = repository.get_upstream_companies(("Company", "company:NVDA"), max_depth=1)

    assert downstream == [("Company", "company:NVDA")]
    assert upstream == [("Company", "company:MU")]
    assert repository.get_supply_chain_neighbors(
        ("Theme", "hbm"),
        relationship_types={"PART_OF_SUPPLY_CHAIN"},
        direction="out",
        max_depth=1,
    ) == [("Industry", "supply_chain:hbm:end_customer"), ("Industry", "supply_chain:hbm:equipment_supplier"), ("Industry", "supply_chain:hbm:manufacturing")]
