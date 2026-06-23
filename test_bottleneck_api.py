from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main


def test_bottleneck_api_endpoints_return_expected_shape(monkeypatch) -> None:
    payload = {
        "themes": [
            {
                "theme": "Glass Substrate",
                "theme_id": "glass_substrate",
                "primary_bottleneck": {"name": "Yield", "type": "Yield Constraint", "severity_score": 88},
                "secondary_bottlenecks": [],
                "controllers": [],
                "beneficiaries": [],
                "resolution_probability": 65,
                "why_it_matters": "Yield limits scalable adoption.",
                "what_fixes_it": [],
                "what_to_monitor": [],
            }
        ]
    }
    monkeypatch.setattr(main, "get_theme_bottlenecks", lambda: payload, raising=False)
    monkeypatch.setattr(main, "get_theme_bottleneck_detail", lambda theme_id: payload["themes"][0], raising=False)

    client = TestClient(main.app)
    listing = client.get("/api/theme/bottlenecks")
    detail = client.get("/api/theme/bottlenecks/glass_substrate")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert listing.json()["themes"][0]["primary_bottleneck"]["name"] == "Yield"
    assert detail.json()["theme_id"] == "glass_substrate"

