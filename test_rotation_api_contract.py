from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main


def test_rotation_api_returns_stable_snapshot_contract(monkeypatch) -> None:
    payload = {
        "status": "partial",
        "source": "sector_etf_quotes",
        "updated_at": "2026-06-13T00:00:00Z",
        "market_regime": "mixed",
        "risk_appetite": "neutral",
        "volatility_state": "unavailable",
        "rotation_bias": "mixed",
        "leaders": [],
        "laggards": [],
        "sector_ranking": [],
        "selected_sector": None,
        "diagnostics": [],
        "theme_links": [],
        "data_quality": {"available_sectors": 0, "total_sectors": 11},
    }
    monkeypatch.setattr(main, "_sector_rotation_snapshot_response", lambda: payload)
    monkeypatch.setattr(main, "get_cached_value", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "set_cached_value", lambda *args, **kwargs: None)

    response = TestClient(main.app).get("/sector/rotation")

    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {
        "status",
        "source",
        "updated_at",
        "market_regime",
        "risk_appetite",
        "volatility_state",
        "rotation_bias",
        "leaders",
        "laggards",
        "sector_ranking",
        "selected_sector",
        "diagnostics",
        "theme_links",
        "data_quality",
    }

