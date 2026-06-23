from __future__ import annotations

import re
from dataclasses import replace

from .theme_ranking_models import (
    ThemeRank,
    ThemeRankingLifecycle,
    ThemeRankingSource,
    ThemeRankingWeights,
)


THEME_RANKING_ALGORITHM_VERSION = "theme-ranking-v1"


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _identity_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


class ThemeRankingEngine:
    def __init__(self, weights: ThemeRankingWeights | None = None) -> None:
        self.weights = weights or ThemeRankingWeights()

    def rank_themes(self, sources: list[ThemeRankingSource]) -> list[ThemeRank]:
        selected: dict[str, ThemeRankingSource] = {}
        for row in sorted(sources, key=lambda item: item.theme_id):
            key = _identity_key(row.theme_id)
            current = selected.get(key)
            selected[key] = row if current is None else self._merge_sources(current, row)
        ranks = [self._rank(row) for row in selected.values()]
        return sorted(ranks, key=lambda row: (-row.rank_score, row.theme_id))

    def _merge_sources(self, left: ThemeRankingSource, right: ThemeRankingSource) -> ThemeRankingSource:
        primary = left if self._source_strength(left) >= self._source_strength(right) else right
        return replace(
            primary,
            theme_id=_identity_key(primary.theme_id),
            theme_name=primary.theme_name or left.theme_name or right.theme_name,
            has_active_graph=left.has_active_graph or right.has_active_graph,
            has_scout_signal=left.has_scout_signal or right.has_scout_signal,
            scout_theme_score=max(left.scout_theme_score, right.scout_theme_score),
            scout_velocity_score=max(left.scout_velocity_score, right.scout_velocity_score),
            scout_evidence_count=max(left.scout_evidence_count, right.scout_evidence_count),
            scout_signal_count=max(left.scout_signal_count, right.scout_signal_count),
            research_case_count=max(left.research_case_count, right.research_case_count),
            approved_research_count=max(left.approved_research_count, right.approved_research_count),
            monitoring_research_count=max(left.monitoring_research_count, right.monitoring_research_count),
            controller_count=max(left.controller_count, right.controller_count),
            opportunity_count=max(left.opportunity_count, right.opportunity_count),
            graph_evidence_count=max(left.graph_evidence_count, right.graph_evidence_count),
            updated_at=max(left.updated_at, right.updated_at),
        )

    def _rank(self, row: ThemeRankingSource) -> ThemeRank:
        evidence = self._evidence_score(row)
        research = self._research_score(row)
        controller = self._controller_score(row)
        opportunity = self._opportunity_score(row)
        momentum = self._momentum_score(row)
        weights = self.weights
        rank_score = (
            evidence * weights.evidence
            + research * weights.research
            + controller * weights.controller
            + opportunity * weights.opportunity
            + momentum * weights.momentum
        )
        return ThemeRank(
            theme_id=row.theme_id,
            theme_name=row.theme_name,
            lifecycle=self._lifecycle(row),
            rank_score=round(rank_score, 4),
            momentum_score=momentum,
            evidence_score=evidence,
            research_score=research,
            controller_score=controller,
            opportunity_score=opportunity,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _source_strength(row: ThemeRankingSource) -> tuple[float, str]:
        return (
            row.graph_evidence_count + row.scout_evidence_count + row.controller_count + row.opportunity_count,
            row.updated_at,
        )

    @staticmethod
    def _evidence_score(row: ThemeRankingSource) -> float:
        return _bounded(row.graph_evidence_count * 10 + row.scout_evidence_count * 10 + row.scout_signal_count * 5)

    @staticmethod
    def _research_score(row: ThemeRankingSource) -> float:
        discovered = max(0, row.research_case_count - row.approved_research_count - row.monitoring_research_count)
        return _bounded(row.approved_research_count * 80 + row.monitoring_research_count * 55 + discovered * 35)

    @staticmethod
    def _controller_score(row: ThemeRankingSource) -> float:
        return _bounded(row.controller_count * 25)

    @staticmethod
    def _opportunity_score(row: ThemeRankingSource) -> float:
        return _bounded(row.opportunity_count * 35)

    @staticmethod
    def _momentum_score(row: ThemeRankingSource) -> float:
        return _bounded(row.scout_velocity_score if row.has_scout_signal else 0)

    @staticmethod
    def _lifecycle(row: ThemeRankingSource) -> ThemeRankingLifecycle:
        if row.has_active_graph and row.controller_count > 0 and row.opportunity_count > 0:
            return "ACTIVE"
        if (
            row.has_scout_signal
            and row.scout_theme_score >= 70
            and row.research_case_count > 0
            and (row.scout_velocity_score >= 60 or row.scout_evidence_count >= 5)
        ):
            return "ACCELERATING"
        if row.has_scout_signal and not row.has_active_graph and row.scout_theme_score >= 60 and row.scout_evidence_count > 0:
            return "EMERGING"
        if (
            (row.has_active_graph or row.approved_research_count > 0 or row.monitoring_research_count > 0)
            and row.opportunity_count == 0
            and (not row.has_scout_signal or row.scout_velocity_score < 60)
        ):
            return "MONITORING"
        return "DECLINING"
