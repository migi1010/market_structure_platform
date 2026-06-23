from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from typing import Any

from alpha_engine.scoring import bounded_score
from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, get_cached_entry

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


def analyze_sector_rotation() -> dict[str, Any]:
    started = time.perf_counter()
    spy_entry = _cached_quote_entry("SPY")
    spy_change = _quote_change_percent(_entry_value(spy_entry))
    rows = [_sector_row(sector, etf, spy_change) for sector, etf in SECTOR_ETFS.items()]
    scored = [row for row in rows if row["score"] is not None]
    scored.sort(key=lambda row: float(row["score"]), reverse=True)
    unavailable = [row for row in rows if row["score"] is None]
    ranking = [*scored, *unavailable]
    available_count = len(scored)
    stale_count = sum(row["status"] == "stale" for row in scored)
    status = _snapshot_status(available_count, stale_count, spy_entry)
    ranking = [_with_snapshot_status(row, status) for row in ranking]
    normalized_scored = [row for row in ranking if row["score"] is not None]
    leaders = normalized_scored[:5]
    laggards = list(reversed(normalized_scored[-5:]))
    selected = _selected_sector(leaders[0]) if leaders else None
    updated_at = _latest_updated_at([spy_entry, *(_cached_quote_entry(etf) for etf in SECTOR_ETFS.values())])
    score_average = _average(scored, "score")
    flow_average = _average(scored, "flow")
    momentum_average = _average(scored, "momentum")
    snapshot = {
        "status": status,
        "source": "sector_etf_quote_cache" if available_count else "unavailable",
        "updated_at": updated_at,
        "market_regime": _band(score_average, 62.0, 45.0, "risk_on", "risk_off"),
        "risk_appetite": _band(flow_average, 60.0, 42.0, "expanding", "contracting"),
        "volatility_state": "unavailable",
        "rotation_bias": _band(momentum_average, 0.25, -0.25, "positive", "negative"),
        "leaders": leaders,
        "laggards": laggards,
        "sector_ranking": ranking,
        "selected_sector": selected,
        "diagnostics": [
            {"id": "coverage", "label": "Sector coverage", "value": available_count, "status": status},
            {"id": "freshness", "label": "Stale sectors", "value": stale_count, "status": "stale" if stale_count else status},
        ],
        "theme_links": [],
        "data_quality": {
            "available_sectors": available_count,
            "unavailable_sectors": len(rows) - available_count,
            "stale_sectors": stale_count,
            "total_sectors": len(rows),
            "benchmark_available": spy_change is not None,
            "coverage_ratio": round(available_count / len(rows), 4),
        },
    }
    logger.info("sector_rotation_compute_ms=%.2f", (time.perf_counter() - started) * 1000.0)
    return snapshot


def _sector_row(sector: str, etf: str, spy_change_percent: float | None) -> dict[str, Any]:
    entry = _cached_quote_entry(etf)
    quote = _entry_value(entry)
    price_change = _quote_change_percent(quote)
    volume_ratio = _volume_ratio(quote)
    row_status = _entry_status(entry)
    if price_change is None:
        return _empty_sector_row(sector, etf)

    benchmark_change = spy_change_percent if spy_change_percent is not None else price_change
    momentum = price_change
    relative_strength = bounded_score(50.0 + (price_change - benchmark_change) * 5.5)
    flow = bounded_score(50.0 + (volume_ratio - 1.0) * 28.0) if volume_ratio is not None else None
    momentum_score = bounded_score(50.0 + price_change * 4.5)
    score_inputs = [momentum_score, relative_strength, flow]
    available_inputs = [value for value in score_inputs if value is not None]
    score = sum(available_inputs) / len(available_inputs)
    confidence = 75.0 if volume_ratio is not None and spy_change_percent is not None else 55.0
    trend = "up" if price_change > 0.25 else "down" if price_change < -0.25 else "flat"
    return {
        "id": etf.lower(),
        "name": sector,
        "type": "sector",
        "sector": sector,
        "sector_id": sector.lower().replace(" ", "_"),
        "etf": etf,
        "score": round(score, 2),
        "momentum": round(momentum, 2),
        "relative_strength": round(relative_strength, 2),
        "flow": round(flow, 2) if flow is not None else None,
        "trend": trend,
        "rotation_state": _rotation_state(score),
        "status": row_status,
        "evidence_source": str(quote.get("source") or quote.get("quoteSource") or "persisted_quote_cache"),
        "updated_at": _entry_updated_at(entry),
        "linked_themes": [],
        "companies": [],
        "rotation_score": round(score, 2),
        "rotation_momentum": round(momentum, 2),
        "rotation_relative_strength": round(relative_strength, 2),
        "rotation_flow_quality": round(flow, 2) if flow is not None else None,
        "rotation_confidence": confidence,
        "confidence_score": confidence,
        "lifecycle_state": row_status,
    }


def _empty_sector_row(sector: str, etf: str) -> dict[str, Any]:
    return {
        "id": etf.lower(),
        "name": sector,
        "type": "sector",
        "sector": sector,
        "sector_id": sector.lower().replace(" ", "_"),
        "etf": etf,
        "score": None,
        "momentum": None,
        "relative_strength": None,
        "flow": None,
        "trend": "unavailable",
        "rotation_state": "Unavailable",
        "status": "unavailable",
        "evidence_source": None,
        "updated_at": None,
        "linked_themes": [],
        "companies": [],
        "rotation_score": None,
        "rotation_momentum": None,
        "rotation_relative_strength": None,
        "rotation_flow_quality": None,
        "rotation_confidence": None,
        "confidence_score": None,
        "lifecycle_state": "unavailable",
    }


def _cached_quote_entry(symbol: str) -> dict[str, Any] | None:
    normalized = symbol.strip().upper()
    for namespace in ("quote", "quote_lkg"):
        entry = get_cached_entry(
            f"{namespace}:{CACHE_SCHEMA_VERSION}:{normalized}",
            allow_expired=True,
        )
        if entry is not None:
            return {**entry, "cache_namespace": namespace}
    return None


def _entry_value(entry: dict[str, Any] | None) -> dict[str, Any]:
    value = entry.get("value") if isinstance(entry, dict) else None
    return value if isinstance(value, dict) else {}


def _entry_status(entry: dict[str, Any] | None) -> str:
    if not entry:
        return "unavailable"
    quote = _entry_value(entry)
    quote_status = str(quote.get("quoteStatus") or quote.get("status") or "").lower()
    if entry.get("cache_namespace") == "quote_lkg" or entry.get("is_expired") or quote.get("is_stale") or quote_status in {"stale", "fallback"}:
        return "stale"
    return "live"


def _entry_updated_at(entry: dict[str, Any] | None) -> str | None:
    if not entry:
        return None
    timestamp = _finite(entry.get("updated_at"))
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _latest_updated_at(entries: list[dict[str, Any] | None]) -> str | None:
    timestamps = [_finite(entry.get("updated_at")) for entry in entries if entry]
    finite_timestamps = [value for value in timestamps if value is not None]
    if not finite_timestamps:
        return None
    return datetime.fromtimestamp(max(finite_timestamps), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _snapshot_status(available_count: int, stale_count: int, spy_entry: dict[str, Any] | None) -> str:
    if available_count == 0:
        return "unavailable"
    if stale_count == available_count:
        return "stale"
    if available_count < len(SECTOR_ETFS) or stale_count > 0 or _entry_status(spy_entry) != "live":
        return "partial"
    return "live"


def _with_snapshot_status(row: dict[str, Any], snapshot_status: str) -> dict[str, Any]:
    if snapshot_status == "partial" and row["status"] == "live":
        return {**row, "status": "partial", "lifecycle_state": "partial"}
    return row


def _selected_sector(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sector": row["sector"],
        "sector_id": row["sector_id"],
        "leadership": row["score"],
        "momentum": row["momentum"],
        "flow": row["flow"],
        "related_themes": row["linked_themes"],
        "risk_overlay": None,
        "updated_at": row["updated_at"],
        "status": row["status"],
        "rotation_score": row["rotation_score"],
        "rotation_momentum": row["rotation_momentum"],
        "rotation_relative_strength": row["rotation_relative_strength"],
        "rotation_flow_quality": row["rotation_flow_quality"],
        "rotation_confidence": row["rotation_confidence"],
    }


def _quote_change_percent(quote: dict[str, Any]) -> float | None:
    value = _finite(
        quote.get("change_percent")
        or quote.get("regularMarketChangePercent")
        or quote.get("percent_change")
        or quote.get("changePercent")
    )
    if value is not None:
        return value * 100.0 if abs(value) <= 0.1 else value
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


def _average(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [_finite(row.get(key)) for row in rows]
    finite_values = [value for value in values if value is not None]
    return sum(finite_values) / len(finite_values) if finite_values else None


def _band(value: float | None, high: float, low: float, positive: str, negative: str) -> str:
    if value is None:
        return "unavailable"
    if value >= high:
        return positive
    if value <= low:
        return negative
    return "neutral"


def _finite(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _rotation_state(score: float) -> str:
    if score >= 65.0:
        return "Accumulation"
    if score <= 45.0:
        return "Distribution"
    return "Neutral"
