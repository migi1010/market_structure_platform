from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_models import (
    NODE_TYPES,
    IndustrialGraphBuild,
    IndustrialGraphNode,
    normalize_canonical_key,
)
from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_node_taxonomy_and_canonical_normalization() -> None:
    assert len(NODE_TYPES) == 17
    assert normalize_canonical_key("Glass Substrate") == "glass_substrate"
    assert normalize_canonical_key("NVDA", node_type="Company") == "company:NVDA"

    node = IndustrialGraphNode(
        node_type="Theme",
        canonical_key="Glass Substrate",
        display_name="Glass Substrate",
        aliases=("substrate", "glass", "glass"),
        external_ids={"z": "2", "a": "1"},
    )

    assert node.canonical_key == "glass_substrate"
    assert node.aliases == ("glass", "substrate")
    assert list(node.external_ids) == ["a", "z"]
    assert node.identity_key == ("Theme", "glass_substrate")


def test_invalid_node_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported node type"):
        IndustrialGraphNode("Catalyst", "capacity", "Capacity")


def test_graph_schema_is_idempotent_and_preserves_phase10_graph(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    repository.initialize()
    repository.initialize()

    with sqlite3.connect(repository.db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        node_indexes = {row[1] for row in conn.execute("PRAGMA index_list(graph_nodes)")}

    assert {
        "graph_nodes",
        "graph_edges",
        "graph_evidence",
        "graph_edge_evidence",
        "graph_snapshots",
        "theme_graph_edges",
    } <= tables
    assert {
        "idx_graph_nodes_type",
        "idx_graph_nodes_canonical_key",
        "idx_graph_nodes_status",
    } <= node_indexes


def test_repository_reuses_canonical_node_and_validator_rejects_build_duplicates(tmp_path: Path) -> None:
    repository = IndustrialGraphRepository(ThemeRepository(tmp_path / "graph.sqlite3"))
    node = IndustrialGraphNode("Theme", "HBM", "HBM")
    with repository.connect() as conn:
        first = repository.resolve_nodes(conn, [node])
        second = repository.resolve_nodes(conn, [node])
        conn.commit()

    assert first[node.identity_key] == second[node.identity_key]
    duplicate_build = IndustrialGraphBuild(nodes=(node, node))
    with pytest.raises(GraphValidationError, match="duplicate canonical node"):
        GraphValidator().validate(duplicate_build)

