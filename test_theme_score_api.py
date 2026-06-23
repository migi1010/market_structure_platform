from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main


def test_theme_score_api_endpoints_return_expected_shape(monkeypatch) -> None:
    payload = {
        "themes": [
            {
                "theme": "Glass Substrate",
                "theme_id": "glass_substrate",
                "ai_potential_score": 91,
                "research_importance": 95,
                "allocation_readiness": 88,
                "risk_adjusted_score": 84,
                "conviction_level": "High Conviction",
                "score_breakdown": {"discovery_score": 89},
            }
        ],
        "rankings": {},
    }
    monkeypatch.setattr(main, "get_theme_scores", lambda: payload, raising=False)
    monkeypatch.setattr(main, "get_theme_score_detail", lambda theme_id: payload["themes"][0], raising=False)

    client = TestClient(main.app)
    listing = client.get("/api/theme/scores")
    detail = client.get("/api/theme/scores/glass_substrate")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert listing.json()["themes"][0]["conviction_level"] == "High Conviction"
    assert detail.json()["score_breakdown"]["discovery_score"] == 89

