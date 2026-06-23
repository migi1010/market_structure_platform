from __future__ import annotations

from .theme_score_models import ThemeScoreInput


class ThemeScoreAllocator:
    """Assigns cautious, research-oriented conviction labels."""

    def conviction_level(
        self,
        score_input: ThemeScoreInput,
        risk_adjusted_score: float,
        allocation_readiness: float,
    ) -> str:
        bubble_penalty = score_input.bubble_penalty
        stage = score_input.lifecycle_stage
        crowding = score_input.crowding_proxy

        if bubble_penalty >= 70 or risk_adjusted_score < 40 or allocation_readiness < 35:
            return "Avoid"
        if stage == "Mature" and (crowding >= 60 or bubble_penalty >= 35):
            return "Watchlist" if risk_adjusted_score < 75 else "Medium Conviction"
        if (
            risk_adjusted_score >= 88
            and allocation_readiness >= 72
            and bubble_penalty < 35
            and crowding < 55
            and stage in {"Early", "Growth"}
        ):
            return "Very High Conviction"
        if risk_adjusted_score >= 78 and allocation_readiness >= 65 and bubble_penalty < 45 and stage != "Mature":
            return "High Conviction"
        if risk_adjusted_score >= 62 and allocation_readiness >= 50:
            return "Medium Conviction"
        if risk_adjusted_score >= 45 or allocation_readiness >= 45:
            return "Watchlist"
        return "Avoid"
