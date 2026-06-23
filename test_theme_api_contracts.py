from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.graph.graph_engine import GraphEngine
from theme_intelligence.storage.theme_repository import ThemeRepository


def _seeded_client(tmp_path: Path, monkeypatch: Any) -> TestClient:
    repository = ThemeRepository(tmp_path / "theme_api_contract.sqlite3")
    repository.initialize()
    ThemeSeedLoader(repository=repository).load(recompute=True)

    def intelligence(limit: int | None = None) -> dict[str, Any]:
        rows = repository.get_top_scores(limit) if limit else repository.get_scores()
        return {
            "themes": [
                {
                    "name": row["name"],
                    "mention_score": row["mention_score"],
                    "velocity_score": row["velocity_score"],
                    "sentiment_score": row["sentiment_score"],
                    "lifecycle_stage": row["lifecycle_stage"],
                    "lifecycle_confidence": row["lifecycle_confidence"],
                    "total_score": row["total_score"],
                }
                for row in rows
            ],
            "source_status": {"source": "seeded_contract"},
        }

    def discovery(limit: int = 20) -> dict[str, Any]:
        return {"themes": repository.get_discovery_scores(limit=limit), "source_status": {"source": "seeded_contract"}}

    monkeypatch.setattr(main, "get_theme_intelligence_detail", lambda theme_id: __import__("theme_intelligence.aggregate", fromlist=["ThemeIntelligenceAggregateService"]).ThemeIntelligenceAggregateService(repository=repository).get_theme(theme_id), raising=False)
    monkeypatch.setattr(main, "get_theme_catalyst_detail", lambda theme_id: __import__("theme_intelligence.catalysts.catalyst_engine", fromlist=["CatalystEngine"]).CatalystEngine(repository=repository).get_detail(theme_id), raising=False)
    monkeypatch.setattr(main, "get_theme_bottleneck_detail", lambda theme_id: __import__("theme_intelligence.bottlenecks.bottleneck_engine", fromlist=["BottleneckEngine"]).BottleneckEngine(repository=repository).get_detail(theme_id), raising=False)
    monkeypatch.setattr(main, "get_theme_beneficiary_detail", lambda theme_id: __import__("theme_intelligence.beneficiaries.beneficiary_engine", fromlist=["BeneficiaryEngine"]).BeneficiaryEngine(repository=repository).get_detail(theme_id), raising=False)
    monkeypatch.setattr(main, "get_theme_score_detail", lambda theme_id: __import__("theme_intelligence.theme_score.theme_score_engine", fromlist=["ThemeScoreEngine"]).ThemeScoreEngine(repository=repository).get_score_detail(theme_id), raising=False)
    monkeypatch.setattr(main, "get_theme_lifecycle_detail", lambda theme_id: __import__("theme_intelligence.lifecycle.lifecycle_engine", fromlist=["LifecycleEngine"]).LifecycleEngine(repository=repository).lifecycle_detail(theme_id), raising=False)
    monkeypatch.setattr(main, "get_theme_portfolio_detail", lambda portfolio_type: __import__("theme_intelligence.portfolio.portfolio_engine", fromlist=["PortfolioEngine"]).PortfolioEngine(repository=repository).get_detail(portfolio_type), raising=False)
    monkeypatch.setattr(main, "get_theme_intelligence", lambda: intelligence(), raising=False)
    monkeypatch.setattr(main, "get_top_theme_intelligence", lambda limit=20: intelligence(limit=limit), raising=False)
    monkeypatch.setattr(main, "get_theme_discovery", lambda: discovery(), raising=False)
    monkeypatch.setattr(main, "get_theme_lifecycle", lambda: __import__("theme_intelligence.lifecycle.lifecycle_engine", fromlist=["LifecycleEngine"]).LifecycleEngine(repository=repository).lifecycle_summary(), raising=False)
    monkeypatch.setattr(main, "get_theme_catalysts", lambda: __import__("theme_intelligence.catalysts.catalyst_engine", fromlist=["CatalystEngine"]).CatalystEngine(repository=repository).get_catalysts(use_cache=False), raising=False)
    monkeypatch.setattr(main, "get_theme_bottlenecks", lambda: __import__("theme_intelligence.bottlenecks.bottleneck_engine", fromlist=["BottleneckEngine"]).BottleneckEngine(repository=repository).get_bottlenecks(use_cache=False), raising=False)
    monkeypatch.setattr(main, "get_theme_beneficiaries", lambda: __import__("theme_intelligence.beneficiaries.beneficiary_engine", fromlist=["BeneficiaryEngine"]).BeneficiaryEngine(repository=repository).get_beneficiaries(use_cache=False), raising=False)
    monkeypatch.setattr(main, "get_theme_scores", lambda: __import__("theme_intelligence.theme_score.theme_score_engine", fromlist=["ThemeScoreEngine"]).ThemeScoreEngine(repository=repository).get_scores(), raising=False)
    monkeypatch.setattr(main, "get_theme_portfolios", lambda: __import__("theme_intelligence.portfolio.portfolio_engine", fromlist=["PortfolioEngine"]).PortfolioEngine(repository=repository).get_portfolios(), raising=False)
    monkeypatch.setattr(main, "get_theme_graph", lambda: GraphEngine(repository).get_graph(), raising=False)
    monkeypatch.setattr(main, "get_theme_graph_detail", lambda theme_id: GraphEngine(repository).get_theme_graph(theme_id), raising=False)
    monkeypatch.setattr(main, "get_theme_overlap", lambda theme_id: GraphEngine(repository).get_overlap(theme_id), raising=False)
    return TestClient(main.app)


def test_phase_10_endpoints_have_stable_response_shapes(tmp_path: Path, monkeypatch: Any) -> None:
    client = _seeded_client(tmp_path, monkeypatch)
    endpoints = [
        "/api/theme/intelligence",
        "/api/theme/intelligence/top",
        "/api/theme/discovery",
        "/api/theme/lifecycle",
        "/api/theme/lifecycle/glass_substrate",
        "/api/theme/catalysts",
        "/api/theme/catalysts/glass_substrate",
        "/api/theme/bottlenecks",
        "/api/theme/bottlenecks/glass_substrate",
        "/api/theme/beneficiaries",
        "/api/theme/beneficiaries/glass_substrate",
        "/api/theme/scores",
        "/api/theme/scores/glass_substrate",
        "/api/theme/portfolio",
        "/api/theme/portfolio/balanced_growth",
        "/api/theme/intelligence/glass_substrate",
        "/api/theme/graph",
        "/api/theme/graph/glass_substrate",
        "/api/theme/overlap/glass_substrate",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200, endpoint
        assert isinstance(response.json(), dict), endpoint


def test_aggregate_missing_theme_returns_honest_empty_sections(tmp_path: Path, monkeypatch: Any) -> None:
    client = _seeded_client(tmp_path, monkeypatch)

    payload = client.get("/api/theme/intelligence/not_a_theme").json()

    assert payload["theme_id"] == "not_a_theme"
    assert payload["score"] == {}
    assert payload["discovery"] == {}
    assert payload["catalysts"]["top_catalysts"] == []
    assert payload["bottlenecks"]["primary_bottleneck"] is None
    assert payload["beneficiaries"]["top_beneficiaries"] == []
    assert payload["portfolio_context"]["portfolios"] == []
    assert payload["relationship_intelligence"]["related_themes"] == []
