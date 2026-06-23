from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main
from theme_intelligence.portfolio.portfolio_engine import PortfolioEngine


def test_theme_portfolio_api_shape(monkeypatch) -> None:
    payload = {
        "portfolios": [
            {
                "portfolio_type": "balanced_growth",
                "portfolio_name": "Balanced Growth Theme Portfolio",
                "portfolio_score": 86,
                "risk_profile": "Moderate",
                "bubble_exposure": 28,
                "lifecycle_mix": {"Early": 40, "Growth": 35, "Expansion": 20, "Mature": 5},
                "themes": [{"theme": "Glass Substrate", "theme_id": "glass_substrate", "weight": 30, "allocation_rationale": "High score."}],
                "why_selected": [],
                "why_excluded": [],
                "risk_sources": [],
                "bubble_sources": [],
                "diversification_notes": [],
            }
        ]
    }
    monkeypatch.setattr(main, "get_theme_portfolios", lambda: payload, raising=False)
    monkeypatch.setattr(main, "get_theme_portfolio_detail", lambda portfolio_type: payload["portfolios"][0], raising=False)

    client = TestClient(main.app)
    listing = client.get("/api/theme/portfolio")
    detail = client.get("/api/theme/portfolio/balanced_growth")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert listing.json()["portfolios"][0]["portfolio_type"] == "balanced_growth"
    assert detail.json()["themes"][0]["weight"] == 30


def test_portfolio_default_reads_persisted_rows_without_recomputing() -> None:
    class Portfolio:
        portfolio_type = "balanced_growth"

        def to_api(self) -> dict:
            return {"portfolio_type": self.portfolio_type, "portfolio_score": 80}

    class Repository:
        def initialize(self) -> None:
            return None

        def get_portfolios(self, limit: int = 20) -> list[Portfolio]:
            return [Portfolio()]

    engine = PortfolioEngine(repository=Repository())
    engine.run = lambda: (_ for _ in ()).throw(AssertionError("run should be explicit"))  # type: ignore[method-assign]
    engine.ranker.rank = lambda rows: []

    payload = engine.get_portfolios()

    assert payload["portfolios"][0]["portfolio_type"] == "balanced_growth"
    assert payload["source_status"]["source"] == "persisted"
