from __future__ import annotations

from statistics import mean
from time import monotonic
from typing import Any

from theme_intelligence.portfolio.portfolio_allocator import PortfolioAllocator
from theme_intelligence.portfolio.portfolio_diversifier import PortfolioDiversifier
from theme_intelligence.portfolio.portfolio_explainer import PortfolioExplainer
from theme_intelligence.portfolio.portfolio_models import (
    PORTFOLIO_NAMES,
    PORTFOLIO_TYPES,
    PortfolioAllocation,
    PortfolioResult,
    PortfolioThemeCandidate,
    round_score,
    theme_id_for,
)
from theme_intelligence.portfolio.portfolio_ranker import PortfolioRanker
from theme_intelligence.portfolio.portfolio_risk import PortfolioRiskScorer
from theme_intelligence.storage.theme_repository import ThemeRepository


THEME_PORTFOLIO_TTL_SECONDS = 6 * 60 * 60


class PortfolioEngine:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()
        self.allocator = PortfolioAllocator()
        self.risk_scorer = PortfolioRiskScorer()
        self.diversifier = PortfolioDiversifier()
        self.explainer = PortfolioExplainer()
        self.ranker = PortfolioRanker()
        self._cache: tuple[float, dict[str, Any]] | None = None

    def get_portfolios(self, use_cache: bool = True) -> dict[str, Any]:
        if use_cache and self._cache and monotonic() - self._cache[0] < THEME_PORTFOLIO_TTL_SECONDS:
            return self._cache[1]
        self.repository.initialize()
        rows = self.repository.get_portfolios(limit=20) if use_cache else self.run()
        payload = {
            "portfolios": [row.to_api() for row in rows],
            "rankings": self.ranker.rank(rows),
            "source_status": {
                "portfolio_count": len(rows),
                "source": "persisted" if use_cache else "recomputed",
                "cache_ttl_seconds": THEME_PORTFOLIO_TTL_SECONDS,
            },
        }
        self._cache = (monotonic(), payload)
        return payload

    def get_detail(self, portfolio_type: str) -> dict[str, Any]:
        normalized = portfolio_type.strip().lower()
        payload = self.get_portfolios()
        for row in payload["portfolios"]:
            if row["portfolio_type"] == normalized:
                return row
        return {"portfolio_type": normalized, "error": "Theme portfolio not found"}

    def run(self) -> list[PortfolioResult]:
        self.repository.initialize()
        final_scores = self.repository.get_final_scores(limit=100)
        if not final_scores:
            return self.repository.get_portfolios(limit=20)
        bottlenecks = self.repository.get_bottlenecks()
        beneficiaries = self.repository.get_beneficiary_scores()
        candidates = self._candidates(final_scores, bottlenecks, beneficiaries)
        rows = [self._build_portfolio(portfolio_type, candidates) for portfolio_type in PORTFOLIO_TYPES]
        self.repository.save_portfolios(rows)
        return rows

    def _build_portfolio(self, portfolio_type: str, candidates: list[PortfolioThemeCandidate]) -> PortfolioResult:
        allocations = self.allocator.allocate(candidates, portfolio_type)
        selected_ids = {row.theme_id for row in allocations}
        selected = [row for row in candidates if row.theme_id in selected_ids]
        excluded = [row for row in candidates if row.theme_id not in selected_ids]
        risk = self.risk_scorer.score(allocations, selected)
        diversification = self.diversifier.evaluate(allocations, selected, portfolio_type)
        allocation_quality = self._allocation_quality(allocations, selected)
        portfolio_score = round_score(
            allocation_quality * 0.40
            + diversification.diversification_score * 0.25
            + (100.0 - risk.risk_score) * 0.20
            + diversification.lifecycle_balance * 0.15
        )
        risk_sources = self._risk_sources(risk, selected)
        bubble_sources = [
            f"{row.theme_name} has beneficiary bubble penalty of {row.bubble_penalty:.0f}."
            for row in selected
            if row.bubble_penalty >= 45
        ]
        explanation = self.explainer.explain(
            allocations=allocations,
            selected=selected,
            excluded=excluded,
            risk_sources=risk_sources,
            bubble_sources=bubble_sources,
            diversification_notes=diversification.diversification_notes,
        )
        return PortfolioResult(
            portfolio_name=PORTFOLIO_NAMES[portfolio_type],
            portfolio_type=portfolio_type,
            themes=allocations,
            risk_profile=risk.risk_profile,
            lifecycle_mix=diversification.lifecycle_mix,
            bubble_exposure=risk.weighted_bubble_penalty,
            portfolio_score=portfolio_score,
            allocation_quality=allocation_quality,
            diversification_score=diversification.diversification_score,
            risk_score=risk.risk_score,
            lifecycle_balance=diversification.lifecycle_balance,
            constraints={
                "min_weight": 5,
                "max_weight": 35,
                "max_single_bottleneck_cluster": 45,
                "max_same_top_beneficiary_overlap": 40,
                "max_mature_weight_non_low_bubble": 20,
            },
            **explanation,
        )

    def _candidates(self, final_scores: list[Any], bottlenecks: list[Any], beneficiaries: list[Any]) -> list[PortfolioThemeCandidate]:
        bottleneck_map = self._bottleneck_keys(bottlenecks)
        beneficiary_map = self._beneficiary_keys(beneficiaries)
        rows: list[PortfolioThemeCandidate] = []
        for score in final_scores:
            components = getattr(score, "score_components", {}) or {}
            risk_penalties = components.get("risk_penalties", {}) if isinstance(components.get("risk_penalties", {}), dict) else {}
            theme_name = getattr(score, "theme_name", "")
            theme_id = theme_id_for(theme_name)
            rows.append(
                PortfolioThemeCandidate(
                    theme_name=theme_name,
                    theme_id=theme_id,
                    ai_potential_score=getattr(score, "ai_potential_score", 0.0),
                    research_importance=getattr(score, "research_importance", 0.0),
                    allocation_readiness=getattr(score, "allocation_readiness", 0.0),
                    risk_adjusted_score=getattr(score, "risk_adjusted_score", 0.0),
                    conviction_level=getattr(score, "conviction_level", "Watchlist"),
                    lifecycle_stage=str(components.get("lifecycle_stage") or "Seed"),
                    confidence_score=self._number(components, "confidence_score", default=0.0),
                    bubble_penalty=self._number(components, "bubble_penalty", default=0.0),
                    crowding_penalty=self._number(risk_penalties, "crowding_penalty", default=self._number(components, "crowding_proxy", default=0.0)),
                    unresolved_bottleneck_penalty=self._number(risk_penalties, "unresolved_bottleneck_penalty", default=0.0),
                    bottleneck_overlap_keys=bottleneck_map.get(theme_name, []),
                    beneficiary_overlap_keys=beneficiary_map.get(theme_name, []),
                )
            )
        return rows

    @staticmethod
    def _bottleneck_keys(bottlenecks: list[Any]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for row in bottlenecks:
            controllers = getattr(row, "controller_entities", []) or []
            tickers = sorted({str(item.get("ticker", "")).upper() for item in controllers if isinstance(item, dict) and item.get("ticker")})
            key = "|".join(
                [
                    str(getattr(row, "bottleneck_type", "")),
                    str(getattr(row, "bottleneck_name", "")),
                    ",".join(tickers),
                ]
            )
            if key.strip("|"):
                grouped.setdefault(str(getattr(row, "theme_name", "")), []).append(key)
        return grouped

    @staticmethod
    def _beneficiary_keys(beneficiaries: list[Any]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for row in beneficiaries:
            key = "|".join(
                [
                    str(getattr(row, "ticker", "")).upper(),
                    str(getattr(row, "company_name", "")),
                    str(getattr(row, "beneficiary_type", "")),
                ]
            )
            if key.strip("|"):
                grouped.setdefault(str(getattr(row, "theme_name", "")), []).append(key)
        return grouped

    @staticmethod
    def _allocation_quality(allocations: list[PortfolioAllocation], candidates: list[PortfolioThemeCandidate]) -> float:
        candidate_map = {row.theme_id: row for row in candidates}
        values = []
        for allocation in allocations:
            candidate = candidate_map.get(allocation.theme_id)
            if candidate is None:
                continue
            values.append((candidate.risk_adjusted_score * 0.55 + candidate.allocation_readiness * 0.45) * allocation.weight / 100.0)
        return round_score(sum(values))

    @staticmethod
    def _risk_sources(risk: Any, selected: list[PortfolioThemeCandidate]) -> list[str]:
        sources = []
        if risk.weighted_unresolved_bottleneck_penalty >= 30:
            sources.append("Weighted unresolved bottleneck exposure is elevated.")
        if risk.weighted_crowding_penalty >= 20:
            sources.append("Crowding proxy is elevated across selected themes.")
        if risk.confidence_gap >= 30:
            sources.append("Portfolio confidence gap remains material.")
        sources.extend(
            f"{row.theme_name} has unresolved bottleneck penalty of {row.unresolved_bottleneck_penalty:.0f}."
            for row in selected
            if row.unresolved_bottleneck_penalty >= 40
        )
        return sources

    @staticmethod
    def _number(row: dict[str, Any], key: str, default: float = 0.0) -> float:
        value = row.get(key, default)
        return float(value) if isinstance(value, (int, float)) else default


def get_theme_portfolios() -> dict[str, Any]:
    return PortfolioEngine().get_portfolios()


def get_theme_portfolio_detail(portfolio_type: str) -> dict[str, Any]:
    return PortfolioEngine().get_detail(portfolio_type)
