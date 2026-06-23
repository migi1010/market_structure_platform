from __future__ import annotations

from .theme_score_models import ThemeFinalScore


CONVICTION_ORDER = {
    "Very High Conviction": 5,
    "High Conviction": 4,
    "Medium Conviction": 3,
    "Watchlist": 2,
    "Avoid": 1,
}


class ThemeScoreRanker:
    def rank(self, scores: list[ThemeFinalScore], limit: int = 20) -> dict[str, list[dict]]:
        return {
            "top_ai_themes": [row.to_api() for row in sorted(scores, key=lambda item: item.ai_potential_score, reverse=True)[:limit]],
            "top_emerging_themes": [
                row.to_api()
                for row in sorted(
                    scores,
                    key=lambda item: item.score_components.get("emerging_score", 0),
                    reverse=True,
                )[:limit]
            ],
            "highest_conviction": [
                row.to_api()
                for row in sorted(
                    scores,
                    key=lambda item: (
                        CONVICTION_ORDER.get(item.conviction_level, 0),
                        item.risk_adjusted_score,
                        item.allocation_readiness,
                    ),
                    reverse=True,
                )[:limit]
            ],
            "highest_research_priority": [
                row.to_api() for row in sorted(scores, key=lambda item: item.research_importance, reverse=True)[:limit]
            ],
            "best_risk_adjusted": [
                row.to_api() for row in sorted(scores, key=lambda item: item.risk_adjusted_score, reverse=True)[:limit]
            ],
        }
