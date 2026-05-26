from __future__ import annotations

import math
from typing import Any, Mapping

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.factors import COMPOSITE_DEFINITIONS, FactorResult, aggregate_composite


def enrich_theme_leadership(row: Mapping[str, Any]) -> dict[str, Any]:
    theme_name = str(row.get("theme") or "Theme").strip()
    strength = _score(row.get("theme_strength_score"))
    acceleration = _score(row.get("emerging_score"))
    participation = _score(row.get("breadth_participation"))
    flow = _score(row.get("theme_capital_flow_score"))
    relative_strength = bounded_score(50.0 + _number(row.get("relative_strength_vs_spy")) * 1.4)
    volume_anomaly = bounded_score(50.0 + (_number(row.get("volume_expansion"), 1.0) - 1.0) * 24.0)
    volatility_context = bounded_score(100.0 - _score(row.get("overheating_score")))
    sector_context = _score(row.get("macro_alignment"))
    confidence = _score(row.get("confidence_score"), 35.0)
    lifecycle_state = _lifecycle(confidence, [strength, acceleration, participation, flow])

    factors = {
        "simple_momentum": _factor("simple_momentum", strength, confidence, "theme_metrics", lifecycle_state, "Theme strength proxy."),
        "relative_strength": _factor("relative_strength", relative_strength, confidence, "theme_metrics", lifecycle_state, "Relative strength versus SPY."),
        "volatility_snapshot": _factor("volatility_snapshot", volatility_context, confidence, "theme_metrics", lifecycle_state, "Overheating-adjusted volatility context."),
        "volume_anomaly": _factor("volume_anomaly", volume_anomaly, confidence, "theme_metrics", lifecycle_state, "Theme volume expansion proxy."),
        "smart_money_partial": _factor("smart_money_partial", flow, confidence * 0.85, "theme_metrics", "partial_live", "Capital flow proxy."),
        "simple_sector_leadership": _factor("simple_sector_leadership", sector_context, confidence * 0.75, "theme_metrics", "partial_live", "Macro and sector alignment proxy."),
    }
    momentum = aggregate_composite(COMPOSITE_DEFINITIONS["momentum_composite"], factors)
    smart_money = aggregate_composite(COMPOSITE_DEFINITIONS["smart_money_composite"], factors)
    sector_leadership = aggregate_composite(COMPOSITE_DEFINITIONS["sector_leadership_composite"], factors)
    leadership_score = _weighted_score([
        (momentum.composite_score, 0.34),
        (smart_money.composite_score, 0.26),
        (sector_leadership.composite_score, 0.20),
        (participation, 0.20),
    ])
    leadership = {
        "theme_id": _theme_id(theme_name),
        "theme_name": theme_name,
        "leadership_score": leadership_score,
        "acceleration_score": acceleration,
        "participation_score": participation,
        "participating_sectors": [str(row.get("category") or "Market Theme")],
        "representative_symbols": _representative_symbols(row),
        "confidence": confidence,
        "confidence_label": confidence_label(confidence),
        "lifecycle_state": lifecycle_state,
        "status": "partial_data" if lifecycle_state != "live" else "live",
        "explanation": _theme_explanation(theme_name, leadership_score, acceleration, participation, flow),
        "capital_rotation": _capital_rotation_theme(theme_name, leadership_score, acceleration, participation),
        "composites": {
            "momentum_composite": momentum.to_dict(),
            "smart_money_composite": smart_money.to_dict(),
            "sector_leadership_composite": sector_leadership.to_dict(),
        },
        "future_hooks": [
            "narrative_acceleration",
            "theme_clustering",
            "macro_overlays",
            "ai_trend_prediction",
            "capital_flow_graph",
            "multi_theme_ranking",
        ],
    }
    return {
        **dict(row),
        "theme_id": leadership["theme_id"],
        "leadership_score": leadership_score,
        "acceleration_score": acceleration,
        "participation_score": participation,
        "lifecycle_state": lifecycle_state,
        "leadership_intelligence": leadership,
    }


def enrich_sector_leadership(row: Mapping[str, Any], rank: int | None = None) -> dict[str, Any]:
    sector_name = str(row.get("sector") or "Sector").strip()
    score = _score(row.get("score"))
    relative_strength = _score(row.get("relative_strength"))
    flow = _score(row.get("flow"))
    confidence = _score(row.get("confidence_score"), 35.0)
    companies = row.get("companies") if isinstance(row.get("companies"), list) else []
    positive = 0
    for company in companies:
        if isinstance(company, Mapping) and _number(company.get("change_percent")) > 0:
            positive += 1
    participation = bounded_score(positive / max(len(companies), 1) * 100.0) if companies else confidence
    lifecycle_state = _lifecycle(confidence, [score, relative_strength, flow, participation])
    leadership_state = _sector_state(score, flow)
    momentum_direction = "strengthening" if score >= 62 and flow >= 55 else "weakening" if score <= 42 or flow <= 42 else "neutral"
    enriched = {
        **dict(row),
        "sector_rank": rank,
        "leadership_state": leadership_state,
        "momentum_direction": momentum_direction,
        "participation_strength": participation,
        "lifecycle_state": lifecycle_state,
        "capital_rotation": _capital_rotation_sector(sector_name, leadership_state, momentum_direction, participation),
        "leadership_intelligence": {
            "sector_rank": rank,
            "leadership_state": leadership_state,
            "momentum_direction": momentum_direction,
            "participation_strength": participation,
            "confidence": confidence,
            "confidence_label": confidence_label(confidence),
            "lifecycle_state": lifecycle_state,
            "explanation": _sector_explanation(sector_name, score, relative_strength, flow, participation),
        },
    }
    return enriched


def _factor(factor_id: str, score: float | None, confidence: float, source: str, lifecycle_state: str, explanation: str) -> FactorResult:
    return FactorResult(
        factor_id=factor_id,
        score=score,
        confidence=bounded_score(confidence),
        status="live" if lifecycle_state == "live" and score is not None else "partial_data",
        source=source,
        freshness="live" if lifecycle_state == "live" else "partial",
        explanation=explanation,
        lifecycle_state=lifecycle_state if lifecycle_state in {"cold_start", "warming", "partial_live", "live", "degraded", "recovery"} else "partial_live",
    )


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def _score(value: Any, default: float = 50.0) -> float:
    return bounded_score(_number(value, default))


def _weighted_score(values: list[tuple[float | None, float]]) -> float | None:
    usable = [(score, weight) for score, weight in values if score is not None]
    if not usable:
        return None
    total_weight = sum(weight for _, weight in usable) or 1.0
    return bounded_score(sum(float(score) * weight for score, weight in usable) / total_weight)


def _lifecycle(confidence: float, scores: list[float | None]) -> str:
    if not any(score is not None for score in scores):
        return "warming"
    if confidence >= 62:
        return "live"
    return "partial_live"


def _theme_id(theme_name: str) -> str:
    return theme_name.strip().lower().replace("/", " ").replace("&", "and").replace(" ", "_")


def _representative_symbols(row: Mapping[str, Any]) -> list[str]:
    leaders = row.get("leaders")
    if not isinstance(leaders, list):
        return []
    symbols: list[str] = []
    for item in leaders[:6]:
        if isinstance(item, Mapping) and item.get("ticker"):
            symbols.append(str(item["ticker"]).upper())
    return symbols


def _theme_explanation(theme: str, leadership: float | None, acceleration: float, participation: float, flow: float) -> str:
    if leadership is None:
        return f"{theme} leadership is partial because confirming factor inputs are unavailable."
    if leadership >= 70 and acceleration >= 60:
        return f"Capital rotating into {theme} with accelerating leadership participation."
    if leadership >= 62:
        return f"{theme} leadership strengthening with improving participation."
    if participation <= 42:
        return "Momentum participation weakening."
    if flow >= 62:
        return f"Capital rotating into {theme}, but confirmation remains partial."
    return f"{theme} remains watchlist-level with mixed leadership confirmation."


def _capital_rotation_theme(theme: str, leadership: float | None, acceleration: float, participation: float) -> str:
    if leadership is not None and leadership >= 70:
        return f"Capital rotating into {theme}."
    if acceleration >= 62:
        return f"{theme} acceleration improving."
    if participation <= 42:
        return "Momentum participation weakening."
    return f"{theme} capital rotation is mixed."


def _sector_state(score: float, flow: float) -> str:
    if score >= 72 and flow >= 60:
        return "Leadership"
    if score >= 58:
        return "Accumulation"
    if score <= 42 or flow <= 40:
        return "Weakening"
    return "Neutral"


def _capital_rotation_sector(sector: str, state: str, direction: str, participation: float) -> str:
    if "semiconductor" in sector.lower() and direction == "strengthening":
        return "Semiconductor leadership strengthening."
    if state == "Leadership":
        return f"Capital rotating into {sector}."
    if participation >= 62 and sector.lower() in {"utilities", "healthcare", "consumer staples"}:
        return "Defensive sector participation increasing."
    if direction == "weakening":
        return "Momentum participation weakening."
    return f"{sector} rotation remains mixed."


def _sector_explanation(sector: str, score: float, relative_strength: float, flow: float, participation: float) -> str:
    if score >= 70:
        return f"{sector} is leading on relative strength, flow, and participation."
    if relative_strength >= 60 and flow >= 55:
        return f"{sector} leadership is improving with relative strength support."
    if participation <= 42:
        return "Momentum participation weakening."
    return f"{sector} leadership is neutral with partial confirmation."
