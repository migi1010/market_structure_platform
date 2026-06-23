from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.portfolio.portfolio_diversifier import PortfolioDiversifier
from theme_intelligence.portfolio.portfolio_models import PortfolioAllocation, PortfolioThemeCandidate


def candidate(name: str, stage: str, bottleneck: str = "", beneficiary: str = "") -> PortfolioThemeCandidate:
    return PortfolioThemeCandidate(
        theme_name=name,
        theme_id=name.lower().replace(" ", "_"),
        ai_potential_score=82,
        research_importance=80,
        allocation_readiness=78,
        risk_adjusted_score=84,
        conviction_level="High Conviction",
        lifecycle_stage=stage,
        confidence_score=80,
        bubble_penalty=12,
        crowding_penalty=0,
        unresolved_bottleneck_penalty=8,
        bottleneck_overlap_keys=[bottleneck] if bottleneck else [],
        beneficiary_overlap_keys=[beneficiary] if beneficiary else [],
    )


def test_diversification_penalizes_lifecycle_concentration_and_large_weights() -> None:
    allocations = [
        PortfolioAllocation("A", "a", 50, ""),
        PortfolioAllocation("B", "b", 30, ""),
        PortfolioAllocation("C", "c", 20, ""),
    ]
    concentrated = [candidate("A", "Growth"), candidate("B", "Growth"), candidate("C", "Growth")]
    diversified = [candidate("A", "Early"), candidate("B", "Growth"), candidate("C", "Expansion")]

    scorer = PortfolioDiversifier()

    assert scorer.evaluate(allocations, diversified, "institutional").diversification_score > scorer.evaluate(allocations, concentrated, "institutional").diversification_score
