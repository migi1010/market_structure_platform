from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.portfolio.portfolio_diversifier import PortfolioDiversifier
from theme_intelligence.portfolio.portfolio_models import PortfolioAllocation, PortfolioThemeCandidate


def row(name: str, stage: str) -> PortfolioThemeCandidate:
    return PortfolioThemeCandidate(name, name.lower(), 80, 80, 80, 80, "High Conviction", stage, 80, 10, 0, 0)


def test_lifecycle_mix_and_balance_compare_actual_to_target() -> None:
    allocations = [
        PortfolioAllocation("Seed Theme", "seed", 10, ""),
        PortfolioAllocation("Early Theme", "early", 35, ""),
        PortfolioAllocation("Growth Theme", "growth", 35, ""),
        PortfolioAllocation("Expansion Theme", "expansion", 15, ""),
        PortfolioAllocation("Mature Theme", "mature", 5, ""),
    ]
    candidates = [
        row("Seed Theme", "Seed"),
        row("Early Theme", "Early"),
        row("Growth Theme", "Growth"),
        row("Expansion Theme", "Expansion"),
        row("Mature Theme", "Mature"),
    ]

    diversifier = PortfolioDiversifier()
    mix = diversifier.lifecycle_mix(allocations, candidates)
    balance = diversifier.lifecycle_balance_score(mix, "balanced_growth")

    assert mix == {"Seed": 10, "Early": 35, "Growth": 35, "Expansion": 15, "Mature": 5}
    assert balance == 100
