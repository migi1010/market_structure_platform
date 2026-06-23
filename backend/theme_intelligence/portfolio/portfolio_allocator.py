from __future__ import annotations

from .portfolio_constraints import objective_adjusted_score, normalize_weights
from .portfolio_models import PortfolioAllocation, PortfolioThemeCandidate


class PortfolioAllocator:
    def allocate(self, candidates: list[PortfolioThemeCandidate], portfolio_type: str, limit: int = 5) -> list[PortfolioAllocation]:
        eligible = [row for row in candidates if row.eligible_score > 0 and row.conviction_level != "Avoid"]
        ranked = sorted(
            eligible,
            key=lambda row: (objective_adjusted_score(row, portfolio_type), row.risk_adjusted_score, row.allocation_readiness),
            reverse=True,
        )[: max(1, limit)]
        raw_weights = {row.theme_id: objective_adjusted_score(row, portfolio_type) for row in ranked}
        weights = normalize_weights(raw_weights)
        return [
            PortfolioAllocation(
                theme=row.theme_name,
                theme_id=row.theme_id,
                weight=weights.get(row.theme_id, 0.0),
                allocation_rationale=self._rationale(row, portfolio_type),
            )
            for row in ranked
            if weights.get(row.theme_id, 0.0) > 0
        ]

    @staticmethod
    def _rationale(candidate: PortfolioThemeCandidate, portfolio_type: str) -> str:
        if portfolio_type == "low_bubble":
            return f"{candidate.theme_name} balances risk-adjusted score with bubble exposure of {candidate.bubble_penalty:.0f}."
        if portfolio_type == "early_opportunity":
            return f"{candidate.theme_name} offers {candidate.lifecycle_stage} lifecycle exposure with research importance of {candidate.research_importance:.0f}."
        if portfolio_type == "institutional":
            return f"{candidate.theme_name} contributes allocation readiness and lifecycle diversification."
        return f"{candidate.theme_name} is selected for {candidate.conviction_level.lower()} and risk-adjusted score of {candidate.risk_adjusted_score:.0f}."
