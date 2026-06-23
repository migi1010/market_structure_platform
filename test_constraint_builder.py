from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_builder_adds_curated_constraints_and_explicit_company_semantics(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    build = IndustrialGraphBuilder(repository).build()
    edges = {edge.base_identity_key for edge in build.edges}

    hbm = ("Constraint", "constraint:hbm_capacity")
    assert (("Theme", "hbm"), "THEME_LIMITED_BY_CONSTRAINT", hbm) in edges
    for ticker in ("000660.KS", "MU", "005930.KS"):
        assert (("Company", f"company:{ticker}"), "COMPANY_EXPOSED_TO_CONSTRAINT", hbm) in edges
        assert not any(
            edge.relationship_type == "CONSTRAINT_RESOLVED_BY_COMPANY"
            and edge.target_key == ("Company", f"company:{ticker}")
            and edge.source_key == hbm
            for edge in build.edges
        )
    assert (
        ("Constraint", "constraint:cowos_capacity"),
        "CONSTRAINT_RESOLVED_BY_COMPANY",
        ("Company", "company:TSM"),
    ) in edges


def test_builder_migrates_supported_bottlenecks_and_skips_unsupported_categories(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    build = IndustrialGraphBuilder(repository).build()
    constraints = {node.canonical_key: node for node in build.nodes if node.node_type == "Constraint"}
    relationships = {edge.relationship_type for edge in build.edges}

    assert "constraint:glass_substrate_yield" in constraints
    assert constraints["constraint:glass_substrate_yield"].external_ids["category"] == "Yield Constraint"
    assert not any("deployment_complexity" in key or "software_use_case_maturity" in key for key in constraints)
    assert "LIMITS" not in relationships
    assert "RESOLVES" not in relationships
