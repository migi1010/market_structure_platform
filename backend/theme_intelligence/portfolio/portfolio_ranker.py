from __future__ import annotations

from .portfolio_models import PortfolioResult


class PortfolioRanker:
    def rank(self, rows: list[PortfolioResult]) -> dict[str, list[dict]]:
        return {
            "best_portfolios": [row.to_api() for row in sorted(rows, key=lambda item: item.portfolio_score, reverse=True)],
            "lowest_risk": [row.to_api() for row in sorted(rows, key=lambda item: item.risk_score)],
            "highest_diversification": [row.to_api() for row in sorted(rows, key=lambda item: item.diversification_score, reverse=True)],
            "highest_allocation_quality": [row.to_api() for row in sorted(rows, key=lambda item: item.allocation_quality, reverse=True)],
        }
