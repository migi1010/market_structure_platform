from __future__ import annotations

from statistics import mean

from theme_intelligence.lifecycle.lifecycle_models import LifecycleInput, StageDecision
from theme_intelligence.models import LIFECYCLE_STAGES, clamp_score, expected_next_stage


def classify_stage(data: LifecycleInput) -> StageDecision:
    deteriorating = is_deteriorating(data)
    rules: list[str] = []

    if (
        data.crowding_proxy >= 70
        and data.entity_strength_score >= 65
        and (data.emerging_score < 55 or deteriorating)
    ):
        rules.append("high crowding with slower acceleration")
        return StageDecision("Mature", rules, deteriorating)

    if (
        data.final_ai_score >= 70
        and data.entity_strength_score >= 70
        and data.discovery_score >= 70
        and 45 <= data.crowding_proxy <= 75
    ):
        rules.append("broad recognition with strong entity confirmation")
        return StageDecision("Expansion", rules, deteriorating)

    if (
        data.emerging_score >= 60
        and data.catalyst_score >= 55
        and data.entity_strength_score >= 55
        and data.confidence_score >= 55
        and data.crowding_proxy < 65
    ):
        rules.append("sustained acceleration with catalysts and entity confirmation")
        return StageDecision("Growth", rules, deteriorating)

    if (
        data.emerging_score >= 55
        and data.catalyst_score >= 45
        and 30 <= data.entity_strength_score <= 65
        and data.crowding_proxy < 45
    ):
        rules.append("early acceleration with visible catalysts and low crowding")
        return StageDecision("Early", rules, deteriorating)

    if (
        data.emerging_score < 45
        and data.entity_strength_score < 40
        and data.catalyst_score < 35
        and data.crowding_proxy < 30
    ):
        rules.append("low evidence and low crowding")
        return StageDecision("Seed", rules, deteriorating)

    composite = data.emerging_score * 0.36 + data.catalyst_score * 0.22 + data.entity_strength_score * 0.24 + data.confidence_score * 0.18
    if data.crowding_proxy >= 70:
        return StageDecision("Mature", ["crowding dominates available evidence"], deteriorating)
    if composite >= 72 and data.crowding_proxy >= 45:
        return StageDecision("Expansion", ["strong composite evidence with rising crowding"], deteriorating)
    if composite >= 64:
        return StageDecision("Growth", ["balanced growth-stage evidence"], deteriorating)
    if composite >= 50:
        return StageDecision("Early", ["early-stage evidence is present but incomplete"], deteriorating)
    return StageDecision("Seed", ["evidence remains preliminary"], deteriorating)


def compute_lifecycle_confidence(data: LifecycleInput) -> float:
    catalyst_confidence = mean([float(item.get("confidence_score", 0.0)) for item in data.key_catalysts]) if data.key_catalysts else 35.0
    strength_values = [float(item.get("catalyst_strength", 0.0)) for item in data.key_catalysts if float(item.get("catalyst_strength", 0.0)) > 0]
    catalyst_strength = mean(strength_values) if strength_values else catalyst_confidence
    history_quality = min(100.0, len(data.history) * 8.0)
    source_diversity = min(100.0, data.source_count * 25.0)
    crowding_clarity = max(data.crowding_proxy, 100.0 - data.crowding_proxy)
    base = clamp_score(
        data.confidence_score * 0.24
        + catalyst_confidence * 0.18
        + catalyst_strength * 0.30
        + data.entity_strength_score * 0.12
        + history_quality * 0.01
        + source_diversity * 0.11
        + crowding_clarity * 0.04
    )
    if not data.key_bottlenecks:
        return base
    bottleneck_strengths = [
        float(item.get("bottleneck_strength", 0.0))
        for item in data.key_bottlenecks
        if isinstance(item, dict) and float(item.get("bottleneck_strength", 0.0)) > 0
    ]
    bottleneck_clarity = mean(bottleneck_strengths) if bottleneck_strengths else 0.0
    return clamp_score(base + min(6.0, bottleneck_clarity * 0.06))


def compute_expected_next_stage(stage: str, deteriorating: bool) -> str:
    if deteriorating and stage in {"Growth", "Expansion", "Mature"}:
        return stage
    if stage not in LIFECYCLE_STAGES:
        return "Early"
    return expected_next_stage(stage)


def time_window_for_stage(stage: str) -> str:
    return {
        "Seed": "3-9 months",
        "Early": "1-6 months",
        "Growth": "1-3 months",
        "Expansion": "0-3 months",
        "Mature": "already priced / monitor risk",
    }.get(stage, "3-9 months")


def is_deteriorating(data: LifecycleInput) -> bool:
    if len(data.history) < 2:
        return False
    previous = data.history[-2]
    latest = data.history[-1]
    try:
        emerging_down = float(latest.get("emerging_score", data.emerging_score)) < float(previous.get("emerging_score", data.emerging_score))
        ai_down = float(latest.get("final_ai_score", data.final_ai_score)) < float(previous.get("final_ai_score", data.final_ai_score))
    except (TypeError, ValueError):
        return False
    return emerging_down and ai_down
