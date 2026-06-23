from __future__ import annotations

from .portfolio_models import PortfolioThemeCandidate


MIN_THEME_WEIGHT = 5.0
MAX_THEME_WEIGHT = 35.0
MAX_BOTTLENECK_CLUSTER_WEIGHT = 45.0
MAX_BENEFICIARY_OVERLAP_WEIGHT = 40.0
MAX_MATURE_WEIGHT_NON_LOW_BUBBLE = 20.0


def objective_adjusted_score(candidate: PortfolioThemeCandidate, portfolio_type: str) -> float:
    score = candidate.eligible_score
    if portfolio_type == "maximum_conviction":
        score += candidate.conviction_score * 0.12 + candidate.risk_adjusted_score * 0.05
    elif portfolio_type == "balanced_growth":
        if candidate.lifecycle_stage in {"Early", "Growth"}:
            score += 8.0
    elif portfolio_type == "low_bubble":
        score += max(0.0, 55.0 - candidate.bubble_penalty) * 0.35
        score -= max(0.0, candidate.bubble_penalty - 35.0) * 0.65
    elif portfolio_type == "early_opportunity":
        if candidate.lifecycle_stage == "Seed":
            score += 12.0
        if candidate.lifecycle_stage == "Early":
            score += 16.0
        if candidate.lifecycle_stage == "Mature":
            score -= 25.0
    elif portfolio_type == "institutional":
        score += candidate.allocation_readiness * 0.05
        if candidate.lifecycle_stage == "Mature":
            score -= 5.0
    if candidate.conviction_level == "Avoid":
        score = 0.0
    return max(0.0, score)


def normalize_weights(raw: dict[str, float], min_weight: float = MIN_THEME_WEIGHT, max_weight: float = MAX_THEME_WEIGHT) -> dict[str, float]:
    if not raw:
        return {}
    total = sum(max(0.0, value) for value in raw.values())
    if total <= 0:
        equal = 100.0 / len(raw)
        return {key: equal for key in raw}

    weights = {key: max(0.0, value) / total * 100.0 for key, value in raw.items()}
    effective_min = min(min_weight, 100.0 / len(weights))
    effective_max = max(max_weight, 100.0 / len(weights))
    for _ in range(12):
        changed = False
        for key, value in list(weights.items()):
            capped = min(effective_max, max(effective_min, value))
            if abs(capped - value) > 0.0001:
                weights[key] = capped
                changed = True
        diff = 100.0 - sum(weights.values())
        if abs(diff) <= 0.0001:
            break
        if diff > 0:
            receivers = [key for key, value in weights.items() if value < effective_max - 0.0001]
        else:
            receivers = [key for key, value in weights.items() if value > effective_min + 0.0001]
        if not receivers:
            break
        step = diff / len(receivers)
        for key in receivers:
            weights[key] += step
        if not changed and abs(diff) <= 0.01:
            break

    rounded = {key: round(value, 2) for key, value in weights.items()}
    drift = round(100.0 - sum(rounded.values()), 2)
    if rounded and drift:
        key = max(rounded, key=rounded.get)
        rounded[key] = round(rounded[key] + drift, 2)
    return rounded
