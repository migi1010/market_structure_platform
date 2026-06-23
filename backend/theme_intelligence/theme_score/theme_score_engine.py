from __future__ import annotations

from statistics import mean
from time import monotonic
from typing import Any

from ..models.theme_models import normalize_theme_name
from ..storage.theme_repository import ThemeRepository
from .theme_score_models import ThemeFinalScore, ThemeScoreInput, theme_id_for
from .theme_score_ranker import ThemeScoreRanker
from .theme_score_scorer import ThemeScoreScorer, compute_beneficiary_quality


THEME_SCORE_CACHE_TTL_SECONDS = 6 * 60 * 60


class ThemeScoreEngine:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()
        self.scorer = ThemeScoreScorer()
        self.ranker = ThemeScoreRanker()
        self._cache: tuple[float, dict[str, Any]] | None = None

    def get_scores(self) -> dict[str, Any]:
        if self._cache and monotonic() - self._cache[0] < THEME_SCORE_CACHE_TTL_SECONDS:
            return self._cache[1]

        score_rows = self.run()
        payload = {
            "themes": [row.to_api() for row in score_rows],
            "rankings": self.ranker.rank(score_rows),
        }
        self._cache = (monotonic(), payload)
        return payload

    def get_score_detail(self, theme_id: str) -> dict[str, Any]:
        payload = self.get_scores()
        normalized_id = theme_id.lower()
        for row in payload["themes"]:
            if row["theme_id"] == normalized_id or theme_id_for(row["theme"]) == normalized_id:
                return row
        return {"theme_id": normalized_id, "theme": theme_id, "error": "Theme score not found"}

    def run(self) -> list[ThemeFinalScore]:
        discovery_rows = self.repository.get_discovery_scores(limit=100)
        catalysts = self.repository.get_catalysts()
        bottlenecks = self.repository.get_bottlenecks()
        beneficiary_scores = self.repository.get_beneficiary_scores()

        if not discovery_rows:
            stored_scores = self.repository.get_final_scores(limit=100)
            return stored_scores

        score_rows: list[ThemeFinalScore] = []
        for row in discovery_rows:
            score_input = self._input_from_sources(
                row=row,
                catalysts=catalysts,
                bottlenecks=bottlenecks,
                beneficiary_scores=beneficiary_scores,
            )
            score_rows.append(self.scorer.score(score_input))

        score_rows.sort(key=lambda item: item.risk_adjusted_score, reverse=True)
        self.repository.save_final_scores(score_rows)
        return score_rows

    def _input_from_sources(
        self,
        *,
        row: dict[str, Any],
        catalysts: list[Any],
        bottlenecks: list[Any],
        beneficiary_scores: list[Any],
    ) -> ThemeScoreInput:
        theme_name = normalize_theme_name(str(row.get("theme_name") or row.get("name") or ""))
        theme_catalysts = [item for item in catalysts if normalize_theme_name(getattr(item, "theme_name", "")) == theme_name]
        theme_bottlenecks = [item for item in bottlenecks if normalize_theme_name(getattr(item, "theme_name", "")) == theme_name]
        theme_beneficiaries = [
            item for item in beneficiary_scores if normalize_theme_name(getattr(item, "theme_name", "")) == theme_name
        ]

        top_beneficiaries = [self._beneficiary_to_dict(item) for item in theme_beneficiaries[:5]]
        beneficiary_quality = compute_beneficiary_quality(top_beneficiaries)
        if beneficiary_quality == 0:
            beneficiary_quality = self._number(row, "entity_strength_score", "confidence_score")

        catalyst_strength = self._number(row, "catalyst_score")
        if theme_catalysts:
            catalyst_strength = max(catalyst_strength, mean(getattr(item, "catalyst_strength", 0.0) for item in theme_catalysts[:5]))

        bottleneck_strength = self._number(row, "bottleneck_strength")
        resolution_probability = self._number(row, "resolution_probability")
        if theme_bottlenecks:
            primary = max(theme_bottlenecks, key=lambda item: getattr(item, "bottleneck_strength", 0.0))
            bottleneck_strength = max(bottleneck_strength, getattr(primary, "bottleneck_strength", 0.0))
            resolution_probability = max(resolution_probability, getattr(primary, "resolution_probability", 0.0))

        bubble_penalty = 0.0
        if top_beneficiaries:
            bubble_penalty = mean(self._number(item, "bubble_penalty") for item in top_beneficiaries)

        beneficiary_research_importance = self._number(row, "beneficiary_research_importance")
        if beneficiary_research_importance == 0 and top_beneficiaries:
            beneficiary_research_importance = mean(self._number(item, "beneficiary_score") for item in top_beneficiaries)

        return ThemeScoreInput(
            theme_name=theme_name,
            discovery_score=self._number(row, "discovery_score", "final_ai_score"),
            emerging_score=self._number(row, "emerging_score"),
            confidence_score=self._number(row, "confidence_score"),
            crowding_proxy=self._number(row, "crowding_proxy"),
            lifecycle_stage=str(row.get("lifecycle_stage") or "Seed"),
            lifecycle_confidence=self._number(row, "lifecycle_confidence"),
            catalyst_strength=catalyst_strength,
            bottleneck_strength=bottleneck_strength,
            resolution_probability=resolution_probability,
            beneficiary_quality=beneficiary_quality,
            beneficiary_research_importance=beneficiary_research_importance,
            bubble_penalty=bubble_penalty,
            top_beneficiaries=top_beneficiaries,
        )

    @staticmethod
    def _number(row: Any, *keys: str) -> float:
        if isinstance(row, dict):
            for key in keys:
                value = row.get(key)
                if isinstance(value, (int, float)):
                    return max(0.0, min(100.0, float(value)))
        return 0.0

    @staticmethod
    def _beneficiary_to_dict(row: Any) -> dict[str, Any]:
        if isinstance(row, dict):
            return row
        return {
            "theme_name": getattr(row, "theme_name", ""),
            "ticker": getattr(row, "ticker", ""),
            "company_name": getattr(row, "company_name", ""),
            "beneficiary_type": getattr(row, "beneficiary_type", ""),
            "allocation_score": getattr(row, "allocation_score", 0.0),
            "beneficiary_score": getattr(row, "beneficiary_score", 0.0),
            "bubble_penalty": getattr(row, "bubble_penalty", 0.0),
        }
