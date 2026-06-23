from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.portfolio.portfolio_diversifier import PortfolioDiversifier
from theme_intelligence.portfolio.portfolio_models import PortfolioAllocation, PortfolioThemeCandidate


def candidate(name: str, overlap: str) -> PortfolioThemeCandidate:
    return PortfolioThemeCandidate(
        theme_name=name,
        theme_id=name.lower().replace(" ", "_"),
        ai_potential_score=85,
        research_importance=84,
        allocation_readiness=82,
        risk_adjusted_score=86,
        conviction_level="High Conviction",
        lifecycle_stage="Growth",
        confidence_score=82,
        bubble_penalty=10,
        crowding_penalty=0,
        unresolved_bottleneck_penalty=12,
        bottleneck_overlap_keys=[overlap],
    )


def test_shared_bottleneck_cluster_lowers_diversification_and_adds_note() -> None:
    allocations = [
        PortfolioAllocation("HBM", "hbm", 34, ""),
        PortfolioAllocation("CoWoS", "cowos", 33, ""),
        PortfolioAllocation("Glass Substrate", "glass_substrate", 33, ""),
    ]
    shared = [candidate("HBM", "Yield Constraint|Packaging Yield|TSM"), candidate("CoWoS", "Yield Constraint|Packaging Yield|TSM"), candidate("Glass Substrate", "Yield Constraint|Packaging Yield|TSM")]
    separate = [candidate("HBM", "Capacity|Memory|MU"), candidate("CoWoS", "Equipment|Packaging|ASML"), candidate("Glass Substrate", "Yield|Substrate|GLW")]

    scorer = PortfolioDiversifier()
    shared_result = scorer.evaluate(allocations, shared, "balanced_growth")
    separate_result = scorer.evaluate(allocations, separate, "balanced_growth")

    assert shared_result.diversification_score < separate_result.diversification_score
    assert any("bottleneck" in note.lower() for note in shared_result.diversification_notes)
