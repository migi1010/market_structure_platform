from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main
from theme_intelligence.aggregate import ThemeIntelligenceAggregateService
from theme_intelligence.theme_score.theme_score_models import ThemeFinalScore


class EmptyRepository:
    def initialize(self) -> None:
        return None

    def get_final_scores(self, limit: int = 100) -> list[Any]:
        return []

    def get_discovery_scores(self, limit: int = 100) -> list[dict[str, Any]]:
        return []

    def get_catalysts(self) -> list[Any]:
        return []

    def get_bottlenecks(self) -> list[Any]:
        return []

    def get_beneficiary_scores(self) -> list[Any]:
        return []

    def get_portfolios(self, limit: int = 20) -> list[Any]:
        return []

    def get_score_history(self, theme_name: str) -> list[dict[str, Any]]:
        return []

    def get_entities(self) -> list[Any]:
        return []


class PopulatedRepository(EmptyRepository):
    def get_final_scores(self, limit: int = 100) -> list[Any]:
        return [
            ThemeFinalScore(
                "Glass Substrate",
                91,
                88,
                76,
                84,
                "High Conviction",
                score_components={"lifecycle_stage": "Early", "confidence_score": 87},
            )
        ]

    def get_discovery_scores(self, limit: int = 100) -> list[dict[str, Any]]:
        return [
            {
                "theme_id": "glass_substrate",
                "name": "Glass Substrate",
                "ai_score": 90,
                "discovery_score": 89,
                "emerging_score": 86,
                "lifecycle_stage": "Early",
                "expected_next_stage": "Growth",
                "time_window": "1-3 months",
                "brief": {"why_now": "Evidence is accelerating.", "signals": [], "risks": [], "watch_triggers": []},
            }
        ]


class StubGraphEngine:
    def relationship_intelligence(self, theme_id: str) -> dict[str, Any]:
        return {
            "related_themes": [{"related_theme_id": "hbm", "overlap_score": 62.5}],
            "shared_controllers": ["TSM"],
            "shared_beneficiaries": ["NVDA"],
            "portfolio_exposure": ["balanced_growth"],
            "shared_supply_chain_roles": ["packaging"],
        }


def test_aggregate_service_returns_all_sections_from_persisted_data() -> None:
    payload = ThemeIntelligenceAggregateService(
        repository=PopulatedRepository(),
        graph_engine=StubGraphEngine(),
    ).get_theme("Glass Substrate")

    assert payload["theme_id"] == "glass_substrate"
    assert payload["score"]["ai_potential_score"] == 91
    assert payload["discovery"]["emerging_score"] == 86
    assert set(payload) >= {"score", "discovery", "lifecycle", "catalysts", "bottlenecks", "beneficiaries", "portfolio_context", "supply_chain", "relationship_intelligence"}
    assert payload["relationship_intelligence"]["related_themes"][0]["related_theme_id"] == "hbm"


def test_aggregate_service_missing_theme_degrades_with_empty_sections() -> None:
    payload = ThemeIntelligenceAggregateService(
        repository=EmptyRepository(),
        graph_engine=StubGraphEngine(),
    ).get_theme("unknown_theme")

    assert payload["theme_id"] == "unknown_theme"
    assert payload["score"] == {}
    assert payload["discovery"] == {}
    assert payload["catalysts"]["top_catalysts"] == []
    assert payload["bottlenecks"]["primary_bottleneck"] is None
    assert payload["beneficiaries"]["top_beneficiaries"] == []
    assert payload["portfolio_context"]["portfolios"] == []
    assert payload["lifecycle"]["lifecycle_stage"] is None
    assert payload["lifecycle"]["lifecycle_confidence"] is None
    assert payload["lifecycle"]["expected_next_stage"] is None
    assert payload["supply_chain"]["layers"] == []
    assert "relationship_intelligence" in payload


def test_theme_intelligence_aggregate_api_shape(monkeypatch) -> None:
    payload = ThemeIntelligenceAggregateService(
        repository=PopulatedRepository(),
        graph_engine=StubGraphEngine(),
    ).get_theme("glass_substrate")
    monkeypatch.setattr(main, "get_theme_intelligence_detail", lambda theme_id: payload, raising=False)

    response = TestClient(main.app).get("/api/theme/intelligence/glass_substrate")

    assert response.status_code == 200
    assert response.json()["score"]["conviction_level"] == "High Conviction"
    assert "supply_chain" in response.json()
    assert "relationship_intelligence" in response.json()
