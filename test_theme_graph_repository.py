from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.graph.graph_models import GraphEdge
from theme_intelligence.graph.graph_repository import GraphRepository
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_graph_repository_creates_typed_unique_schema_and_replaces_edges(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_graph.sqlite3")
    repository.initialize()
    graph_repository = GraphRepository(repository)
    first = [
        GraphEdge("theme", "hbm", "company", "NVDA", "theme_company", 88, "theme_entities"),
        GraphEdge("company", "hbm", "theme", "NVDA", "theme_company", 77, "test"),
    ]

    assert graph_repository.replace_edges(first) == 2
    assert graph_repository.replace_edges([
        GraphEdge("theme", "glass_substrate", "company", "INTC", "theme_company", 72, "theme_entities")
    ]) == 1

    edges = graph_repository.get_edges()
    assert [(edge.source_id, edge.target_id) for edge in edges] == [("glass_substrate", "INTC")]

    with sqlite3.connect(repository.db_path) as conn:
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(theme_graph_edges)").fetchall()}
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'idx_theme_graph_edges_unique'"
        ).fetchone()[0]

    assert {
        "idx_theme_graph_edges_source",
        "idx_theme_graph_edges_target",
        "idx_theme_graph_edges_relationship",
        "idx_theme_graph_edges_unique",
    } <= indexes
    assert "source_type, source_id, target_type, target_id, relationship_type" in sql


def test_graph_repository_filters_edges_for_a_theme(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_graph.sqlite3")
    repository.initialize()
    graph_repository = GraphRepository(repository)
    graph_repository.replace_edges([
        GraphEdge("theme", "hbm", "catalyst", "hbm:blackwell", "theme_catalyst", 91, "theme_catalysts"),
        GraphEdge("theme", "glass_substrate", "catalyst", "glass:yield", "theme_catalyst", 74, "theme_catalysts"),
        GraphEdge("theme", "hbm", "theme", "ai_infrastructure", "theme_overlap", 62, "graph_overlap"),
    ])

    edges = graph_repository.get_theme_edges("hbm")

    assert len(edges) == 2
    assert {edge.relationship_type for edge in edges} == {"theme_catalyst", "theme_overlap"}
