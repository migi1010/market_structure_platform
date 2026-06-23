from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.graph.graph_builder import GraphBuilder
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_graph_builder_uses_only_persisted_phase_10_evidence(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_graph_builder.sqlite3")
    repository.initialize()
    ThemeSeedLoader(repository=repository).load(recompute=True)

    edges = GraphBuilder(repository).build_base_edges()

    assert edges == sorted(edges, key=lambda edge: edge.sort_key)
    assert edges
    assert all(edge.evidence_source for edge in edges)
    assert {edge.relationship_type for edge in edges} >= {
        "theme_catalyst",
        "theme_bottleneck",
        "theme_beneficiary",
        "theme_controller",
        "theme_portfolio",
        "theme_supply_chain_role",
        "company_theme",
        "company_bottleneck",
        "portfolio_theme",
    }
    assert not any(edge.evidence_source == "synthetic" for edge in edges)


def test_graph_builder_emits_supply_roles_as_evidence_edges(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_graph_supply.sqlite3")
    repository.initialize()
    ThemeSeedLoader(repository=repository).load(recompute=True)

    edges = GraphBuilder(repository).build_base_edges()
    role_edges = [edge for edge in edges if edge.relationship_type == "theme_supply_chain_role"]

    assert role_edges
    assert all(edge.target_type == "supply_chain_role" for edge in role_edges)
    assert all(edge.evidence_source == "theme_entities" for edge in role_edges)


def test_graph_builder_uses_cross_theme_catalyst_identity() -> None:
    class CatalystRepository:
        def initialize(self) -> None:
            return None

        def get_entities(self) -> list[object]:
            return []

        def get_portfolios(self, limit: int = 100) -> list[object]:
            return []

        def get_bottlenecks(self) -> list[object]:
            return []

        def get_beneficiary_scores(self) -> list[object]:
            return []

        def get_catalysts(self) -> list[object]:
            return [
                SimpleNamespace(
                    theme_name="HBM",
                    catalyst_name="Capacity Expansion",
                    catalyst_type="capacity",
                    cluster_key="hbm:capacity_expansion:capacity",
                    catalyst_strength=80,
                ),
                SimpleNamespace(
                    theme_name="Glass Substrate",
                    catalyst_name="Capacity Expansion",
                    catalyst_type="capacity",
                    cluster_key="glass_substrate:capacity_expansion:capacity",
                    catalyst_strength=75,
                ),
            ]

    edges = GraphBuilder(CatalystRepository()).build_base_edges()  # type: ignore[arg-type]
    catalyst_targets = {
        edge.target_id for edge in edges if edge.relationship_type == "theme_catalyst"
    }

    assert catalyst_targets == {"capacity_expansion:capacity"}
