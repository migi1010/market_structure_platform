from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main
from theme_intelligence.discovery.discovery_engine import DiscoveryEngine


def test_theme_discovery_api_response_shape(monkeypatch) -> None:
    def fake_discovery() -> dict:
        return {
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
                    "expected_next_stage": "Growth",
                    "time_window": "1-3 months",
                    "key_catalysts": [],
                    "beneficiaries": [],
                    "brief": {"why_now": "Recent evidence accelerated.", "signals": [], "risks": [], "watch_triggers": []},
                }
            ]
        }

    monkeypatch.setattr(main, "get_theme_discovery", fake_discovery, raising=False)
    client = TestClient(main.app)

    response = client.get("/api/theme/discovery")

    assert response.status_code == 200
    row = response.json()["themes"][0]
    assert row["theme_id"] == "glass_substrate"
    assert row["lifecycle_stage"] == "Early"
    assert "brief" in row


def test_discovery_default_reads_persisted_rows_without_collecting() -> None:
    class Repository:
        def initialize(self) -> None:
            return None

        def get_discovery_scores(self, limit: int = 20) -> list[dict]:
            return [{"theme_id": "hbm", "name": "HBM", "ai_score": 88}]

    engine = DiscoveryEngine(repository=Repository())
    engine.refresh = lambda limit=20: (_ for _ in ()).throw(AssertionError("refresh should be explicit"))  # type: ignore[method-assign]

    payload = engine.get_discovery()

    assert payload["themes"][0]["theme_id"] == "hbm"
    assert payload["source_status"]["source"] == "persisted"
