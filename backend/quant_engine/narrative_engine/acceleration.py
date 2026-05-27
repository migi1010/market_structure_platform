from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from alpha_engine.scoring import bounded_score, confidence_label


NARRATIVE_STATES = {
    "emerging",
    "accelerating",
    "leadership",
    "crowded",
    "weakening",
    "defensive_rotation",
}


def enrich_theme_narrative(row: Mapping[str, Any]) -> dict[str, Any]:
    narrative = build_narrative_signal(row)
    return {
        **dict(row),
        "narrative_state": narrative["narrative_state"],
        "acceleration_velocity": narrative["acceleration_velocity"],
        "participation_breadth": narrative["participation_breadth"],
        "institutional_alignment": narrative["institutional_alignment"],
        "narrative_intelligence": narrative,
    }


def enrich_sector_narrative(row: Mapping[str, Any]) -> dict[str, Any]:
    sector_name = str(row.get("sector") or "Sector").strip()
    participation = _first_score(row.get("participation_strength"), row.get("confidence_score"), 45.0)
    proxy = {
        "theme": sector_name,
        "theme_strength_score": row.get("score"),
        "theme_capital_flow_score": row.get("flow"),
        "emerging_score": row.get("relative_strength"),
        "breadth_participation": participation,
        "overheating_score": 100.0 - _first_score(row.get("confidence_score"), 50.0),
        "relative_momentum": row.get("relative_strength"),
        "macro_alignment": row.get("flow"),
        "leadership_intelligence": {
            "leadership_score": row.get("score"),
            "acceleration_score": row.get("relative_strength"),
            "participation_score": participation,
            "confidence": row.get("confidence_score"),
            "representative_symbols": _sector_symbols(row),
        },
    }
    narrative = build_narrative_signal(proxy)
    narrative["narrative_id"] = f"sector_{_narrative_id(sector_name)}"
    narrative["representative_themes"] = [sector_name]
    return {
        **dict(row),
        "narrative_state": narrative["narrative_state"],
        "acceleration_velocity": narrative["acceleration_velocity"],
        "participation_breadth": narrative["participation_breadth"],
        "institutional_alignment": narrative["institutional_alignment"],
        "narrative_intelligence": narrative,
    }


def build_cross_theme_ranking(rows: Iterable[Mapping[str, Any]], limit: int = 8) -> dict[str, Any]:
    narratives = [build_narrative_signal(row) for row in rows]
    ranked = sorted(narratives, key=lambda item: (_number(item.get("narrative_strength")), _number(item.get("confidence"))), reverse=True)
    emerging = _rank_state(narratives, {"emerging", "accelerating"}, "acceleration_velocity", limit)
    weakening = _rank_state(narratives, {"weakening"}, "acceleration_velocity", limit, reverse=False)
    crowded = _rank_state(narratives, {"crowded"}, "narrative_strength", limit)
    defensive = _rank_state(narratives, {"defensive_rotation"}, "institutional_alignment", limit)
    finite_ranked = [item for item in ranked if item.get("narrative_strength") is not None]
    lifecycle_state = _aggregate_lifecycle(finite_ranked)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "live" if lifecycle_state == "live" else "partial_data" if finite_ranked else "unavailable",
        "lifecycle_state": lifecycle_state,
        "top_narratives": ranked[:limit],
        "emerging_narratives": emerging,
        "weakening_narratives": weakening,
        "crowded_narratives": crowded,
        "defensive_narratives": defensive,
        "narratives": ranked,
        "summary": _ranking_summary(ranked, emerging, weakening),
        "future_hooks": [
            "ai_narrative_prediction",
            "semantic_clustering",
            "macro_overlays",
            "market_regime_overlays",
            "cross_asset_intelligence",
            "capital_flow_graph",
            "event_correlation",
            "institutional_crowding_analysis",
        ],
    }


def build_narrative_signal(row: Mapping[str, Any]) -> dict[str, Any]:
    theme_name = str(row.get("theme") or row.get("theme_name") or "Theme").strip()
    leadership = row.get("leadership_intelligence") if isinstance(row.get("leadership_intelligence"), Mapping) else {}
    composites = leadership.get("composites") if isinstance(leadership.get("composites"), Mapping) else {}

    leadership_score = _first_score(row.get("leadership_score"), leadership.get("leadership_score"), row.get("theme_strength_score"))
    acceleration = _first_score(row.get("acceleration_score"), leadership.get("acceleration_score"), row.get("emerging_score"), row.get("narrative_acceleration"))
    participation = _first_score(row.get("participation_score"), leadership.get("participation_score"), row.get("breadth_participation"))
    momentum = _first_score(_composite_score(composites, "momentum_composite"), row.get("relative_momentum"), row.get("theme_strength_score"))
    smart_money = _first_score(_composite_score(composites, "smart_money_composite"), row.get("theme_capital_flow_score"), row.get("smart_money_accumulation"))
    sector_leadership = _first_score(_composite_score(composites, "sector_leadership_composite"), row.get("macro_alignment"))
    overheating = _first_score(row.get("overheating_score"))
    volatility_context = bounded_score(100.0 - overheating) if overheating is not None else None
    saturation = _first_score(row.get("narrative_saturation"), row.get("narrative_bubble_risk"))
    confidence = _first_score(leadership.get("confidence"), row.get("confidence_score"))

    narrative_strength = _weighted_score([
        (leadership_score, 0.28),
        (momentum, 0.22),
        (smart_money, 0.18),
        (sector_leadership, 0.14),
        (volatility_context, 0.08),
        (participation, 0.10),
    ])
    acceleration_velocity = _weighted_score([
        (acceleration, 0.38),
        (momentum, 0.24),
        (smart_money, 0.20),
        (participation, 0.18),
    ])
    participation_breadth = bounded_score(participation)
    institutional_alignment = _weighted_score([
        (smart_money, 0.35),
        (sector_leadership, 0.25),
        (leadership_score, 0.25),
        (volatility_context, 0.15),
    ])
    state = _narrative_state(theme_name, narrative_strength, acceleration_velocity, participation_breadth, institutional_alignment, saturation)
    lifecycle_state = _lifecycle(confidence, [narrative_strength, acceleration_velocity, participation_breadth, institutional_alignment])

    return {
        "narrative_id": _narrative_id(theme_name),
        "narrative_name": theme_name,
        "theme": theme_name,
        "narrative_strength": narrative_strength,
        "narrative_acceleration": acceleration_velocity,
        "narrative_saturation": saturation,
        "narrative_bubble_risk": _bubble_risk(saturation, acceleration_velocity),
        "acceleration_velocity": acceleration_velocity,
        "participation_breadth": participation_breadth,
        "institutional_alignment": institutional_alignment,
        "narrative_state": state,
        "representative_themes": [theme_name],
        "representative_symbols": _representative_symbols(row),
        "confidence": confidence,
        "confidence_label": confidence_label(confidence) if confidence is not None else "Unavailable",
        "lifecycle_state": lifecycle_state,
        "explanation": _explanation(theme_name, state, narrative_strength, acceleration_velocity, participation_breadth, institutional_alignment),
        "capital_flow_semantics": _capital_flow_semantics(theme_name, state, acceleration_velocity, participation_breadth, institutional_alignment),
        "summary": _explanation(theme_name, state, narrative_strength, acceleration_velocity, participation_breadth, institutional_alignment),
        "source": "theme_leadership_composites",
        "status": "partial_data" if lifecycle_state != "live" else "live",
    }


def _rank_state(items: list[dict[str, Any]], states: set[str], key: str, limit: int, reverse: bool = True) -> list[dict[str, Any]]:
    selected = [item for item in items if item.get("narrative_state") in states]
    return sorted(selected, key=lambda item: _number(item.get(key)), reverse=reverse)[:limit]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def _first_score(*values: Any) -> float | None:
    for value in values:
        if value is None:
            continue
        parsed = _number(value, math.nan)
        if math.isfinite(parsed):
            return bounded_score(parsed)
    return None


def _weighted_score(values: list[tuple[float | None, float]]) -> float | None:
    usable = [(score, weight) for score, weight in values if score is not None and math.isfinite(float(score))]
    if not usable:
        return None
    total = sum(max(weight, 0.0) for _, weight in usable) or 1.0
    return bounded_score(sum(float(score) * max(weight, 0.0) for score, weight in usable) / total)


def _bubble_risk(saturation: float | None, acceleration_velocity: float | None) -> float | None:
    if saturation is None and acceleration_velocity is None:
        return None
    sat = float(saturation or 0.0)
    accel = float(acceleration_velocity or 0.0)
    return bounded_score(sat * 0.62 + max(0.0, accel - 72.0) * 0.35)


def _composite_score(composites: Mapping[str, Any], composite_id: str) -> float | None:
    item = composites.get(composite_id)
    if not isinstance(item, Mapping):
        return None
    value = item.get("composite_score")
    parsed = _number(value, math.nan)
    return bounded_score(parsed) if math.isfinite(parsed) else None


def _narrative_state(theme: str, strength: float | None, velocity: float | None, breadth: float | None, alignment: float | None, saturation: float | None) -> str:
    strength_v = float(strength or 0.0)
    velocity_v = float(velocity or 0.0)
    breadth_v = float(breadth or 0.0)
    alignment_v = float(alignment or 0.0)
    saturation_v = float(saturation or 0.0)
    if not any(value is not None for value in (strength, velocity, breadth, alignment)):
        return "emerging"
    if saturation_v >= 72 and strength_v >= 62:
        return "crowded"
    if _is_defensive_theme(theme) and alignment_v >= 58 and breadth_v >= 52:
        return "defensive_rotation"
    if strength_v >= 70 and breadth_v >= 58:
        return "leadership"
    if velocity_v >= 66 and breadth_v >= 50:
        return "accelerating"
    if velocity_v >= 58 and strength_v < 66:
        return "emerging"
    if velocity_v <= 42 or breadth_v <= 40:
        return "weakening"
    return "emerging" if strength_v >= 52 else "weakening"


def _lifecycle(confidence: float | None, scores: list[float | None]) -> str:
    if not any(score is not None for score in scores):
        return "warming"
    if confidence is not None and confidence >= 62:
        return "live"
    return "partial_live"


def _aggregate_lifecycle(items: list[Mapping[str, Any]]) -> str:
    states = {str(item.get("lifecycle_state") or "partial_live") for item in items}
    if not states:
        return "warming"
    if "degraded" in states:
        return "degraded"
    if states == {"live"}:
        return "live"
    return "partial_live"


def _narrative_id(theme_name: str) -> str:
    return theme_name.strip().lower().replace("/", " ").replace("&", "and").replace(" ", "_")


def _representative_symbols(row: Mapping[str, Any]) -> list[str]:
    leadership = row.get("leadership_intelligence") if isinstance(row.get("leadership_intelligence"), Mapping) else {}
    symbols = leadership.get("representative_symbols") if isinstance(leadership.get("representative_symbols"), list) else None
    if symbols:
        return [str(symbol).upper() for symbol in symbols[:8]]
    leaders = row.get("leaders")
    if not isinstance(leaders, list):
        return []
    return [str(item.get("ticker")).upper() for item in leaders[:8] if isinstance(item, Mapping) and item.get("ticker")]


def _sector_symbols(row: Mapping[str, Any]) -> list[str]:
    companies = row.get("companies")
    if not isinstance(companies, list):
        return []
    return [str(item.get("ticker")).upper() for item in companies[:8] if isinstance(item, Mapping) and item.get("ticker")]


def _is_defensive_theme(theme: str) -> bool:
    lowered = theme.lower()
    return any(token in lowered for token in ("utility", "utilities", "healthcare", "consumer staples", "defensive", "nuclear", "grid"))


def _explanation(theme: str, state: str, strength: float | None, velocity: float | None, breadth: float | None, alignment: float | None) -> str:
    alignment_v = float(alignment or 0.0)
    if state == "accelerating":
        return f"{theme} participation broadening with improving acceleration across leadership factors."
    if state == "leadership":
        return f"{theme} is in leadership with broad participation and institutional alignment."
    if state == "crowded":
        return f"{theme} remains strong but crowding risk is elevated as narrative saturation rises."
    if state == "defensive_rotation":
        return "Defensive capital rotation increasing."
    if state == "weakening":
        return "Narrative momentum weakening as participation narrows."
    if alignment_v >= 60:
        return "Institutional alignment improving across leadership factors."
    return f"{theme} narrative is emerging with partial factor confirmation."


def _capital_flow_semantics(theme: str, state: str, velocity: float | None, breadth: float | None, alignment: float | None) -> str:
    lowered = theme.lower()
    breadth_v = float(breadth or 0.0)
    velocity_v = float(velocity or 0.0)
    alignment_v = float(alignment or 0.0)
    if "ai" in lowered and breadth_v >= 52:
        return "AI infrastructure participation broadening."
    if "semiconductor" in lowered and velocity_v >= 58:
        return "Semiconductor momentum leadership accelerating."
    if state == "defensive_rotation":
        return "Defensive capital rotation increasing."
    if state == "weakening":
        return "Narrative momentum weakening as participation narrows."
    if alignment_v >= 60:
        return "Institutional alignment improving across leadership factors."
    return f"{theme} narrative confirmation remains mixed."


def _ranking_summary(ranked: list[Mapping[str, Any]], emerging: list[Mapping[str, Any]], weakening: list[Mapping[str, Any]]) -> str:
    if not ranked:
        return "Narrative acceleration engine is warming up theme leadership inputs."
    top = ", ".join(str(item.get("narrative_name")) for item in ranked[:3])
    early = ", ".join(str(item.get("narrative_name")) for item in emerging[:2]) or "no confirmed early acceleration"
    weak = ", ".join(str(item.get("narrative_name")) for item in weakening[:2]) or "no major narrowing"
    return f"Top narratives: {top}. Emerging acceleration: {early}. Weakening pressure: {weak}."
