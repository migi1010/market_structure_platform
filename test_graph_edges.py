from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_models import (
    RELATIONSHIP_TYPES,
    IndustrialGraphEdge,
    IndustrialGraphNode,
)
from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_relationship_taxonomy_and_directional_identity() -> None:
    assert len(RELATIONSHIP_TYPES) == 52
    edge = IndustrialGraphEdge(
        source_key=("Constraint", "constraint:hbm:stacking_yield"),
        relationship_type="LIMITS",
        target_key=("Theme", "hbm"),
        confidence_score=72,
        dependency_strength=68,
        build_version="build-1",
        valid_from="2026-06-12T00:00:00+00:00",
    )
    assert edge.identity_key == (
        ("Constraint", "constraint:hbm:stacking_yield"),
        "LIMITS",
        ("Theme", "hbm"),
        "2026-06-12T00:00:00+00:00",
    )
    with pytest.raises(ValueError, match="Unsupported relationship"):
        IndustrialGraphEdge(("Theme", "hbm"), "RELATED_TO", ("Company", "company:MU"))


def test_repository_rejects_orphan_edges_and_filters_active_build(tmp_path: Path) -> None:
    repository = IndustrialGraphRepository(ThemeRepository(tmp_path / "graph.sqlite3"))
    theme = IndustrialGraphNode("Theme", "hbm", "HBM")
    constraint = IndustrialGraphNode("Constraint", "constraint:hbm:yield", "Yield")
    with repository.connect() as conn:
        node_ids = repository.resolve_nodes(conn, [theme, constraint])
        edge = IndustrialGraphEdge(
            constraint.identity_key,
            "LIMITS",
            theme.identity_key,
            build_version="build-1",
            valid_from="2026-06-12T00:00:00+00:00",
        )
        repository.insert_edges(conn, [edge], node_ids)
        conn.execute("UPDATE graph_edges SET status='active' WHERE build_version='build-1'")
        conn.commit()

    assert len(repository.get_edges()) == 1
    with repository.connect() as conn:
        with pytest.raises((KeyError, sqlite3.IntegrityError)):
            repository.insert_edges(
                conn,
                [IndustrialGraphEdge(("Constraint", "missing"), "LIMITS", theme.identity_key)],
                node_ids,
            )


def test_graph_edge_indexes_exist(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    repository.initialize()
    with sqlite3.connect(repository.db_path) as conn:
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(graph_edges)")}
    assert {
        "idx_graph_edges_source",
        "idx_graph_edges_target",
        "idx_graph_edges_relationship",
        "idx_graph_edges_build_status",
    } <= indexes
