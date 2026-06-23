from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main


def test_beneficiary_api_endpoints_return_expected_shape(monkeypatch) -> None:
    payload = {
        "themes": [
            {
                "theme": "Glass Substrate",
                "theme_id": "glass_substrate",
                "top_beneficiaries": [
                    {
                        "ticker": "GLW",
                        "company": "Corning Inc.",
                        "beneficiary_type": "Direct Beneficiary",
                        "beneficiary_score": 92,
                        "allocation_score": 88,
                        "allocation_bucket": "High Conviction",
                    }
                ],
                "controllers": [],
                "resolution_enablers": [],
                "ecosystem_beneficiaries": [],
            }
        ]
    }
    monkeypatch.setattr(main, "get_theme_beneficiaries", lambda: payload, raising=False)
    monkeypatch.setattr(main, "get_theme_beneficiary_detail", lambda theme_id: payload["themes"][0], raising=False)

    client = TestClient(main.app)
    listing = client.get("/api/theme/beneficiaries")
    detail = client.get("/api/theme/beneficiaries/glass_substrate")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert listing.json()["themes"][0]["top_beneficiaries"][0]["ticker"] == "GLW"
    assert detail.json()["theme_id"] == "glass_substrate"

