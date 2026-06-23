from __future__ import annotations

from collections.abc import Callable

from .portfolio_models import PortfolioAllocation, PortfolioRiskResult, PortfolioThemeCandidate, round_score


LIFECYCLE_RISK = {
    "Seed": 35.0,
    "Early": 20.0,
    "Growth": 12.0,
    "Expansion": 10.0,
    "Mature": 25.0,
}


class PortfolioRiskScorer:
    def score(self, allocations: list[PortfolioAllocation], candidates: list[PortfolioThemeCandidate]) -> PortfolioRiskResult:
        candidate_map = {row.theme_id: row for row in candidates}
        weighted_bubble = self._weighted(allocations, candidate_map, lambda row: row.bubble_penalty)
        weighted_crowding = self._weighted(allocations, candidate_map, lambda row: row.crowding_penalty)
        weighted_bottleneck = self._weighted(allocations, candidate_map, lambda row: row.unresolved_bottleneck_penalty)
        lifecycle_risk = self._weighted(allocations, candidate_map, lambda row: LIFECYCLE_RISK.get(row.lifecycle_stage, 35.0))
        confidence_gap = self._weighted(allocations, candidate_map, lambda row: 100.0 - row.confidence_score)
        risk_score = round_score(
            weighted_bubble * 0.30
            + weighted_crowding * 0.20
            + weighted_bottleneck * 0.25
            + lifecycle_risk * 0.15
            + confidence_gap * 0.10
        )
        return PortfolioRiskResult(
            risk_score=risk_score,
            risk_profile=self._profile(risk_score),
            weighted_bubble_penalty=round_score(weighted_bubble),
            weighted_crowding_penalty=round_score(weighted_crowding),
            weighted_unresolved_bottleneck_penalty=round_score(weighted_bottleneck),
            lifecycle_risk=round_score(lifecycle_risk),
            confidence_gap=round_score(confidence_gap),
        )

    @staticmethod
    def _weighted(
        allocations: list[PortfolioAllocation],
        candidate_map: dict[str, PortfolioThemeCandidate],
        getter: Callable[[PortfolioThemeCandidate], float],
    ) -> float:
        total = 0.0
        for allocation in allocations:
            candidate = candidate_map.get(allocation.theme_id)
            if candidate is None:
                continue
            total += allocation.weight / 100.0 * getter(candidate)
        return total

    @staticmethod
    def _profile(score: float) -> str:
        if score <= 35:
            return "Low"
        if score <= 60:
            return "Moderate"
        if score <= 80:
            return "Elevated"
        return "High"
