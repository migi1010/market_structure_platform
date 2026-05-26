from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from alpha_engine.scoring import bounded_score, confidence_label


CLASSIFICATIONS = {
    "strongest_leadership",
    "accelerating",
    "emerging",
    "weakening",
    "crowded",
    "defensive",
    "risk_on",
    "risk_off",
}


def enrich_universe_ranking(row: Mapping[str, Any], entity_type: str = "theme", rank: int | None = None) -> dict[str, Any]:
    screener = build_screener_row(row, entity_type=entity_type, rank=rank)
    return {
        **dict(row),
        "overall_rank": screener["overall_rank"],
        "ranking_score": screener["ranking_score"],
        "market_classification": screener["market_classification"],
        "universe_ranking": screener,
    }


def build_universe_ranking(rows: Iterable[Mapping[str, Any]], entity_type: str = "theme", limit: int = 10) -> dict[str, Any]:
    screener = [build_screener_row(row, entity_type=entity_type) for row in rows]
    ranked = sorted(
        screener,
        key=lambda item: (_rankable_score(item.get("ranking_score")), _rankable_score(item.get("confidence"))),
        reverse=True,
    )
    for index, row in enumerate(ranked, start=1):
        row["overall_rank"] = index
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "partial_data" if screener else "unavailable",
        "lifecycle_state": _aggregate_lifecycle(screener),
        "screener": ranked[:limit],
        "strongest_leadership": _classification_bucket(ranked, "strongest_leadership", limit),
        "accelerating": _classification_bucket(ranked, "accelerating", limit),
        "emerging": _classification_bucket(ranked, "emerging", limit),
        "weakening": _classification_bucket(ranked, "weakening", limit),
        "crowded": _classification_bucket(ranked, "crowded", limit),
        "defensive": _classification_bucket(ranked, "defensive", limit),
        "risk_on": _classification_bucket(ranked, "risk_on", limit),
        "risk_off": _classification_bucket(ranked, "risk_off", limit),
        "summary": _summary(ranked),
        "future_hooks": [
            "feature_store",
            "portfolio_optimizer",
            "ai_narrative_prediction",
            "cross_asset_ranking",
            "macro_overlays",
            "institutional_crowding_engine",
            "factor_attribution",
            "dynamic_universe_selection",
        ],
    }


def build_screener_row(row: Mapping[str, Any], entity_type: str = "theme", rank: int | None = None) -> dict[str, Any]:
    symbol = _symbol(row, entity_type)
    company_name = str(row.get("company_name") or row.get("theme") or row.get("sector") or symbol).strip()
    narrative = row.get("narrative_intelligence") if isinstance(row.get("narrative_intelligence"), Mapping) else {}
    leadership = row.get("leadership_intelligence") if isinstance(row.get("leadership_intelligence"), Mapping) else {}

    narrative_strength = _first_optional(row.get("narrative_strength"), narrative.get("narrative_strength"))
    narrative_acceleration = _first_optional(row.get("acceleration_velocity"), row.get("narrative_acceleration"), narrative.get("acceleration_velocity"))
    momentum_strength = _first_optional(row.get("momentum_strength"), row.get("relative_strength"), row.get("theme_strength_score"), row.get("alpha_score"))
    sector_leadership = _first_optional(row.get("sector_leadership"), row.get("sector_alignment"), row.get("leadership_score"), leadership.get("leadership_score"), row.get("score"))
    institutional_alignment = _first_optional(row.get("institutional_alignment"), narrative.get("institutional_alignment"), row.get("theme_capital_flow_score"), row.get("smart_money"))
    participation_breadth = _first_optional(row.get("participation_breadth"), row.get("participation_score"), row.get("breadth_participation"), narrative.get("participation_breadth"))
    volatility_quality = _volatility_quality(row)
    crowding_risk = _first_optional(row.get("crowding_risk"), row.get("overheating_score"), row.get("narrative_bubble_risk"), narrative.get("narrative_bubble_risk"), row.get("bubble_risk"))
    defensive_rotation = _defensive_rotation(row, narrative)
    confidence = _first_optional(row.get("confidence_score"), row.get("confidence"), leadership.get("confidence"), narrative.get("confidence"))
    lifecycle_state = _lifecycle(confidence, [narrative_strength, momentum_strength, sector_leadership, institutional_alignment])

    ranking_score = _ranking_score(
        momentum_strength=momentum_strength,
        narrative_acceleration=narrative_acceleration,
        sector_leadership=sector_leadership,
        institutional_alignment=institutional_alignment,
        participation_breadth=participation_breadth,
        volatility_quality=volatility_quality,
        crowding_risk=crowding_risk,
        defensive_rotation=defensive_rotation,
    )
    classification = _classification(
        row,
        ranking_score=ranking_score,
        narrative_acceleration=narrative_acceleration,
        participation_breadth=participation_breadth,
        institutional_alignment=institutional_alignment,
        crowding_risk=crowding_risk,
        defensive_rotation=defensive_rotation,
    )
    return {
        "symbol": symbol,
        "company_name": company_name,
        "entity_type": entity_type,
        "overall_rank": rank,
        "ranking_score": ranking_score,
        "confidence": confidence,
        "confidence_label": confidence_label(confidence) if confidence is not None else "Unavailable",
        "lifecycle_state": lifecycle_state,
        "narrative_strength": narrative_strength,
        "momentum_strength": momentum_strength,
        "sector_leadership": sector_leadership,
        "institutional_alignment": institutional_alignment,
        "participation_breadth": participation_breadth,
        "volatility_quality": volatility_quality,
        "crowding_risk": crowding_risk,
        "defensive_rotation": defensive_rotation,
        "risk_state": _risk_state(crowding_risk, volatility_quality),
        "crowding_state": _crowding_state(crowding_risk),
        "market_classification": classification,
        "explanation": _explanation(classification, row, ranking_score, narrative_acceleration, participation_breadth, institutional_alignment, crowding_risk),
        "status": "partial_data" if ranking_score is not None else "unavailable",
        "source": "factor_narrative_universe_ranking",
    }


def _ranking_score(
    *,
    momentum_strength: float | None,
    narrative_acceleration: float | None,
    sector_leadership: float | None,
    institutional_alignment: float | None,
    participation_breadth: float | None,
    volatility_quality: float | None,
    crowding_risk: float | None,
    defensive_rotation: float | None,
) -> float | None:
    values = [
        (momentum_strength, 0.20),
        (narrative_acceleration, 0.18),
        (sector_leadership, 0.16),
        (institutional_alignment, 0.18),
        (participation_breadth, 0.12),
        (volatility_quality, 0.08),
        (defensive_rotation, 0.04),
    ]
    usable = [(score, weight) for score, weight in values if _finite(score)]
    if not usable:
        return None
    total = sum(weight for _, weight in usable) or 1.0
    base = sum(float(score) * weight for score, weight in usable) / total
    penalty = max(0.0, float(crowding_risk or 0.0) - 70.0) * 0.22 if _finite(crowding_risk) else 0.0
    return bounded_score(base - penalty)


def _classification(
    row: Mapping[str, Any],
    *,
    ranking_score: float | None,
    narrative_acceleration: float | None,
    participation_breadth: float | None,
    institutional_alignment: float | None,
    crowding_risk: float | None,
    defensive_rotation: float | None,
) -> str:
    if _finite(crowding_risk) and float(crowding_risk) >= 72 and _finite(ranking_score) and float(ranking_score) >= 58:
        return "crowded"
    if _finite(defensive_rotation) and float(defensive_rotation) >= 58:
        return "defensive"
    if _finite(ranking_score) and float(ranking_score) >= 72 and _finite(participation_breadth) and float(participation_breadth) >= 55:
        return "strongest_leadership"
    if _finite(narrative_acceleration) and float(narrative_acceleration) >= 64:
        return "accelerating"
    if _finite(ranking_score) and float(ranking_score) <= 42:
        return "weakening"
    if _finite(institutional_alignment) and float(institutional_alignment) >= 60:
        return "risk_on"
    if _is_defensive_name(row):
        return "risk_off"
    return "emerging"


def _explanation(classification: str, row: Mapping[str, Any], ranking_score: float | None, acceleration: float | None, breadth: float | None, alignment: float | None, crowding: float | None) -> str:
    name = str(row.get("theme") or row.get("sector") or row.get("ticker") or row.get("symbol") or "Universe row")
    if classification in {"strongest_leadership", "risk_on"}:
        return "Institutional alignment strengthening across momentum and participation factors."
    if classification == "accelerating":
        return f"Narrative acceleration broadening into {name}."
    if classification == "crowded":
        return "Crowding risk increasing despite strong leadership."
    if classification in {"defensive", "risk_off"}:
        return "Defensive participation improving while momentum weakens."
    if classification == "weakening":
        return "Leadership weakening as participation and momentum fade."
    if ranking_score is None:
        return "Ranking unavailable until finite factor inputs arrive."
    return f"{name} is emerging with partial institutional confirmation."


def _symbol(row: Mapping[str, Any], entity_type: str) -> str:
    if row.get("ticker"):
        return str(row["ticker"]).upper()
    if row.get("symbol"):
        return str(row["symbol"]).upper()
    if row.get("theme"):
        return _slug(str(row["theme"]))
    if row.get("sector"):
        return _slug(str(row["sector"]))
    return _slug(entity_type)


def _slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.upper()).strip("_")
    return cleaned or "UNIVERSE"


def _first_optional(*values: Any) -> float | None:
    for value in values:
        if value is None:
            continue
        parsed = _number(value, math.nan)
        if math.isfinite(parsed):
            return bounded_score(parsed)
    return None


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def _finite(value: Any) -> bool:
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _rankable_score(value: Any) -> float:
    return float(value) if _finite(value) else -1.0


def _volatility_quality(row: Mapping[str, Any]) -> float | None:
    if _finite(row.get("volatility_quality")):
        return bounded_score(float(row["volatility_quality"]))
    if _finite(row.get("overheating_score")):
        return bounded_score(100.0 - float(row["overheating_score"]))
    if _finite(row.get("bubble_risk")):
        return bounded_score(100.0 - float(row["bubble_risk"]))
    return None


def _defensive_rotation(row: Mapping[str, Any], narrative: Mapping[str, Any]) -> float | None:
    if _is_defensive_name(row):
        return _first_optional(row.get("institutional_alignment"), narrative.get("institutional_alignment"), row.get("flow"), 55.0)
    return _first_optional(narrative.get("defensive_rotation"))


def _is_defensive_name(row: Mapping[str, Any]) -> bool:
    name = " ".join(str(row.get(key) or "") for key in ("theme", "sector", "company_name")).lower()
    return any(token in name for token in ("utility", "utilities", "healthcare", "consumer staples", "defensive", "grid", "nuclear"))


def _risk_state(crowding_risk: float | None, volatility_quality: float | None) -> str:
    if _finite(crowding_risk) and float(crowding_risk) >= 72:
        return "elevated"
    if _finite(volatility_quality) and float(volatility_quality) <= 38:
        return "fragile"
    return "balanced"


def _crowding_state(crowding_risk: float | None) -> str:
    if not _finite(crowding_risk):
        return "unknown"
    if float(crowding_risk) >= 72:
        return "crowded"
    if float(crowding_risk) <= 38:
        return "uncrowded"
    return "balanced"


def _lifecycle(confidence: float | None, scores: list[float | None]) -> str:
    if not any(_finite(score) for score in scores):
        return "partial_live"
    if _finite(confidence) and float(confidence) >= 62:
        return "live"
    return "partial_live"


def _aggregate_lifecycle(rows: list[Mapping[str, Any]]) -> str:
    states = {str(row.get("lifecycle_state") or "partial_live") for row in rows}
    if not states:
        return "warming"
    if "degraded" in states:
        return "degraded"
    if states == {"live"}:
        return "live"
    return "partial_live"


def _classification_bucket(rows: list[dict[str, Any]], classification: str, limit: int) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("market_classification") == classification][:limit]


def _summary(rows: list[Mapping[str, Any]]) -> str:
    ranked = [row for row in rows if row.get("ranking_score") is not None]
    if not ranked:
        return "Universe ranking awaits finite factor inputs."
    leaders = ", ".join(str(row.get("symbol")) for row in ranked[:3])
    return f"Top institutional leadership candidates: {leaders}."
