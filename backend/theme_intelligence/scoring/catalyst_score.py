from __future__ import annotations

from statistics import mean

from theme_intelligence.models import CatalystRecord, clamp_score


def compute_catalyst_score(catalysts: list[CatalystRecord]) -> float:
    if not catalysts:
        return 0.0
    top = sorted(
        catalysts,
        key=lambda item: getattr(item, "catalyst_strength", 0.0) or (item.impact_score + item.confidence_score) / 2.0,
        reverse=True,
    )[:5]
    strengths = [getattr(item, "catalyst_strength", 0.0) for item in top if getattr(item, "catalyst_strength", 0.0) > 0]
    if strengths:
        diversity = len({item.catalyst_type for item in top})
        return clamp_score(mean(strengths) * 0.86 + diversity * 3.5)
    impact = mean([item.impact_score for item in top])
    confidence = mean([item.confidence_score for item in top])
    diversity = len({item.catalyst_type for item in top})
    return clamp_score(impact * 0.55 + confidence * 0.30 + diversity * 5.0)
