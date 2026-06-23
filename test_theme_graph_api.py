from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main
from theme_intelligence.graph.graph_engine import GraphEngine
from theme_intelligence.graph.graph_models import GraphEdge


def test_graph_api_routes_preserve_graph_contracts(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "get_theme_graph",
        lambda: {"edges": [{"relationship_type": "theme_overlap"}], "source_status": {"edge_count": 1}},
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "get_theme_graph_detail",
        lambda theme_id: {"theme_id": theme_id, "edges": [{"target_id": "glass_substrate"}]},
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "get_theme_overlap",
        lambda theme_id: {
            "theme_id": theme_id,
            "related_themes": [{"related_theme_id": "glass_substrate", "overlap_score": 62.5}],
        },
        raising=False,
    )
    client = TestClient(main.app)

    graph = client.get("/api/theme/graph")
    detail = client.get("/api/theme/graph/hbm")
    overlap = client.get("/api/theme/overlap/hbm")

    assert graph.status_code == 200
    assert detail.status_code == 200
    assert overlap.status_code == 200
    assert graph.json()["source_status"]["edge_count"] == 1
    assert detail.json()["theme_id"] == "hbm"
    assert overlap.json()["related_themes"][0]["overlap_score"] == 62.5


def test_unknown_theme_overlap_returns_honest_empty_relationships(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "get_theme_overlap",
        lambda theme_id: {"theme_id": theme_id, "related_themes": []},
        raising=False,
    )

    response = TestClient(main.app).get("/api/theme/overlap/not_a_theme")

    assert response.status_code == 200
    assert response.json() == {"theme_id": "not_a_theme", "related_themes": []}


def test_overlap_ranking_reads_persisted_overlap_edges() -> None:
    engine = GraphEngine()
    engine.graph_repository.get_theme_edges = lambda theme_id: [  # type: ignore[method-assign]
        GraphEdge("theme", theme_id, "theme", "glass_substrate", "theme_overlap", 62.5, "graph_overlap")
    ]
    engine.graph_repository.get_edges = lambda **kwargs: (_ for _ in ()).throw(AssertionError("all edges should not be loaded"))  # type: ignore[method-assign]

    payload = engine.get_overlap("hbm")

    assert payload["related_themes"][0]["related_theme_id"] == "glass_substrate"
    assert payload["related_themes"][0]["overlap_score"] == 62.5
