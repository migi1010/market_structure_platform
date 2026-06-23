from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.portfolio.portfolio_diversifier import PortfolioDiversifier
from theme_intelligence.portfolio.portfolio_models import PortfolioAllocation, PortfolioThemeCandidate


def candidate(name: str, beneficiary_key: str) -> PortfolioThemeCandidate:
    return PortfolioThemeCandidate(
        theme_name=name,
        theme_id=name.lower().replace(" ", "_"),
        ai_potential_score=83,
        research_importance=80,
        allocation_readiness=78,
        risk_adjusted_score=82,
        conviction_level="High Conviction",
        lifecycle_stage="Growth",
        confidence_score=78,
        bubble_penalty=20,
        crowding_penalty=0,
        unresolved_bottleneck_penalty=10,
        beneficiary_overlap_keys=[beneficiary_key],
    )


def test_shared_top_beneficiary_lowers_diversification_score() -> None:
    allocations = [
        PortfolioAllocation("AI Infrastructure", "ai_infrastructure", 40, ""),
        PortfolioAllocation("HBM", "hbm", 30, ""),
        PortfolioAllocation("Advanced Packaging", "advanced_packaging", 30, ""),
    ]
    shared = [candidate("AI Infrastructure", "NVDA|NVIDIA|Direct Beneficiary"), candidate("HBM", "NVDA|NVIDIA|Direct Beneficiary"), candidate("Advanced Packaging", "NVDA|NVIDIA|Direct Beneficiary")]
    separate = [candidate("AI Infrastructure", "NVDA|NVIDIA|Direct Beneficiary"), candidate("HBM", "MU|Micron|Direct Beneficiary"), candidate("Advanced Packaging", "TSM|TSMC|Bottleneck Controller")]

    scorer = PortfolioDiversifier()

    assert scorer.evaluate(allocations, shared, "balanced_growth").diversification_score < scorer.evaluate(allocations, separate, "balanced_growth").diversification_score
