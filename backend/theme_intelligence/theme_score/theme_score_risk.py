from __future__ import annotations

from typing import Any


LIFECYCLE_SCORE_WEIGHTS: dict[str, dict[str, float]] = {
    "Seed": {"opportunity": 55.0, "maturity": 25.0, "transition": 65.0},
    "Early": {"opportunity": 100.0, "maturity": 55.0, "transition": 90.0},
    "Growth": {"opportunity": 90.0, "maturity": 75.0, "transition": 80.0},
    "Expansion": {"opportunity": 70.0, "maturity": 90.0, "transition": 55.0},
    "Mature": {"opportunity": 40.0, "maturity": 95.0, "transition": 25.0},
}


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def rounded_score(value: float) -> float:
    return round(clamp_score(value), 2)


def lifecycle_weights(stage: str) -> dict[str, float]:
    return LIFECYCLE_SCORE_WEIGHTS.get(stage, LIFECYCLE_SCORE_WEIGHTS["Seed"])


def compute_risk_penalties(score_input: Any) -> dict[str, float]:
    bubble_penalty = clamp_score(getattr(score_input, "bubble_penalty", 0.0))
    crowding_proxy = clamp_score(getattr(score_input, "crowding_proxy", 0.0))
    bottleneck_strength = clamp_score(getattr(score_input, "bottleneck_strength", 0.0))
    resolution_probability = clamp_score(getattr(score_input, "resolution_probability", 0.0))

    unresolved_bottleneck_penalty = bottleneck_strength * (100.0 - resolution_probability) / 100.0
    lifecycle_stage = getattr(score_input, "lifecycle_stage", "Seed")
    lifecycle_stage_risk = {
        "Seed": 35.0,
        "Early": 20.0,
        "Growth": 12.0,
        "Expansion": 10.0,
        "Mature": 25.0,
    }.get(lifecycle_stage, 35.0)

    return {
        "bubble_penalty": rounded_score(bubble_penalty),
        "crowding_penalty": rounded_score(max(0.0, crowding_proxy - 45.0)),
        "unresolved_bottleneck_penalty": rounded_score(unresolved_bottleneck_penalty),
        "lifecycle_stage_risk": rounded_score(lifecycle_stage_risk),
    }
