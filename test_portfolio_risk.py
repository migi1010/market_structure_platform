from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.portfolio.portfolio_models import PortfolioAllocation, PortfolioThemeCandidate
from theme_intelligence.portfolio.portfolio_risk import PortfolioRiskScorer


def test_portfolio_risk_uses_weighted_risk_inputs() -> None:
    candidates = [
        PortfolioThemeCandidate("Glass Substrate", "glass_substrate", 90, 86, 82, 88, "High Conviction", "Early", 84, 20, 5, 30),
        PortfolioThemeCandidate("HBM", "hbm", 84, 82, 76, 80, "Medium Conviction", "Growth", 70, 50, 25, 45),
    ]
    allocations = [
        PortfolioAllocation("Glass Substrate", "glass_substrate", 60, "Strong score."),
        PortfolioAllocation("HBM", "hbm", 40, "Diversifier."),
    ]

    risk = PortfolioRiskScorer().score(allocations, candidates)

    assert risk.weighted_bubble_penalty == 32
    assert risk.weighted_crowding_penalty == 13
    assert risk.weighted_unresolved_bottleneck_penalty == 36
    assert risk.risk_score == 25.88
    assert risk.risk_profile == "Low"
