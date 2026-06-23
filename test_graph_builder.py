from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.industrial_graph.graph_snapshot import build_checksum
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_builder_is_deterministic_and_emits_only_conservative_edges(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    builder = IndustrialGraphBuilder(repository)

    first = builder.build()
    second = builder.build()

    assert first.nodes == second.nodes
    assert first.edges == second.edges
    assert first.evidence == second.evidence
    assert first.edge_evidence == second.edge_evidence
    assert first.source_watermark == second.source_watermark
    assert build_checksum(first) == build_checksum(second)
    relationships = {edge.relationship_type for edge in first.edges}
    assert {"CONTROLS", "ENABLES"} <= relationships
    assert {"LIMITS", "RESOLVES"}.isdisjoint(relationships)
    assert {
        "PART_OF_SUPPLY_CHAIN",
        "SUPPLY_CHAIN_ROLE",
    } <= {edge.relationship_type for edge in first.edges}
    assert all(link.evidence_key for link in first.edge_evidence)
    assert len(first.edge_evidence) >= len(first.edges)
    assert not any(
        forbidden in evidence.source_type.lower()
        for evidence in first.evidence
        for forbidden in ("quote", "yfinance", "frontend", "runtime_llm", "endpoint_cache", "portfolio")
    )


def test_builder_does_not_fabricate_inverse_or_supplier_edges(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    build = IndustrialGraphBuilder(repository).build()

    relationships = {edge.relationship_type for edge in build.edges}
    assert "SUPPLIED_BY" not in relationships
    assert "PRODUCED_BY" not in relationships
    assert "CUSTOMER_OF" not in relationships
    for edge in build.edges:
        assert not any(
            candidate.source_key == edge.target_key
            and candidate.target_key == edge.source_key
            and candidate.relationship_type == edge.relationship_type
            for candidate in build.edges
        )
