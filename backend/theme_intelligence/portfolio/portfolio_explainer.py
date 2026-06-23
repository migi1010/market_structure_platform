from __future__ import annotations

from .portfolio_models import PortfolioAllocation, PortfolioThemeCandidate


class PortfolioExplainer:
    def explain(
        self,
        *,
        allocations: list[PortfolioAllocation],
        selected: list[PortfolioThemeCandidate],
        excluded: list[PortfolioThemeCandidate],
        risk_sources: list[str],
        bubble_sources: list[str],
        diversification_notes: list[str],
    ) -> dict[str, list[str]]:
        selected_map = {row.theme_id: row for row in selected}
        why_selected = []
        for allocation in allocations:
            candidate = selected_map.get(allocation.theme_id)
            if candidate is None:
                continue
            why_selected.append(
                f"{allocation.theme} receives {allocation.weight:.0f}% because risk-adjusted score is {candidate.risk_adjusted_score:.0f} and allocation readiness is {candidate.allocation_readiness:.0f}."
            )
        why_excluded = [
            f"{row.theme_name} remains outside the allocation because conviction is {row.conviction_level} or score rank is below selected themes."
            for row in excluded[:5]
        ]
        return {
            "why_selected": why_selected,
            "why_excluded": why_excluded,
            "risk_sources": risk_sources,
            "bubble_sources": bubble_sources,
            "diversification_notes": diversification_notes,
        }
