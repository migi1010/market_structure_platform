from __future__ import annotations

import math
import logging
import time
from typing import Any, Dict, List

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, get_cached_value

logger = logging.getLogger("miji.api")

SECTOR_ETFS: dict[str, str] = {
    "Technology": "XLK",
    "Energy": "XLE",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Industrials": "XLI",
    "Utilities": "XLU",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

_SAFE_SECTOR_BASELINES: dict[str, tuple[float, float, float]] = {
    "Technology": (64.0, 62.0, 58.0),
    "Energy": (52.0, 51.0, 50.0),
    "Healthcare": (54.0, 53.0, 52.0),
    "Financials": (55.0, 54.0, 53.0),
    "Industrials": (56.0, 55.0, 54.0),
    "Utilities": (48.0, 49.0, 50.0),
    "Consumer Discretionary": (53.0, 52.0, 51.0),
    "Consumer Staples": (49.0, 50.0, 50.0),
    "Materials": (51.0, 50.0, 50.0),
    "Real Estate": (47.0, 48.0, 49.0),
    "Communication Services": (57.0, 56.0, 55.0),
}


def analyze_sector_rotation() -> List[Dict[str, Any]]:
    started = time.perf_counter()
    spy_quote = _cached_quote("SPY")
    spy_change = _quote_change_percent(spy_quote) or 0.0
    rows = [_sector_row(sector, etf, spy_change) for sector, etf in SECTOR_ETFS.items()]
    rows.sort(key=lambda row: float(row["score"]), reverse=True)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    logger.info("sector_rotation_compute_ms=%.2f", elapsed_ms)
    return rows


def _sector_row(sector: str, etf: str, spy_change_percent: float) -> Dict[str, Any]:
    quote = _cached_quote(etf)
    price_change = _quote_change_percent(quote)
    volume_ratio = _volume_ratio(quote)
    baseline_score, baseline_rs, baseline_flow = _SAFE_SECTOR_BASELINES[sector]

    if price_change is None:
        score = baseline_score
        relative_strength = baseline_rs
        flow = baseline_flow
        confidence = 30.0
        status = "partial_data"
        lifecycle_state = "partial_live"
    else:
        momentum_20d = bounded_score(50.0 + price_change * 4.5)
        momentum_60d = bounded_score(50.0 + price_change * 3.0)
        relative_strength = bounded_score(50.0 + (price_change - spy_change_percent) * 5.5)
        flow = bounded_score(50.0 + (volume_ratio - 1.0) * 28.0) if volume_ratio is not None else bounded_score((momentum_20d + momentum_60d) / 2.0)
        volatility_quality = bounded_score(100.0 - abs(price_change) * 7.5)
        trend_consistency = bounded_score((momentum_20d * 0.65) + (momentum_60d * 0.35))
        score = bounded_score(
            momentum_20d * 0.22
            + momentum_60d * 0.22
            + relative_strength * 0.24
            + flow * 0.18
            + volatility_quality * 0.08
            + trend_consistency * 0.06
        )
        confidence = 62.0 if volume_ratio is not None else 48.0
        status = "live" if confidence >= 60.0 else "partial_data"
        lifecycle_state = "partial_live"

    score = _finite_or_default(score, baseline_score)
    relative_strength = _finite_or_default(relative_strength, baseline_rs)
    flow = _finite_or_default(flow, baseline_flow)
    confidence = _finite_or_default(confidence, 30.0)
    return {
        "sector": sector,
        "score": round(score, 2),
        "relative_strength": round(relative_strength, 2),
        "flow": round(flow, 2),
        "rotation_state": _rotation_state(score),
        "confidence_score": round(confidence, 2),
        "confidence_label": confidence_label(confidence),
        "lifecycle_state": lifecycle_state,
        "status": status,
    }


def _cached_quote(symbol: str) -> dict[str, Any]:
    normalized = symbol.strip().upper()
    keys = (
        f"quote:{CACHE_SCHEMA_VERSION}:{normalized}",
        f"quote_lkg:{CACHE_SCHEMA_VERSION}:{normalized}",
    )
    for key in keys:
        cached = get_cached_value(key, allow_expired=True)
        if isinstance(cached, dict):
            return cached
    return {}


def _quote_change_percent(quote: dict[str, Any]) -> float | None:
    value = _finite(
        quote.get("change_percent")
        or quote.get("regularMarketChangePercent")
        or quote.get("percent_change")
        or quote.get("changePercent")
    )
    if value is not None:
        return value * 100.0 if abs(value) <= 1.0 else value
    price = _finite(quote.get("price") or quote.get("regularMarketPrice") or quote.get("currentPrice"))
    previous = _finite(quote.get("previousClose") or quote.get("regularMarketPreviousClose") or quote.get("previous_close"))
    if price is not None and previous is not None and previous > 0.0:
        return (price / previous - 1.0) * 100.0
    return None


def _volume_ratio(quote: dict[str, Any]) -> float | None:
    volume = _finite(quote.get("volume") or quote.get("regularMarketVolume"))
    average = _finite(
        quote.get("averageVolume")
        or quote.get("averageDailyVolume10Day")
        or quote.get("averageVolume10days")
    )
    if volume is None or average is None or average <= 0.0:
        return None
    return max(0.1, min(volume / average, 4.0))


def _finite(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _finite_or_default(value: Any, default: float) -> float:
    parsed = _finite(value)
    return bounded_score(parsed if parsed is not None else default)


def _rotation_state(score: float) -> str:
    if score >= 75.0:
        return "Accumulation"
    if score >= 55.0:
        return "Neutral"
    return "Distribution"
