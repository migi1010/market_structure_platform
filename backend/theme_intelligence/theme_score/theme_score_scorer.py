from __future__ import annotations

from statistics import mean
from typing import Any

from .theme_score_allocator import ThemeScoreAllocator
from .theme_score_explainer import ThemeScoreExplainer
from .theme_score_models import ThemeFinalScore, ThemeScoreInput
from .theme_score_risk import clamp_score, compute_risk_penalties, lifecycle_weights, rounded_score


def _numeric(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = row.get(key)
        if isinstance(value, (int, float)):
            return clamp_score(float(value))
    return 0.0


def compute_beneficiary_quality(top_beneficiaries: list[dict[str, Any]]) -> float:
    if not top_beneficiaries:
        return 0.0

    ranked = top_beneficiaries[:5]
    allocation_scores = [_numeric(row, "allocation_score", "allocation_readiness") for row in ranked]
    beneficiary_scores = [_numeric(row, "beneficiary_score") for row in ranked]
    roles = {str(row.get("beneficiary_type") or row.get("role") or "unknown") for row in ranked}

    avg_top_allocation_score = mean(allocation_scores) if allocation_scores else 0.0
    avg_top_beneficiary_score = mean(beneficiary_scores) if beneficiary_scores else 0.0
    diversity_score = clamp_score(len(roles) * 22.0)
    controller_quality = max(
        (
            _numeric(row, "allocation_score", "beneficiary_score")
            for row in ranked
            if "controller" in str(row.get("beneficiary_type") or row.get("role") or "").lower()
        ),
        default=0.0,
    )
    resolution_enabler_quality = max(
        (
            _numeric(row, "allocation_score", "beneficiary_score")
            for row in ranked
            if "resolution" in str(row.get("beneficiary_type") or row.get("role") or "").lower()
        ),
        default=0.0,
    )

    return rounded_score(
        avg_top_allocation_score * 0.45
        + avg_top_beneficiary_score * 0.30
        + diversity_score * 0.10
        + controller_quality * 0.075
        + resolution_enabler_quality * 0.075
    )


class ThemeScoreScorer:
    def __init__(self) -> None:
        self.allocator = ThemeScoreAllocator()
        self.explainer = ThemeScoreExplainer()

    def score(self, score_input: ThemeScoreInput) -> ThemeFinalScore:
        weights = lifecycle_weights(score_input.lifecycle_stage)
        risk_penalties = compute_risk_penalties(score_input)

        lifecycle_opportunity = weights["opportunity"]
        lifecycle_maturity_score = weights["maturity"]
        lifecycle_transition_score = weights["transition"]
        unresolved_penalty = risk_penalties["unresolved_bottleneck_penalty"]
        bottleneck_quality = clamp_score(100.0 - unresolved_penalty * 0.76)
        bottleneck_resolution_quality = clamp_score(score_input.resolution_probability)

        ai_potential_score = rounded_score(
            score_input.discovery_score * 0.24
            + score_input.catalyst_strength * 0.20
            + score_input.beneficiary_quality * 0.20
            + lifecycle_opportunity * 0.14
            + bottleneck_quality * 0.10
            + score_input.confidence_score * 0.12
        )
        research_importance = rounded_score(
            score_input.emerging_score * 0.28
            + score_input.catalyst_strength * 0.24
            + score_input.bottleneck_strength * 0.18
            + lifecycle_transition_score * 0.16
            + score_input.confidence_score * 0.08
            + score_input.beneficiary_research_importance * 0.06
        )
        allocation_readiness = rounded_score(
            score_input.beneficiary_quality * 0.34
            + lifecycle_maturity_score * 0.18
            + score_input.confidence_score * 0.16
            + score_input.catalyst_strength * 0.14
            + bottleneck_resolution_quality * 0.08
            - score_input.bubble_penalty * 0.10
        )
        risk_adjusted_score = rounded_score(
            ai_potential_score
            - risk_penalties["bubble_penalty"] * 0.25
            - risk_penalties["crowding_penalty"] * 0.20
            - unresolved_penalty * 0.25
            + allocation_readiness * 0.20
            + score_input.confidence_score * 0.10
        )
        conviction_level = self.allocator.conviction_level(
            score_input,
            risk_adjusted_score=risk_adjusted_score,
            allocation_readiness=allocation_readiness,
        )

        result = ThemeFinalScore(
            theme_name=score_input.theme_name,
            ai_potential_score=ai_potential_score,
            research_importance=research_importance,
            allocation_readiness=allocation_readiness,
            risk_adjusted_score=risk_adjusted_score,
            conviction_level=conviction_level,
            score_components={
                "discovery_score": rounded_score(score_input.discovery_score),
                "emerging_score": rounded_score(score_input.emerging_score),
                "confidence_score": rounded_score(score_input.confidence_score),
                "crowding_proxy": rounded_score(score_input.crowding_proxy),
                "catalyst_strength": rounded_score(score_input.catalyst_strength),
                "bottleneck_strength": rounded_score(score_input.bottleneck_strength),
                "resolution_probability": rounded_score(score_input.resolution_probability),
                "bottleneck_quality": rounded_score(bottleneck_quality),
                "bottleneck_resolution_quality": rounded_score(bottleneck_resolution_quality),
                "beneficiary_quality": rounded_score(score_input.beneficiary_quality),
                "beneficiary_research_importance": rounded_score(score_input.beneficiary_research_importance),
                "bubble_penalty": rounded_score(score_input.bubble_penalty),
                "lifecycle_stage": score_input.lifecycle_stage,
                "lifecycle_confidence": rounded_score(score_input.lifecycle_confidence),
                "lifecycle_opportunity": rounded_score(lifecycle_opportunity),
                "lifecycle_maturity_score": rounded_score(lifecycle_maturity_score),
                "lifecycle_transition_score": rounded_score(lifecycle_transition_score),
                "risk_penalties": risk_penalties,
            },
        )
        return self.explainer.explain(result, score_input)
