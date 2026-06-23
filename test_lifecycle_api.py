from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main
from theme_intelligence.lifecycle.lifecycle_engine import LifecycleEngine


def test_lifecycle_api_shape(monkeypatch) -> None:
    payload = {
        "themes": [
            {
                "theme_id": "glass_substrate",
                "name": "Glass Substrate",
                "name_zh": "玻璃基板",
                "lifecycle_stage": "Early",
                "lifecycle_confidence": 87,
                "expected_next_stage": "Growth",
                "time_window": "1-6 months",
                "final_ai_score": 88,
                "emerging_score": 84,
                "catalyst_score": 80,
                "entity_strength_score": 78,
                "crowding_proxy": 12,
                "stage_reason": "Evidence is accelerating.",
                "positive_signals": [],
                "negative_signals": [],
                "stage_risks": [],
                "next_stage_triggers": [],
                "history": [],
            }
        ]
    }

    monkeypatch.setattr(main, "get_theme_lifecycle", lambda: payload, raising=False)
    monkeypatch.setattr(main, "get_theme_lifecycle_detail", lambda theme_id: payload["themes"][0], raising=False)
    client = TestClient(main.app)

    summary = client.get("/api/theme/lifecycle")
    detail = client.get("/api/theme/lifecycle/glass_substrate")

    assert summary.status_code == 200
    assert detail.status_code == 200
    assert summary.json()["themes"][0]["lifecycle_stage"] == "Early"
    assert detail.json()["expected_next_stage"] == "Growth"


def test_discovery_includes_lifecycle(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "get_theme_discovery",
        lambda: {
            "themes": [
                {
                    "theme_id": "glass_substrate",
                    "name": "Glass Substrate",
                    "name_zh": "玻璃基板",
                    "ai_score": 88,
                    "discovery_score": 86,
                    "emerging_score": 84,
                    "catalyst_score": 80,
                    "entity_strength_score": 78,
                    "confidence_score": 82,
                    "crowding_proxy": 12,
                    "lifecycle_stage": "Early",
                    "lifecycle_confidence": 87,
                    "expected_next_stage": "Growth",
                    "time_window": "1-6 months",
                    "lifecycle_reason": "Evidence is accelerating.",
                    "key_catalysts": [],
                    "beneficiaries": [],
                    "brief": {"why_now": "", "signals": [], "risks": [], "watch_triggers": []},
                }
            ]
        },
        raising=False,
    )
    response = TestClient(main.app).get("/api/theme/discovery")

    row = response.json()["themes"][0]
    assert row["lifecycle_confidence"] == 87
    assert row["lifecycle_reason"]


class EmptyLifecycleRepository:
    def initialize(self) -> None:
        return None

    def get_discovery_scores(self, limit: int = 50) -> list[dict]:
        return []

    def get_bottlenecks(self) -> list:
        return []


def test_missing_lifecycle_detail_returns_null_fields() -> None:
    payload = LifecycleEngine(repository=EmptyLifecycleRepository()).lifecycle_detail("unknown_theme")

    assert payload["lifecycle_stage"] is None
    assert payload["lifecycle_confidence"] is None
    assert payload["expected_next_stage"] is None
    assert payload["time_window"] is None
