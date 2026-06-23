from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main


def test_catalyst_api_endpoints_return_summary(monkeypatch) -> None:
    payload = {
        "themes": [
            {
                "theme": "Glass Substrate",
                "theme_id": "glass_substrate",
                "top_catalysts": [{"name": "Intel Packaging Expansion", "type": "CapEx Expansion", "impact_score": 92, "confidence_score": 87}],
                "top_positive_catalysts": [],
                "top_risks": [],
                "top_future_catalysts": [{"name": "HBM4 Adoption"}],
                "future_catalysts": [{"name": "HBM4 Adoption"}],
                "key_blockers": [{"name": "Yield Risk"}],
            }
        ]
    }

    monkeypatch.setattr(main, "get_theme_catalysts", lambda: payload, raising=False)
    monkeypatch.setattr(main, "get_theme_catalyst_detail", lambda theme_id: payload["themes"][0], raising=False)

    client = TestClient(main.app)
    listing = client.get("/api/theme/catalysts")
    detail = client.get("/api/theme/catalysts/glass_substrate")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert listing.json()["themes"][0]["top_catalysts"][0]["name"] == "Intel Packaging Expansion"
    assert detail.json()["future_catalysts"][0]["name"] == "HBM4 Adoption"

