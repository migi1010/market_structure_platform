from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.data_pipeline import safe_float
from quant_engine.narrative_engine import build_cross_theme_ranking, enrich_theme_narrative
from quant_engine.ranking_engine import build_universe_ranking, enrich_universe_ranking
from quant_engine.theme_engine import enrich_theme_leadership
from settings import get_settings

from .supply_chain_mapper import map_supply_chain
from .theme_detector import ThemeDefinition, find_theme_exposure, get_theme_definitions
from .theme_scoring import detect_cross_asset_regime, score_theme, symbol_market_snapshot


def _time_bucket(seconds: int = 900) -> int:
    return int(time.time() // seconds)


@lru_cache(maxsize=4)
def _theme_snapshot(_: int) -> List[Dict[str, Any]]:
    definitions = get_theme_definitions()[:12]
    rows: List[Dict[str, Any]] = []
    for theme in definitions:
        try:
            row = _lightweight_theme_row(theme)
        except Exception:
            row = _fallback_theme_row(theme)
        rows.append(enrich_universe_ranking(enrich_theme_narrative(enrich_theme_leadership(row)), "theme"))
    rows.sort(key=lambda item: safe_float(item.get("ranking_score") or item.get("theme_strength_score")), reverse=True)
    return rows


def build_theme_snapshot() -> List[Dict[str, Any]]:
    return _theme_snapshot(_time_bucket())


def get_cached_theme_snapshot() -> List[Dict[str, Any]] | None:
    if _theme_snapshot.cache_info().currsize <= 0:
        return None
    return _theme_snapshot(_time_bucket())


def get_top_themes(limit: int = 10) -> Dict[str, Any]:
    themes = build_theme_snapshot()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cross_asset_regime": detect_cross_asset_regime(),
        "themes": themes[:limit],
        "summary": _summary(themes[:5]),
    }


def get_theme_rotation() -> Dict[str, Any]:
    themes = build_theme_snapshot()
    narrative_ranking = build_cross_theme_ranking(themes, limit=5)
    universe_ranking = build_universe_ranking(themes, entity_type="theme", limit=5)
    strengthening = sorted(themes, key=lambda item: safe_float(item.get("emerging_score")), reverse=True)[:5]
    weakening = sorted(themes, key=lambda item: safe_float(item.get("relative_momentum")))[:5]
    overheated = [item for item in themes if safe_float(item.get("overheating_score")) >= 62][:5]
    undervalued = [
        item for item in themes
        if safe_float(item.get("theme_strength_score")) >= 58
        and safe_float(item.get("overheating_score")) <= 45
        and safe_float(item.get("narrative_saturation")) <= 65
    ][:5]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rotation_map": themes[:10],
        "strengthening": strengthening,
        "weakening": weakening,
        "overheated_themes": overheated,
        "undervalued_themes": undervalued,
        "narrative_ranking": narrative_ranking,
        "universe_ranking": universe_ranking,
        "summary": _rotation_summary(strengthening, weakening),
    }


def get_theme_supply_chain(theme_name: str | None = None) -> Dict[str, Any]:
    definitions = get_theme_definitions()
    selected = definitions
    if theme_name:
        normalized = theme_name.strip().lower()
        selected = [theme for theme in definitions if normalized in theme.name.lower()] or definitions[:3]
    mapped = [map_supply_chain(theme) for theme in selected[:5]]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "themes": mapped,
    }


def theme_alignment_for_symbol(symbol: str, sector: str | None = None) -> Dict[str, Any]:
    exposures = find_theme_exposure(symbol, sector)
    if not exposures:
        return {
            "theme_alignment": 50.0,
            "theme_strength": 50.0,
            "theme_capital_flow": 50.0,
            "themes": [],
            "explanation": ["No concentrated theme exposure detected; ranking relies on stock-level factors."],
        }
    snapshot = {item["theme"]: item for item in build_theme_snapshot()}
    matches = [snapshot.get(theme.name) for theme in exposures if snapshot.get(theme.name)]
    if not matches:
        return {
            "theme_alignment": 50.0,
            "theme_strength": 50.0,
            "theme_capital_flow": 50.0,
            "themes": [theme.name for theme in exposures],
            "explanation": ["Theme exposure exists but live theme metrics are currently unavailable."],
        }
    top = sorted(matches, key=lambda item: safe_float(item.get("theme_strength_score")), reverse=True)[:3]
    strength = sum(safe_float(item.get("theme_strength_score")) for item in top) / len(top)
    flow = sum(safe_float(item.get("theme_capital_flow_score")) for item in top) / len(top)
    alignment = min(100.0, max(0.0, strength * 0.55 + flow * 0.35 + len(top) * 3.0))
    return {
        "theme_alignment": round(alignment, 2),
        "theme_strength": round(strength, 2),
        "theme_capital_flow": round(flow, 2),
        "themes": [str(item.get("theme")) for item in top],
        "explanation": [
            f"{item.get('theme')} strength {safe_float(item.get('theme_strength_score')):.0f} with capital flow {safe_float(item.get('theme_capital_flow_score')):.0f}."
            for item in top
        ],
    }


def _lightweight_theme_row(theme: ThemeDefinition) -> Dict[str, Any]:
    return _fallback_theme_row(theme)


def _fallback_theme_row(theme: ThemeDefinition) -> Dict[str, Any]:
    from quant_engine.factors.lightweight import score_basket, score_symbol  # noqa: PLC0415

    etf = theme.etf_symbols[0] if theme.etf_symbols else "SPY"
    factors = score_symbol(etf)
    # In Render survival mode, theme cards must stay ETF-first and compact.
    # Constituent sampling is bounded outside lightweight mode only.
    basket = (
        {"score": None, "volume_participation": None, "participation_score": None, "confidence_score": None, "leaders": []}
        if get_settings().miji_lightweight_mode
        else score_basket(theme.tickers, limit=5)
    )
    strength = _avg_optional(factors.get("alpha_score"), basket.get("score"), weights=(0.55, 0.45))
    flow = _weighted_optional([
        (factors.get("volume_participation"), 0.35),
        (factors.get("relative_strength_spy"), 0.35),
        (basket.get("volume_participation"), 0.20),
        (strength, 0.10),
    ])
    emerging = _weighted_optional([
        (factors.get("momentum_20d"), 0.26),
        (factors.get("momentum_60d"), 0.24),
        (factors.get("trend_consistency"), 0.20),
        (flow, 0.18),
        (basket.get("participation_score"), 0.12),
    ])
    overheating = _weighted_optional([
        (strength, 0.50),
        (flow, 0.30),
        (100.0 - float(factors.get("volatility_quality")), 0.20) if factors.get("volatility_quality") is not None else (None, 0.20),
    ])
    if overheating is not None:
        overheating = bounded_score(max(18.0, overheating - 16.0) + max(0.0, float(flow or 0.0) - 70.0) * 0.40)
    confidence = bounded_score(min(58.0, ((factors.get("confidence_score") or 24.0) + (basket.get("confidence_score") or 24.0)) / 2.0))
    participation = basket.get("participation_score")
    return {
        "theme": theme.name,
        "category": theme.category,
        "description": theme.description,
        "theme_strength_score": strength,
        "theme_capital_flow_score": flow,
        "emerging_score": emerging,
        "overheating_score": overheating,
        "relative_momentum": _centered_ratio(factors.get("momentum_60d")),
        "etf_relative_strength": _centered_ratio(factors.get("relative_strength_spy")),
        "volume_expansion": _volume_ratio(factors.get("volume_participation")),
        "institutional_accumulation": flow,
        "earnings_acceleration": 0.0,
        "revenue_acceleration": 0.0,
        "capex_trend": strength,
        "smart_money_accumulation": flow,
        "narrative_strength": strength,
        "narrative_acceleration": emerging,
        "narrative_saturation": overheating,
        "narrative_bubble_risk": _weighted_optional([(overheating, 0.62), (max(0.0, float(emerging) - 72.0) if emerging is not None else None, 0.35)]),
        "breadth_participation": participation,
        "leadership_concentration": 0.0,
        "relative_strength_vs_spy": factors.get("relative_strength_spy"),
        "relative_strength_qqq": factors.get("relative_strength_qqq"),
        "momentum_strength": factors.get("momentum_60d"),
        "trend_consistency": factors.get("trend_consistency"),
        "sector_leadership": strength,
        "options_activity": flow,
        "supply_chain_acceleration": emerging,
        "macro_alignment": strength,
        "leaders": [
            {
                "ticker": str(row.get("symbol") or "").upper(),
                "alpha_score": row.get("alpha_score"),
                "momentum_3m": row.get("momentum_strength"),
                "relative_volume": _volume_ratio(row.get("volume_participation")),
                "day_change_percent": None,
            }
            for row in (basket.get("leaders") or [])[:3]
        ],
        "etfs": list(theme.etf_symbols),
        "macro_tags": list(theme.macro_alignment),
        "confidence_score": confidence,
        "confidence_label": confidence_label(confidence),
        "lifecycle_state": "partial_live",
        "explainability": [f"Fallback row uses Render-safe 3-month ETF factors for {etf}."],
    }


def _avg_optional(first: Any, second: Any, weights: tuple[float, float] = (0.5, 0.5)) -> float | None:
    values: list[tuple[float, float]] = []
    for value, weight in ((first, weights[0]), (second, weights[1])):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            values.append((parsed, weight))
    if not values:
        return None
    total = sum(weight for _, weight in values) or 1.0
    return bounded_score(sum(value * weight for value, weight in values) / total)


def _weighted_optional(values: list[tuple[Any, float]]) -> float | None:
    usable: list[tuple[float, float]] = []
    for value, weight in values:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            usable.append((parsed, weight))
    if not usable:
        return None
    total = sum(weight for _, weight in usable) or 1.0
    return bounded_score(sum(value * weight for value, weight in usable) / total)


def _centered_ratio(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return round((bounded_score(parsed) - 50.0) / 100.0, 4) if math.isfinite(parsed) else None


def _volume_ratio(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return round(max(0.2, bounded_score(parsed) / 50.0), 4) if math.isfinite(parsed) else None


def _summary(themes: List[Dict[str, Any]]) -> str:
    if not themes:
        return "Theme engine is warming up live market data."
    top = ", ".join(str(item.get("theme")) for item in themes[:3])
    return f"{top} currently lead the universal theme ranking based on momentum, capital flow, narrative acceleration and macro alignment."


def _rotation_summary(strengthening: List[Dict[str, Any]], weakening: List[Dict[str, Any]]) -> str:
    strong = ", ".join(str(item.get("theme")) for item in strengthening[:3]) or "no confirmed themes"
    weak = ", ".join(str(item.get("theme")) for item in weakening[:2]) or "no major weakness"
    return f"Strengthening themes: {strong}. Weakening pressure is most visible in {weak}."
