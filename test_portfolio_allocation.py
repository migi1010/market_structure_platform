from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.portfolio.portfolio_allocator import PortfolioAllocator
from theme_intelligence.portfolio.portfolio_models import PortfolioThemeCandidate


def candidate(name: str, risk: float, allocation: float, ai: float, research: float, conviction: str = "High Conviction") -> PortfolioThemeCandidate:
    return PortfolioThemeCandidate(
        theme_name=name,
        theme_id=name.lower().replace(" ", "_"),
        ai_potential_score=ai,
        research_importance=research,
        allocation_readiness=allocation,
        risk_adjusted_score=risk,
        conviction_level=conviction,
        lifecycle_stage="Growth",
        confidence_score=80,
        bubble_penalty=12,
        crowding_penalty=4,
        unresolved_bottleneck_penalty=10,
    )


def test_allocator_uses_eligibility_and_enforces_weight_bounds() -> None:
    allocator = PortfolioAllocator()
    rows = [
        candidate("Glass Substrate", 96, 90, 94, 88, "Very High Conviction"),
        candidate("HBM", 88, 82, 86, 84),
        candidate("Power Grid", 82, 78, 80, 80),
        candidate("Robotics", 76, 72, 74, 72, "Medium Conviction"),
        candidate("Satellite", 64, 68, 70, 74, "Watchlist"),
    ]

    allocations = allocator.allocate(rows, "balanced_growth")
    weights = [row.weight for row in allocations]

    assert round(sum(weights), 6) == 100
    assert all(5 <= weight <= 35 for weight in weights)
    assert allocations[0].theme == "Glass Substrate"
    assert allocations[0].weight > allocations[-1].weight


def test_allocator_weights_are_not_hardcoded_final_outputs() -> None:
    allocator = PortfolioAllocator()
    base = [
        candidate("Glass Substrate", 86, 84, 82, 80),
        candidate("HBM", 84, 82, 80, 78),
        candidate("Power Grid", 82, 80, 78, 76),
    ]
    boosted = [base[0].with_updates(risk_adjusted_score=100, allocation_readiness=98), *base[1:]]

    base_weight = allocator.allocate(base, "maximum_conviction")[0].weight
    boosted_weight = allocator.allocate(boosted, "maximum_conviction")[0].weight

    assert boosted_weight > base_weight
