from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.factors.factor_registry import (
    FactorContext,
    FactorPipeline,
    FactorResult,
    FactorStatus,
    LifecycleState,
    get_default_factor_registry,
)


@dataclass(frozen=True)
class CompositeDefinition:
    id: str
    name: str
    description: str
    factor_weights: Mapping[str, float]


@dataclass(frozen=True)
class CompositeIntelligenceResult:
    composite_id: str
    composite_score: float | None
    confidence: float
    status: FactorStatus
    lifecycle_state: LifecycleState
    contributing_factors: list[dict[str, Any]]
    factor_weights: dict[str, float]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "composite_id": self.composite_id,
            "composite_score": self.composite_score,
            "confidence": self.confidence,
            "confidence_label": confidence_label(self.confidence),
            "status": self.status,
            "lifecycle_state": self.lifecycle_state,
            "contributing_factors": self.contributing_factors,
            "factor_weights": self.factor_weights,
            "explanation": self.explanation,
        }


COMPOSITE_DEFINITIONS: dict[str, CompositeDefinition] = {
    "momentum_composite": CompositeDefinition(
        id="momentum_composite",
        name="Momentum Composite",
        description="Momentum, relative strength, and volatility stability.",
        factor_weights={
            "simple_momentum": 0.45,
            "relative_strength": 0.40,
            "volatility_snapshot": 0.15,
        },
    ),
    "smart_money_composite": CompositeDefinition(
        id="smart_money_composite",
        name="Smart Money Composite",
        description="Volume anomaly and lightweight accumulation proxy.",
        factor_weights={
            "volume_anomaly": 0.45,
            "smart_money_partial": 0.55,
        },
    ),
    "quality_composite": CompositeDefinition(
        id="quality_composite",
        name="Quality Composite",
        description="Partial fundamentals and volatility stability.",
        factor_weights={
            "earnings_quality_partial": 0.55,
            "volatility_snapshot": 0.45,
        },
    ),
    "sector_leadership_composite": CompositeDefinition(
        id="sector_leadership_composite",
        name="Sector Leadership Composite",
        description="Sector leadership with relative strength confirmation.",
        factor_weights={
            "simple_sector_leadership": 0.55,
            "relative_strength": 0.45,
        },
    ),
}


def build_composite_intelligence(context: FactorContext, composite_ids: Iterable[str] | None = None) -> dict[str, Any]:
    selected_ids = list(composite_ids or COMPOSITE_DEFINITIONS.keys())
    pipeline = FactorPipeline(get_default_factor_registry(), max_concurrency=1, include_heavy=False)
    needed_factors = sorted({factor_id for composite_id in selected_ids if composite_id in COMPOSITE_DEFINITIONS for factor_id in COMPOSITE_DEFINITIONS[composite_id].factor_weights})
    factor_results = pipeline.run(context, needed_factors).factors
    result_by_id = {result.factor_id: result for result in factor_results}
    composites = {
        composite_id: aggregate_composite(COMPOSITE_DEFINITIONS[composite_id], result_by_id).to_dict()
        for composite_id in selected_ids
        if composite_id in COMPOSITE_DEFINITIONS
    }
    lifecycle = _aggregate_lifecycle_from_composites(composites.values())
    confidence_values = [value["confidence"] for value in composites.values()]
    confidence = bounded_score(sum(confidence_values) / len(confidence_values)) if confidence_values else 0.0
    available = any(value["composite_score"] is not None for value in composites.values())
    return {
        "available": available,
        "status": "partial_data" if available else "unavailable",
        "lifecycle_state": lifecycle,
        "confidence": confidence,
        "confidence_label": confidence_label(confidence),
        "composites": composites,
        "future_hooks": [
            "narrative_acceleration",
            "macro_regime_overlay",
            "multi_timeframe_scoring",
            "feature_store",
            "universe_ranking",
            "ai_narrative_engine",
        ],
    }


def aggregate_composite(definition: CompositeDefinition, result_by_id: Mapping[str, FactorResult]) -> CompositeIntelligenceResult:
    contributing: list[dict[str, Any]] = []
    weighted_score = 0.0
    used_weight = 0.0
    confidence_numerator = 0.0
    confidence_weight = 0.0
    for factor_id, weight in definition.factor_weights.items():
        result = result_by_id.get(factor_id)
        if result is None:
            contributing.append(_missing_factor(factor_id))
            continue
        factor_dict = result.to_dict()
        factor_dict["weight"] = weight
        contributing.append(factor_dict)
        if result.score is None:
            continue
        bounded = bounded_score(result.score)
        weighted_score += bounded * max(weight, 0.0)
        used_weight += max(weight, 0.0)
        confidence_numerator += result.confidence * max(weight, 0.0)
        confidence_weight += max(weight, 0.0)

    if used_weight <= 0:
        confidence = _partial_confidence(contributing)
        return CompositeIntelligenceResult(
            composite_id=definition.id,
            composite_score=None,
            confidence=confidence,
            status="partial_data",
            lifecycle_state="partial_live",
            contributing_factors=contributing,
            factor_weights=dict(definition.factor_weights),
            explanation=explain_composite(definition, None, contributing),
        )

    score = bounded_score(weighted_score / used_weight)
    completeness = used_weight / max(sum(max(weight, 0.0) for weight in definition.factor_weights.values()), 1.0)
    confidence = bounded_score((confidence_numerator / max(confidence_weight, 1.0)) * completeness)
    lifecycle = _aggregate_factor_lifecycle(contributing)
    status: FactorStatus = "live" if lifecycle == "live" and completeness >= 0.95 else "partial_data"
    return CompositeIntelligenceResult(
        composite_id=definition.id,
        composite_score=score,
        confidence=confidence,
        status=status,
        lifecycle_state=lifecycle,
        contributing_factors=contributing,
        factor_weights=dict(definition.factor_weights),
        explanation=explain_composite(definition, score, contributing),
    )


def explain_composite(definition: CompositeDefinition, score: float | None, contributing: list[dict[str, Any]]) -> str:
    finite = [item for item in contributing if item.get("score") is not None]
    if score is None or not finite:
        if definition.id == "quality_composite":
            return "Quality score uncertain due to partial fundamentals."
        return f"{definition.name} is partial because required factor inputs are unavailable."
    by_id = {str(item.get("factor_id")): item for item in finite}
    if definition.id == "momentum_composite":
        rs = _score_value(by_id.get("relative_strength"))
        if score >= 60 and rs is not None and rs >= 55:
            return "Momentum improving with strong relative strength."
        if score <= 40:
            return "Momentum weakening with insufficient relative strength confirmation."
        return "Momentum conditions are balanced with mixed factor confirmation."
    if definition.id == "smart_money_composite":
        volume = _score_value(by_id.get("volume_anomaly"))
        if volume is not None and volume >= 62:
            return "Elevated volume anomaly detected."
        if score >= 58:
            return "Smart money proxy is improving, but institutional confirmation remains partial."
        return "Smart money signal remains partial with limited volume confirmation."
    if definition.id == "quality_composite":
        if any(item.get("factor_id") == "earnings_quality_partial" and item.get("score") is None for item in contributing):
            return "Quality score uncertain due to partial fundamentals."
        return "Quality composite is driven by available fundamentals and volatility stability."
    if definition.id == "sector_leadership_composite":
        sector = _score_value(by_id.get("simple_sector_leadership"))
        if sector is not None and sector >= 60:
            return "Sector leadership improving with relative strength support."
        if sector is not None and sector <= 42:
            return "Sector leadership weakening."
        return "Sector leadership is partial until sector rotation confirms direction."
    return f"{definition.name} computed from available lightweight factors."


def _missing_factor(factor_id: str) -> dict[str, Any]:
    return {
        "factor_id": factor_id,
        "score": None,
        "confidence": 0.0,
        "status": "unavailable",
        "source": "composite_engine",
        "freshness": "partial",
        "explanation": "Factor was not available in this lightweight run.",
        "lifecycle_state": "partial_live",
        "weight": 0.0,
    }


def _score_value(item: Mapping[str, Any] | None) -> float | None:
    if item is None:
        return None
    value = item.get("score")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _partial_confidence(contributing: list[dict[str, Any]]) -> float:
    values = [float(item.get("confidence") or 0.0) for item in contributing]
    return bounded_score(sum(values) / len(values)) if values else 0.0


def _aggregate_factor_lifecycle(contributing: list[dict[str, Any]]) -> LifecycleState:
    states = {str(item.get("lifecycle_state") or "partial_live") for item in contributing}
    if "degraded" in states:
        return "degraded"
    if states == {"live"}:
        return "live"
    return "partial_live"


def _aggregate_lifecycle_from_composites(composites: Iterable[Mapping[str, Any]]) -> LifecycleState:
    states = {str(item.get("lifecycle_state") or "partial_live") for item in composites}
    if "degraded" in states:
        return "degraded"
    if states == {"live"}:
        return "live"
    return "partial_live"
