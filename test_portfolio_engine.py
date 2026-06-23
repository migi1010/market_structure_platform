from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_score.theme_score_models import ThemeFinalScore
from theme_intelligence.portfolio.portfolio_engine import PortfolioEngine


class FakeRepository:
    def __init__(self) -> None:
        self.saved: list[Any] = []

    def initialize(self) -> None:
        return None

    def get_final_scores(self, limit: int = 100) -> list[ThemeFinalScore]:
        return [
            ThemeFinalScore(
                "Glass Substrate",
                92,
                90,
                88,
                91,
                "Very High Conviction",
                score_components={
                    "lifecycle_stage": "Early",
                    "confidence_score": 86,
                    "bubble_penalty": 10,
                    "crowding_proxy": 20,
                    "risk_penalties": {"crowding_penalty": 0, "unresolved_bottleneck_penalty": 20},
                },
            ),
            ThemeFinalScore(
                "HBM",
                88,
                86,
                82,
                84,
                "High Conviction",
                score_components={
                    "lifecycle_stage": "Growth",
                    "confidence_score": 82,
                    "bubble_penalty": 18,
                    "risk_penalties": {"crowding_penalty": 4, "unresolved_bottleneck_penalty": 24},
                },
            ),
            ThemeFinalScore(
                "Mature AI",
                78,
                70,
                80,
                74,
                "Medium Conviction",
                score_components={
                    "lifecycle_stage": "Mature",
                    "confidence_score": 76,
                    "bubble_penalty": 62,
                    "risk_penalties": {"crowding_penalty": 20, "unresolved_bottleneck_penalty": 12},
                },
            ),
        ]

    def get_bottlenecks(self) -> list[Any]:
        return []

    def get_beneficiary_scores(self) -> list[Any]:
        return []

    def save_portfolios(self, rows: list[Any]) -> int:
        self.saved = rows
        return len(rows)

    def get_portfolios(self, limit: int = 20) -> list[Any]:
        return []


def test_portfolio_engine_builds_all_objectives_from_persisted_scores_only() -> None:
    repo = FakeRepository()
    payload = PortfolioEngine(repository=repo).get_portfolios(use_cache=False)

    assert {row["portfolio_type"] for row in payload["portfolios"]} == {
        "maximum_conviction",
        "balanced_growth",
        "low_bubble",
        "early_opportunity",
        "institutional",
    }
    assert repo.saved
    assert round(sum(payload["portfolios"][0]["themes"][index]["weight"] for index in range(len(payload["portfolios"][0]["themes"]))), 6) == 100
