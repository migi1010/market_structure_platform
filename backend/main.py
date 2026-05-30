from __future__ import annotations

import logging
import math
import time
from concurrent.futures import TimeoutError, ThreadPoolExecutor
from contextlib import asynccontextmanager
from threading import Lock
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from alpha_engine.scoring import bounded_score, confidence_label
from backtesting import run_top_alpha_backtest
from logging_config import configure_logging
from middleware import RateLimitMiddleware, RequestLoggingMiddleware, TimeoutMiddleware
from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, debug_provider, get_cached_value, get_history, get_quote, initialize_cache, safe_float, set_cached_value
from quant_engine.sector_rotation_engine import analyze_sector_rotation
from quant_engine.stock_service import central_stock_enrichment, fallback_stock_payload
from settings import get_settings
from theme_engine import (
    analyze_all_narratives,
    get_emerging_themes,
    get_theme_capital_flow,
    get_theme_detail,
    get_theme_detail_static,
    get_theme_rotation,
    get_theme_stocks,
    get_theme_stocks_static,
    get_theme_supply_chain,
    get_top_themes,
)

configure_logging()
logger = logging.getLogger("miji.api")
settings = get_settings()
BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=4)
CACHE_MISS_WAIT_SECONDS = 12.0
LIFECYCLE_STATES = {"cold_start", "warming", "partial_live", "live", "degraded", "recovery"}
UNCACHEABLE_LIFECYCLES = {"cold_start", "warming", "partial_live", "degraded"}
SP500_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "LLY", "JPM", "XOM", "UNH"]
UNIVERSE_PRESETS = {
    "sp500": SP500_UNIVERSE,
    "nasdaq100": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "GOOGL", "COST", "TSLA", "AMD"],
    "sox": ["NVDA", "AMD", "AVGO", "QCOM", "AMAT", "LRCX", "KLAC", "TSM", "ASML", "MRVL"],
    "ai_infrastructure": ["NVDA", "AMD", "AVGO", "ANET", "VRT", "ETN", "DELL", "SMCI", "PWR", "TT"],
    "semiconductor": ["NVDA", "AMD", "AVGO", "QCOM", "AMAT", "LRCX", "KLAC", "TSM", "ASML", "MRVL"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "WMB"],
    "defense": ["LMT", "RTX", "NOC", "GD", "LHX", "BA", "HII", "TXT", "TDG", "GE"],
}
ALPHA_ENDPOINT_LOCK = Lock()
REGIME_ENDPOINT_LOCK = Lock()
_HEAVY_CIRCUITS: dict[str, dict[str, Any]] = {
    "alpha": {"opened_until": 0.0, "reason": ""},
    "regime": {"opened_until": 0.0, "reason": ""},
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_cache()
    logger.info("cache initialized at %s", settings.sqlite_cache_path)
    yield

app = FastAPI(
    title=settings.app_name,
    description="Institutional Alpha Intelligence Platform Quant Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_whitelist,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimeoutMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)


def _guard(task):
    try:
        return task()
    except Exception as exc:
        logger.exception("request failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _cache_key(namespace: str, *parts: Any) -> str:
    suffix = ":".join(str(part).strip().upper() for part in parts if str(part).strip())
    return f"endpoint:{namespace}:{suffix}" if suffix else f"endpoint:{namespace}"


def _schema_cache_key(namespace: str, *parts: Any) -> str:
    return _cache_key(CACHE_SCHEMA_VERSION, namespace, *parts)


def _finite_positive(value: Any) -> bool:
    try:
        parsed = float(value)
        return math.isfinite(parsed) and parsed > 0
    except (TypeError, ValueError):
        return False


def _finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _finite_value(value: Any) -> float | None:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def _weighted_score(values: list[tuple[Any, float]]) -> float | None:
    usable: list[tuple[float, float]] = []
    for value, weight in values:
        parsed = _finite_value(value)
        if parsed is not None:
            usable.append((parsed, weight))
    if not usable:
        return None
    total = sum(weight for _, weight in usable) or 1.0
    return bounded_score(sum(value * weight for value, weight in usable) / total)


def _centered_ratio(value: Any) -> float | None:
    parsed = _finite_value(value)
    return round((bounded_score(parsed) - 50.0) / 100.0, 4) if parsed is not None else None


def _volume_ratio(value: Any) -> float | None:
    parsed = _finite_value(value)
    return round(max(0.2, bounded_score(parsed) / 50.0), 4) if parsed is not None else None


def _contains_non_finite(value: Any) -> bool:
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_contains_non_finite(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_non_finite(item) for item in value)
    return False


def _payload_flagged_fallback(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("fallback") is True:
            return True
        engine = value.get("qlib_engine")
        if isinstance(engine, dict) and engine.get("mode") == "fallback":
            return True
        return any(_payload_flagged_fallback(item) for item in value.values())
    if isinstance(value, list):
        return any(_payload_flagged_fallback(item) for item in value)
    return False


def _score_available(value: Any, *keys: str) -> bool:
    if not isinstance(value, dict):
        return False
    return any(_finite_number(value.get(key)) for key in keys)


def _sector_rotation_rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("sectors", "items", "data", "results", "rows"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _sector_row_has_signal(row: dict) -> bool:
    return any(_finite_positive(row.get(key)) for key in ("score", "relative_strength", "flow"))


def _sector_rotation_has_signal(payload: Any) -> bool:
    rows = _sector_rotation_rows(payload)
    return bool(rows) and any(_sector_row_has_signal(row) for row in rows)


def _sector_row_is_valid(row: dict) -> bool:
    return all(_finite_positive(row.get(key)) for key in ("score", "relative_strength", "flow"))


def _stock_lifecycle(result: dict) -> str:
    if _payload_flagged_fallback(result):
        return "degraded"
    if not _finite_positive(result.get("price")):
        return "warming"
    quote = result.get("quote")
    quote_live = isinstance(quote, dict) and _finite_positive(quote.get("price")) and str(quote.get("status") or "").lower() not in {"unavailable", "fallback"}
    bubble = result.get("bubble_analysis_data")
    earnings = result.get("earnings_quality")
    smart = result.get("smart_money")
    intelligence_live = (
        _score_available(bubble, "bubble_index")
        and _score_available(earnings, "earnings_quality_score", "quality_score")
        and _score_available(smart, "smart_money_score", "score")
    )
    return "live" if quote_live and intelligence_live else "partial_live"


def _endpoint_lifecycle(cache_key: str, result: Any) -> str | None:
    lowered_key = cache_key.lower()
    if ":stock:" in lowered_key and isinstance(result, dict):
        return _stock_lifecycle(result)
    if _payload_flagged_fallback(result):
        return "degraded"
    return None


def _with_lifecycle(cache_key: str, result: Any, override: str | None = None) -> Any:
    if not isinstance(result, dict):
        return result
    lifecycle = override or _endpoint_lifecycle(cache_key, result)
    if lifecycle not in LIFECYCLE_STATES:
        return result
    return {**result, "lifecycle_state": lifecycle}


def _circuit_open(name: str) -> bool:
    return time.time() < float(_HEAVY_CIRCUITS.get(name, {}).get("opened_until", 0.0))


def _circuit_reason(name: str) -> str:
    return str(_HEAVY_CIRCUITS.get(name, {}).get("reason") or "heavy endpoint is cooling down")


def _open_circuit(name: str, reason: str) -> None:
    _HEAVY_CIRCUITS[name] = {
        "opened_until": time.time() + settings.alpha_regime_circuit_cooldown_seconds,
        "reason": reason,
    }


def _clear_circuit(name: str) -> None:
    _HEAVY_CIRCUITS[name] = {"opened_until": 0.0, "reason": ""}


def _cacheable_endpoint_result(cache_key: str, result: Any) -> bool:
    if not isinstance(result, (dict, list)):
        return True
    if _contains_non_finite(result):
        return False
    if _payload_flagged_fallback(result):
        return False
    lifecycle = _endpoint_lifecycle(cache_key, result)
    if lifecycle in UNCACHEABLE_LIFECYCLES:
        return False
    lowered_key = cache_key.lower()
    if ":stock:" in lowered_key and isinstance(result, dict):
        return _finite_positive(result.get("price"))
    if ":bubble:" in lowered_key and isinstance(result, dict):
        data = result.get("bubble_analysis_data") or result
        return data.get("bubble_index") is not None
    if ":smart_money:" in lowered_key and isinstance(result, dict):
        return result.get("smart_money_score") is not None
    if ":earnings_quality:" in lowered_key and isinstance(result, dict):
        return result.get("earnings_quality_score") is not None
    if ":market_overview" in lowered_key:
        items = result.get("items") if isinstance(result, dict) else result
        if isinstance(items, list):
            return any(_finite_positive(item.get("price")) for item in items if isinstance(item, dict))
        return False
    if ":sector_rotation" in lowered_key:
        return _sector_rotation_has_signal(result)
    return True


def _cached_response(cache_key: str, ttl_seconds: int, task: Callable[[], Any]) -> Any:
    cached = get_cached_value(cache_key)
    if cached is not None:
        logger.info("endpoint cache hit key=%s", cache_key)
        return cached
    started = time.perf_counter()
    try:
        result = task()
        cache_result = _with_lifecycle(cache_key, result)
        if _cacheable_endpoint_result(cache_key, cache_result):
            set_cached_value(cache_key, cache_result, ttl_seconds, "json")
        else:
            logger.warning("skipping endpoint cache write for low-quality result key=%s", cache_key)
        logger.info("endpoint cache miss key=%s duration=%.2fs", cache_key, time.perf_counter() - started)
        return cache_result
    except Exception:
        stale = get_cached_value(cache_key, allow_expired=True)
        if stale is not None:
            logger.warning("serving stale endpoint cache key=%s", cache_key)
            return _with_lifecycle(cache_key, stale, "recovery")
        raise


def _schedule_cache_refresh(cache_key: str, ttl_seconds: int, task: Callable[[], Any]) -> None:
    def refresh() -> None:
        try:
            result = task()
            cache_result = _with_lifecycle(cache_key, result)
            if _cacheable_endpoint_result(cache_key, cache_result):
                set_cached_value(cache_key, cache_result, ttl_seconds, "json")
            else:
                logger.warning("skipping background cache write for low-quality result key=%s", cache_key)
            logger.info("background cache refresh complete key=%s", cache_key)
        except Exception as exc:
            logger.warning("background cache refresh failed key=%s error=%s", cache_key, exc)

    BACKGROUND_EXECUTOR.submit(refresh)


def _fast_cached_response(cache_key: str, ttl_seconds: int, task: Callable[[], Any], fallback: Callable[[], Any]) -> Any:
    cached = get_cached_value(cache_key)
    if cached is not None:
        if _cacheable_endpoint_result(cache_key, cached):
            logger.info("endpoint cache hit key=%s", cache_key)
            return cached
        logger.warning("ignoring invalid endpoint cache key=%s", cache_key)
    stale = get_cached_value(cache_key, allow_expired=True)
    if stale is not None:
        if _cacheable_endpoint_result(cache_key, stale):
            logger.info("endpoint stale cache hit key=%s", cache_key)
            _schedule_cache_refresh(cache_key, ttl_seconds, task)
            return _with_lifecycle(cache_key, stale, "recovery")
        logger.warning("ignoring invalid stale endpoint cache key=%s", cache_key)
    future = BACKGROUND_EXECUTOR.submit(task)

    def store_result_when_ready(completed: Any) -> None:
        try:
            result = completed.result()
            cache_result = _with_lifecycle(cache_key, result)
            if _cacheable_endpoint_result(cache_key, cache_result):
                set_cached_value(cache_key, cache_result, ttl_seconds, "json")
            else:
                logger.warning("skipping deferred cache write for low-quality result key=%s", cache_key)
            logger.info("deferred cache fill complete key=%s", cache_key)
        except Exception as exc:
            logger.warning("deferred cache fill failed key=%s error=%s", cache_key, exc)

    future.add_done_callback(store_result_when_ready)
    started = time.perf_counter()
    try:
        result = future.result(timeout=CACHE_MISS_WAIT_SECONDS)
        cache_result = _with_lifecycle(cache_key, result)
        if _cacheable_endpoint_result(cache_key, cache_result):
            set_cached_value(cache_key, cache_result, ttl_seconds, "json")
        else:
            logger.warning("skipping endpoint cache write for low-quality result key=%s", cache_key)
        logger.info("endpoint cache miss key=%s duration=%.2fs", cache_key, time.perf_counter() - started)
        return cache_result
    except TimeoutError:
        logger.warning("endpoint timed out key=%s; serving fallback", cache_key)
        fallback_result = fallback()
        if ":sector_rotation" in cache_key.lower() and not _sector_rotation_has_signal(fallback_result):
            logger.warning("sector timeout fallback produced no finite score/RS/flow; recomputing fallback")
            fallback_result = _fallback_sector_rotation()
        return _with_lifecycle(cache_key, fallback_result, "degraded")
    except Exception as exc:
        logger.warning("endpoint failed key=%s; serving fallback error=%s", cache_key, exc)
        fallback_result = fallback()
        if ":sector_rotation" in cache_key.lower() and not _sector_rotation_has_signal(fallback_result):
            logger.warning("sector error fallback produced no finite score/RS/flow; recomputing fallback")
            fallback_result = _fallback_sector_rotation()
        return _with_lifecycle(cache_key, fallback_result, "degraded")


def _quote_aware_stock_fallback(symbol: str) -> dict:
    """Stock timeout fallback that reads the LKG quote before returning price=null.

    Phase 2.8B fix: _fast_cached_response() calls this when central_stock_enrichment()
    exceeds CACHE_MISS_WAIT_SECONDS (12s). The old static fallback_stock_payload()
    returned price=null unconditionally, discarding the quote already written to
    the SQLite LKG cache by get_quote() during Phase 1 of central_stock_enrichment().

    This function:
    1. Calls get_quote(symbol) — fast: reads from LKG SQLite cache in <50ms since
       Phase 1 of central_stock_enrichment() already executed and wrote the quote.
    2. If price is finite, returns a partial_live payload with real price + calibrating engines.
    3. If price is null (provider genuinely unavailable), falls through to fallback_stock_payload().

    The partial_live result does NOT set fallback=True so it is cacheable by
    _cacheable_endpoint_result() when price is present.
    """
    ticker = symbol.strip().upper()
    try:
        raw_quote = get_quote(ticker)
    except Exception as exc:
        logger.warning("_quote_aware_stock_fallback get_quote failed symbol=%s error=%s", ticker, exc)
        raw_quote = {}

    # Extract price from the provider quote dict (camelCase keys from yfinance/robust_quote_fetch)
    price_raw = raw_quote.get("currentPrice") or raw_quote.get("regularMarketPrice")
    try:
        price = float(price_raw) if price_raw is not None else None
        if price is not None and (not math.isfinite(price) or price <= 0):
            price = None
    except (TypeError, ValueError):
        price = None

    if price is None:
        # No live or LKG quote available — return the static fallback
        logger.warning("_quote_aware_stock_fallback no price available symbol=%s; serving static fallback", ticker)
        return fallback_stock_payload(ticker)

    # We have a finite price. Build a partial_live payload with calibrating engines.
    def _sf(v: Any) -> float | None:
        try:
            f = float(v)
            return f if math.isfinite(f) else None
        except (TypeError, ValueError):
            return None

    change = _sf(raw_quote.get("regularMarketChange"))
    change_pct = _sf(raw_quote.get("regularMarketChangePercent"))
    prev_close = _sf(raw_quote.get("previousClose") or raw_quote.get("regularMarketPreviousClose"))
    market_cap = _sf(raw_quote.get("marketCap"))
    quote_source = str(raw_quote.get("quoteSource") or raw_quote.get("_quote_source") or "last_known_good").lower()
    quote_status = str(raw_quote.get("quoteStatus") or "partial_live").lower()
    if quote_status in {"unavailable", "fallback", ""}:
        quote_status = "partial_live"

    from quant_engine.stock_service import COMMON_METADATA, _fallback_bubble, _fallback_earnings, _fallback_smart_money  # noqa: PLC0415
    metadata = COMMON_METADATA.get(ticker, {"company_name": ticker, "sector": "US Equity"})

    normalized_quote = {
        "ticker": ticker,
        "price": round(price, 4),
        "change": round(change, 4) if change is not None else None,
        "change_percent": round(change_pct, 4) if change_pct is not None else None,
        "previous_close": round(prev_close, 4) if prev_close is not None else None,
        "market_cap": market_cap,
        "pe_ratio": None,
        "ps_ratio": None,
        "currency": raw_quote.get("currency") or "USD",
        "status": quote_status,
        "source": quote_source,
    }
    logger.info("_quote_aware_stock_fallback partial_live symbol=%s price=%.4f source=%s",
                ticker, price, quote_source)
    return {
        "ticker": ticker,
        "company_name": metadata["company_name"],
        "price": round(price, 4),
        "change": normalized_quote["change"],
        "change_percent": normalized_quote["change_percent"],
        "market_cap": market_cap,
        "sector": metadata["sector"],
        "quote_status": quote_status,
        "quote": normalized_quote,
        "bubble_analysis_data": _fallback_bubble(ticker, raw_quote, price)["bubble_analysis_data"],
        "earnings_quality": _fallback_earnings(),
        "smart_money": _fallback_smart_money(),
        "analyst_targets": {"available": False, "high": None, "average": None, "low": None,
                            "average_target": None, "implied_upside": None,
                            "buy": None, "hold": None, "sell": None},
        "analyst_consensus": {"available": False, "high": None, "average": None, "low": None,
                              "average_target": None, "implied_upside": None,
                              "buy": None, "hold": None, "sell": None},
        "hmm_prediction": {
            "available": False,
            "predicted_trend": "Calibrating model...",
            "bull_probability": None,
            "bear_probability": None,
            "regime_state": "Awaiting regime confirmation...",
            "confidence": None,
            "message": "Enrichment engines are warming. Price data is live.",
        },
        "news": [],
    }


def _fallback_sector_rotation() -> list[dict]:
    from quant_engine.factors.lightweight import score_symbol  # noqa: PLC0415

    sectors = [
        ("Technology", "XLK"), ("Energy", "XLE"), ("Healthcare", "XLV"), ("Financials", "XLF"),
        ("Industrials", "XLI"), ("Utilities", "XLU"), ("Consumer Discretionary", "XLY"),
        ("Consumer Staples", "XLP"), ("Materials", "XLB"), ("Real Estate", "XLRE"),
        ("Communication Services", "XLC"), ("Defense", "ITA"), ("Infrastructure", "PAVE"),
        ("Commodities", "DBC"), ("Nuclear", "URA"), ("Shipping", "IYT"), ("Copper", "COPX"),
        ("Aerospace", "ITA"),
    ]
    rows: list[dict] = []

    def fallback_score_from_factors(factors: dict[str, Any]) -> float | None:
        return _weighted_score([
            (factors.get("alpha_score"), 0.30),
            (factors.get("momentum_20d"), 0.16),
            (factors.get("momentum_60d"), 0.20),
            (factors.get("relative_strength_spy"), 0.18),
            (factors.get("volatility_quality"), 0.08),
            (factors.get("trend_consistency"), 0.08),
        ])

    def fallback_rs_from_factors(factors: dict[str, Any], score: float | None) -> float | None:
        return _weighted_score([
            (factors.get("relative_strength_spy"), 0.60),
            (factors.get("relative_strength_qqq"), 0.20),
            (factors.get("momentum_60d"), 0.20),
            (score, 0.10),
        ])

    def fallback_flow_from_factors(factors: dict[str, Any], score: float | None, relative_strength: float | None) -> float | None:
        return _weighted_score([
            (factors.get("volume_participation"), 0.36),
            (factors.get("momentum_20d"), 0.18),
            (factors.get("momentum_60d"), 0.18),
            (relative_strength, 0.16),
            (score, 0.12),
        ])

    def quote_proxy_factors(etf: str) -> dict[str, Any]:
        """Small ETF quote proxy used only when 3-month history factors are unavailable.

        The timeout path must not expand sector constituents or run another engine.
        These proxies are quote-derived and low-confidence by design.
        """
        try:
            quote = get_quote(etf)
        except Exception as exc:
            logger.warning("sector fallback quote proxy failed etf=%s error=%s", etf, exc)
            quote = {}
        if not isinstance(quote, dict):
            quote = {}

        pct = _finite_value(
            quote.get("change_percent")
            or quote.get("regularMarketChangePercent")
            or quote.get("percent_change")
            or quote.get("changePercent")
        )
        if pct is None:
            price = _finite_value(
                quote.get("price")
                or quote.get("regularMarketPrice")
                or quote.get("currentPrice")
            )
            previous = _finite_value(
                quote.get("previousClose")
                or quote.get("regularMarketPreviousClose")
                or quote.get("previous_close")
            )
            if price is not None and previous is not None and previous > 0:
                pct = (price / previous - 1.0) * 100.0
        if pct is not None and abs(pct) <= 1.0:
            pct *= 100.0

        volume = _finite_value(quote.get("volume") or quote.get("regularMarketVolume"))
        average_volume = _finite_value(
            quote.get("averageVolume")
            or quote.get("averageDailyVolume10Day")
            or quote.get("averageVolume10days")
        )

        momentum = bounded_score(50.0 + pct * 4.5) if pct is not None else None
        participation = None
        if volume is not None and average_volume is not None and average_volume > 0:
            participation = bounded_score(50.0 + (volume / average_volume - 1.0) * 30.0)
        confidence = 38.0 if momentum is not None else 20.0
        return {
            "alpha_score": momentum,
            "momentum_20d": momentum,
            "momentum_60d": momentum,
            "relative_strength_spy": momentum,
            "relative_strength_qqq": momentum,
            "volume_participation": participation or momentum,
            "trend_consistency": momentum,
            "confidence_score": confidence,
        }

    def merge_quote_proxy(factors: dict[str, Any], etf: str) -> dict[str, Any]:
        if _weighted_score([
            (factors.get("alpha_score"), 1.0),
            (factors.get("momentum_20d"), 1.0),
            (factors.get("momentum_60d"), 1.0),
            (factors.get("relative_strength_spy"), 1.0),
            (factors.get("volume_participation"), 1.0),
        ]) is not None:
            return factors
        quote_factors = quote_proxy_factors(etf)
        merged = {**quote_factors, **factors}
        for key, value in quote_factors.items():
            if _finite_value(merged.get(key)) is None:
                merged[key] = value
        return merged

    def repair_row(row: dict, factors: dict[str, Any], etf: str) -> dict:
        factors = merge_quote_proxy(factors, etf)
        score = _finite_value(row.get("score")) or fallback_score_from_factors(factors)
        relative_strength = _finite_value(row.get("relative_strength")) or fallback_rs_from_factors(factors, score)
        flow = _finite_value(row.get("flow")) or fallback_flow_from_factors(factors, score, relative_strength)
        repaired = {
            **row,
            "score": bounded_score(score) if score is not None else None,
            "relative_strength": bounded_score(relative_strength) if relative_strength is not None else None,
            "flow": bounded_score(flow) if flow is not None else None,
        }
        if not _sector_row_is_valid(repaired):
            logger.warning("sector fallback row invalid %s", repaired)
        else:
            logger.info("sector fallback repaired %s", repaired)
        return repaired

    for sector, etf in sectors:
        factors: dict[str, Any] = {}
        try:
            factors = score_symbol(etf)
            score = fallback_score_from_factors(factors)
            relative_strength = fallback_rs_from_factors(factors, score)
            flow = fallback_flow_from_factors(factors, score, relative_strength)
            confidence = bounded_score(_finite_value(factors.get("confidence_score")) or 25.0)
        except Exception:
            score = None
            relative_strength = None
            flow = None
            confidence = 25.0
        row = {
            "sector": sector,
            "score": score,
            "relative_strength": relative_strength,
            "flow": flow,
            "rotation_state": "Partial Data" if score is None else "Partial Data" if confidence < 55 else "Accumulation" if score >= 65 else "Weakening" if score < 42 else "Neutral",
            "confidence_score": confidence,
            "confidence_label": confidence_label(confidence),
            "companies": [],
            "fallback": True,
            "status": "partial_data" if confidence < 62 else "live",
            "lifecycle_state": "partial_live",
            "message": "Using Render-safe 3-month ETF factor scores while live sector engine refreshes.",
        }
        rows.append(repair_row(row, factors, etf))
    if rows and not _sector_rotation_has_signal(rows):
        logger.warning("sector fallback payload all-null; forcing second ETF repair pass")
        repaired_rows: list[dict] = []
        for sector, etf in sectors:
            try:
                factors = score_symbol(etf)
            except Exception:
                factors = {}
            repaired_rows.append(repair_row({
                "sector": sector,
                "score": None,
                "relative_strength": None,
                "flow": None,
                "rotation_state": "Partial Data",
                "confidence_score": _finite_value(factors.get("confidence_score")) or 25.0,
                "confidence_label": confidence_label(_finite_value(factors.get("confidence_score")) or 25.0),
                "companies": [],
                "fallback": True,
                "status": "partial_data",
                "lifecycle_state": "partial_live",
                "message": "Using second-pass Render-safe ETF factor repair.",
            }, factors, etf))
        rows = repaired_rows
    return sorted(rows, key=lambda row: row["score"] if row["score"] is not None else -1.0, reverse=True)


def _sector_rotation_response() -> Any:
    live = analyze_sector_rotation()
    if _sector_rotation_has_signal(live):
        return live
    logger.warning("sector rotation live recompute produced no finite score/RS/flow; trying fallback")
    fallback = _fallback_sector_rotation()
    if _sector_rotation_has_signal(fallback):
        return fallback
    return {
        "status": "degraded",
        "lifecycle_state": "degraded",
        "reason": "Sector rotation unavailable: lightweight ETF factors did not produce finite score, relative strength, or flow.",
        "sectors": fallback,
    }


def _fallback_theme_top() -> dict:
    from quant_engine.factors.lightweight import score_symbol  # noqa: PLC0415
    from quant_engine.theme_engine import enrich_theme_leadership  # noqa: PLC0415

    theme_map = [
        ("AI Infrastructure", "SMH"), ("Semiconductor", "SMH"), ("HBM", "SMH"), ("Glass Substrate", "SMH"),
        ("Electric Grid", "XLU"), ("Nuclear Energy", "URA"), ("Energy", "XLE"), ("Defense", "ITA"),
        ("Healthcare", "XLV"), ("Financials", "XLF"), ("Shipping", "IYT"), ("Commodities", "DBC"),
        ("Copper Grid", "COPX"), ("Robotics", "BOTZ"), ("Cybersecurity", "CIBR"),
    ]
    theme_specificity = {
        "AI Infrastructure": 4.0,
        "Semiconductor": 2.0,
        "HBM": -2.0,
        "Glass Substrate": -8.0,
        "Electric Grid": 1.5,
        "Nuclear Energy": 0.5,
        "Defense": 1.0,
        "Copper Grid": -1.0,
        "Robotics": -3.0,
        "Cybersecurity": -1.5,
    }
    rows = []
    for index, (theme, etf) in enumerate(theme_map):
        factors: dict[str, Any] = {}
        try:
            factors = score_symbol(etf)
            adjustment = theme_specificity.get(theme, 0.0)
            base_strength = _finite_value(factors.get("alpha_score"))
            strength = bounded_score(base_strength + adjustment) if base_strength is not None else None
            flow = _weighted_score([(factors.get("volume_participation"), 0.35), (factors.get("relative_strength_spy"), 0.35), (strength, 0.30)])
            if flow is not None:
                flow = bounded_score(flow + adjustment * 0.35)
            emerging = _weighted_score([(factors.get("momentum_20d"), 0.28), (factors.get("momentum_60d"), 0.24), (flow, 0.28), (factors.get("trend_consistency"), 0.20)])
            confidence = bounded_score(factors.get("confidence_score") or 24.0)
            relative_momentum = _centered_ratio(factors.get("momentum_60d"))
            etf_relative_strength = _centered_ratio(factors.get("relative_strength_spy"))
            volume_expansion = _volume_ratio(factors.get("volume_participation"))
        except Exception:
            strength = None
            flow = None
            emerging = None
            confidence = 24.0
            relative_momentum = None
            etf_relative_strength = None
            volume_expansion = None
        overheating = _weighted_score([(strength, 0.55), (flow, 0.30), (100.0 - float(factors.get("volatility_quality")), 0.15) if factors.get("volatility_quality") is not None else (None, 0.15)])
        if overheating is not None:
            overheating = bounded_score(max(18.0, overheating - 16.0) + max(0.0, float(flow or 0.0) - 70.0) * 0.40)
        strength = bounded_score(strength - max(0.0, float(overheating or 0.0) - 70.0) * 0.12) if strength is not None else None
        rows.append({
            "theme": theme,
            "category": "Universal Theme",
            "description": "Live theme signal is calibrating.",
            "theme_strength_score": strength,
            "theme_capital_flow_score": flow,
            "emerging_score": emerging,
            "overheating_score": overheating,
            "status": "Partial Data" if strength is None else "Leadership" if strength >= 78 and (flow or 0.0) >= 65 else "Emerging" if (emerging or 0.0) >= 65 else "Accumulating" if strength >= 58 else "Cooling" if strength < 42 else "Watchlist",
            "confidence_score": confidence,
            "confidence_label": confidence_label(confidence),
            "data_completeness": confidence,
            "relative_momentum": relative_momentum,
            "etf_relative_strength": etf_relative_strength,
            "volume_expansion": volume_expansion,
            "institutional_accumulation": flow,
            "earnings_acceleration": 0.0,
            "revenue_acceleration": 0.0,
            "capex_trend": strength,
            "smart_money_accumulation": flow,
            "narrative_strength": strength,
            "narrative_acceleration": emerging,
            "narrative_saturation": overheating,
            "narrative_bubble_risk": _weighted_score([(overheating, 0.62), (max(0.0, float(emerging) - 72.0) if emerging is not None else None, 0.35)]),
            "breadth_participation": confidence,
            "leadership_concentration": 0.0,
            "relative_strength_vs_spy": factors.get("relative_strength_spy"),
            "relative_strength_qqq": factors.get("relative_strength_qqq"),
            "momentum_strength": factors.get("momentum_60d"),
            "trend_consistency": factors.get("trend_consistency"),
            "options_activity": flow,
            "supply_chain_acceleration": emerging,
            "macro_alignment": strength,
            "leaders": [],
            "etfs": [],
            "macro_tags": [],
            "explainability": ["Theme engine is using ETF and liquidity proxies while full supply-chain scoring refreshes."],
            "risks": ["Confidence is reduced until full constituent, narrative, and macro data are refreshed."],
            "fallback": True,
            "lifecycle_state": "live" if confidence >= 62 and strength is not None else "partial_live",
        })
    rows = sorted(rows, key=lambda row: row["theme_strength_score"] if row["theme_strength_score"] is not None else -1.0, reverse=True)
    rows = [enrich_theme_leadership(row) for row in rows]
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cross_asset_regime": {
            "risk_on_off": "Calibrating",
            "risk_on_score": None,
            "liquidity_regime": "Calibrating",
            "liquidity_score": None,
            "volatility_regime": "Calibrating",
            "volatility_score": None,
            "inflation_regime": "Calibrating",
            "inflation_score": None,
            "AI_capex_regime": "Calibrating",
            "AI_capex_score": None,
        },
        "themes": rows,
        "summary": "Using latest cached institutional intelligence while live theme data warms up.",
        "fallback": True,
    }


def _fallback_alpha(universe: str) -> dict:
    """
    Pure static instant fallback — ZERO network I/O, ZERO data fetching.

    The old implementation called central_stock_enrichment() + get_history() for up to 10
    symbols in the fallback path, making it MORE expensive than the live pipeline during
    an OOM/timeout event. This replacement is instant and allocation-free.

    Scores are graduated (not uniform 50.0) and confidence is explicitly low (28),
    signalling partial_data to the frontend lifecycle system.
    True live scores will replace this once the background pipeline completes.
    """
    from quant_engine.ranking_engine import build_universe_ranking, enrich_universe_ranking  # noqa: PLC0415

    universe_key = universe.lower().strip().replace(" ", "_").replace("/", "_").replace("-", "_")
    symbols = list(dict.fromkeys(UNIVERSE_PRESETS.get(universe_key, SP500_UNIVERSE)))[:10]
    rows = []
    # Graduated base scores by position: top symbol starts ~72, each position drops ~3.5pts.
    # This avoids the uniform-50 collapse that the old numeric-index fallback produced when exceptions
    # fired inside the enrichment loop.
    for index, symbol in enumerate(symbols):
        base  = bounded_score(72.0 - index * 3.5)
        qual  = bounded_score(70.0 - index * 2.8)
        smrt  = bounded_score(68.0 - index * 3.1)
        val   = bounded_score(55.0 - index * 1.8)
        mom   = bounded_score(65.0 - index * 2.4)
        conf  = 28.0  # intentionally low — signals partial data to frontend lifecycle
        rows.append(enrich_universe_ranking({
            "ticker": symbol,
            "company_name": symbol,
            "sector": "Calibrating",
            # Price fields are null — fallback must never emit a live price.
            "price": None,
            "change": None,
            "change_percent": None,
            "quote_status": "unavailable",
            "alpha_score": base,
            "base_alpha_score": base,
            "universe_context_score": base,
            "universe_adjustment": 0.0,
            "universe_percentile": round((len(symbols) - index - 1) / max(len(symbols) - 1, 1) * 100.0, 2),
            "rank_in_universe": index + 1,
            "universe": universe.upper(),
            "quality": qual,
            "growth": mom,
            "smart_money": smrt,
            "valuation": val,
            "earnings_quality": qual,
            "market_structure": mom,
            "bubble_risk": bounded_score(100.0 - val),
            "sector_alignment": mom,
            "theme_alignment": bounded_score((mom + smrt) / 2.0),
            "theme_strength": mom,
            "theme_capital_flow": smrt,
            "confidence_score": conf,
            "confidence_label": confidence_label(conf),
            "theme_explanation": ["Alpha engine warming up; static institutional position shown."],
            "suggested_action": "Hold",
            "factor_importance": {
                "quality": 0.20,
                "growth": 0.20,
                "smart_money": 0.20,
                "valuation": 0.15,
                "earnings_quality": 0.15,
                "market_structure": 0.10,
            },
            "bullish_factors": [],
            "risk_factors": ["Live alpha engine warming up; confidence is low until background pipeline completes."],
        }, "stock", index + 1))
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "universe": universe.upper(),
        "qlib_engine": {
            "available": False,
            "mode": "fallback",
            "provider": "Miji Quant",
            "factor_set": "Static Institutional Fallback",
        },
        "market_regime": {"name": "Calibrating", "confidence": 38.0},
        "factor_importance": {
            "quality": 0.20,
            "growth": 0.20,
            "smart_money": 0.20,
            "valuation": 0.15,
            "earnings_quality": 0.15,
            "market_structure": 0.10,
        },
        "top_alpha": rows,
        "recommendations": rows[:5],
        "universe_screener": build_universe_ranking(rows, entity_type="stock", limit=10),
        "summary": "Alpha pipeline warming up. Static institutional fallback shown. Scores update when live engine completes.",
        "fallback": True,
    }


def _partial_alpha(universe: str, reason: str) -> dict:
    from quant_engine.factors.lightweight import score_symbols  # noqa: PLC0415
    from quant_engine.ranking_engine import build_universe_ranking, enrich_universe_ranking  # noqa: PLC0415

    universe_key = universe.lower().strip().replace(" ", "_").replace("/", "_").replace("-", "_")
    symbols = list(dict.fromkeys(UNIVERSE_PRESETS.get(universe_key, SP500_UNIVERSE)))[:10]
    scored = score_symbols(symbols, limit=10)
    rows = []
    for index, factor_row in enumerate(scored):
        symbol = str(factor_row.get("symbol") or symbols[index]).upper()
        alpha_score = factor_row.get("alpha_score")
        confidence = factor_row.get("confidence_score")
        momentum = factor_row.get("momentum_strength")
        momentum_20d = factor_row.get("momentum_20d")
        momentum_60d = factor_row.get("momentum_60d")
        smart_money = factor_row.get("volume_participation")
        volatility_quality = factor_row.get("volatility_quality")
        drawdown_quality = factor_row.get("drawdown_pressure")
        trend = factor_row.get("trend_consistency")
        relative_strength = factor_row.get("relative_strength_spy")
        rows.append(enrich_universe_ranking({
            "ticker": symbol,
            "company_name": symbol,
            "sector": "Partial Data",
            "price": None,
            "change": None,
            "change_percent": None,
            "quote_status": "unavailable",
            "alpha_score": alpha_score,
            "base_alpha_score": alpha_score,
            "universe_context_score": alpha_score,
            "universe_adjustment": None,
            "universe_percentile": None,
            "rank_in_universe": index + 1,
            "universe": universe_key.upper(),
            "quality": volatility_quality,
            "growth": momentum,
            "momentum_20d": momentum_20d,
            "momentum_60d": momentum_60d,
            "relative_strength_spy": factor_row.get("relative_strength_spy"),
            "relative_strength_qqq": factor_row.get("relative_strength_qqq"),
            "volatility_quality": volatility_quality,
            "volume_participation": smart_money,
            "drawdown_pressure": drawdown_quality,
            "trend_consistency": trend,
            "smart_money": smart_money,
            "valuation": None,
            "earnings_quality": None,
            "market_structure": trend,
            "bubble_risk": bounded_score(100.0 - float(drawdown_quality)) if drawdown_quality is not None else None,
            "sector_alignment": relative_strength,
            "theme_alignment": relative_strength,
            "theme_strength": momentum,
            "theme_capital_flow": smart_money,
            "confidence_score": confidence,
            "confidence_label": confidence_label(float(confidence)) if confidence is not None else "Unavailable",
            "theme_explanation": [factor_row.get("explanation") or "Render-safe lightweight factor score."],
            "suggested_action": "Hold",
            "factor_importance": {
                "momentum": 0.33,
                "relative_strength": 0.28,
                "volatility_quality": 0.16,
                "volume_participation": 0.13,
                "risk_overlay": 0.10,
            },
            "bullish_factors": [],
            "risk_factors": [reason],
            "available": factor_row.get("available") is True,
            "status": "live" if factor_row.get("lifecycle_state") == "live" else "partial_data",
            "lifecycle_state": factor_row.get("lifecycle_state") or "partial_live",
            "lightweight_factors": factor_row.get("factors") or [],
        }, "stock", index + 1))
    rows = sorted(rows, key=lambda row: row.get("ranking_score") if row.get("ranking_score") is not None else row.get("alpha_score") or -1.0, reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank_in_universe"] = index
        row["overall_rank"] = index
        row["universe_percentile"] = round((len(rows) - index) / max(len(rows) - 1, 1) * 100.0, 2)
    finite_rows = [row for row in rows if row.get("alpha_score") is not None]
    live_rows = [row for row in finite_rows if row.get("lifecycle_state") == "live"]
    lifecycle_state = "live" if finite_rows and len(live_rows) == len(finite_rows) else "partial_live" if finite_rows else "warming"
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "universe": universe_key.upper(),
        "available": bool(finite_rows),
        "status": "live" if lifecycle_state == "live" else "partial_data",
        "lifecycle_state": lifecycle_state,
        "qlib_engine": {
            "available": False,
            "mode": "disabled",
            "provider": "Miji Quant",
            "factor_set": "Render-safe lightweight factors",
            "reason": reason,
        },
        "market_regime": {"name": "Partial Data", "confidence": None, "status": "partial_data"},
        "factor_importance": {
            "momentum": 0.33,
            "relative_strength": 0.28,
            "volatility_quality": 0.16,
            "volume_participation": 0.13,
            "risk_overlay": 0.10,
        },
        "top_alpha": rows,
        "recommendations": rows[:5],
        "universe_screener": build_universe_ranking(rows, entity_type="stock", limit=10),
        "summary": reason,
    }


def _partial_regime(reason: str) -> dict:
    return {
        "name": "Partial Data",
        "available": False,
        "status": "partial_data",
        "confidence": None,
        "confidence_label": "Unavailable",
        "states": [],
        "lifecycle_state": "partial_live",
        "summary": reason,
    }


def _alpha_top_response(universe: str) -> dict:
    normalized = universe.strip().lower()
    cache_key = _schema_cache_key("alpha_v5", normalized)
    cached = get_cached_value(cache_key)
    if cached is not None:
        return cached
    if not settings.miji_enable_heavy_alpha:
        result = _partial_alpha(normalized, "Heavy alpha pipeline is disabled by MIJI_ENABLE_HEAVY_ALPHA=false.")
        set_cached_value(cache_key, _with_lifecycle(cache_key, result, result.get("lifecycle_state", "partial_live")), settings.alpha_ranking_ttl_seconds, "json")
        return result
    if _circuit_open("alpha"):
        result = _partial_alpha(normalized, _circuit_reason("alpha"))
        set_cached_value(cache_key, _with_lifecycle(cache_key, result, result.get("lifecycle_state", "partial_live")), settings.alpha_ranking_ttl_seconds, "json")
        return result
    if not ALPHA_ENDPOINT_LOCK.acquire(blocking=False):
        result = _partial_alpha(normalized, "Heavy alpha pipeline is already running; returning partial data.")
        set_cached_value(cache_key, _with_lifecycle(cache_key, result, result.get("lifecycle_state", "partial_live")), settings.alpha_ranking_ttl_seconds, "json")
        return result
    try:
        from quant_engine.qlib_engine import run_alpha_ranking  # noqa: PLC0415

        result = run_alpha_ranking(normalized)
        cache_result = _with_lifecycle(cache_key, result)
        if _cacheable_endpoint_result(cache_key, cache_result):
            set_cached_value(cache_key, cache_result, settings.alpha_ranking_ttl_seconds, "json")
        _clear_circuit("alpha")
        return cache_result
    except Exception as exc:
        reason = f"Heavy alpha pipeline failed; circuit open for cooldown: {exc}"
        logger.warning("alpha endpoint failed universe=%s error=%s", normalized, exc)
        _open_circuit("alpha", reason)
        stale = get_cached_value(cache_key, allow_expired=True)
        if stale is not None:
            return _with_lifecycle(cache_key, stale, "recovery")
        return _partial_alpha(normalized, reason)
    finally:
        ALPHA_ENDPOINT_LOCK.release()


def _market_regime_response() -> dict:
    cache_key = _schema_cache_key("market_regime")
    cached = get_cached_value(cache_key)
    if cached is not None:
        return cached
    if not settings.miji_enable_heavy_regime:
        return _partial_regime("Heavy regime model is disabled by MIJI_ENABLE_HEAVY_REGIME=false.")
    if _circuit_open("regime"):
        return _partial_regime(_circuit_reason("regime"))
    if not REGIME_ENDPOINT_LOCK.acquire(blocking=False):
        return _partial_regime("Heavy regime model is already running; returning partial data.")
    try:
        from quant_engine.regime_engine import detect_market_regime  # noqa: PLC0415

        result = detect_market_regime()
        cache_result = _with_lifecycle(cache_key, result)
        if _cacheable_endpoint_result(cache_key, cache_result):
            set_cached_value(cache_key, cache_result, settings.market_regime_ttl_seconds, "json")
        _clear_circuit("regime")
        return cache_result
    except Exception as exc:
        reason = f"Heavy regime model failed; circuit open for cooldown: {exc}"
        logger.warning("market regime endpoint failed error=%s", exc)
        _open_circuit("regime", reason)
        stale = get_cached_value(cache_key, allow_expired=True)
        if stale is not None:
            return _with_lifecycle(cache_key, stale, "recovery")
        return _partial_regime(reason)
    finally:
        REGIME_ENDPOINT_LOCK.release()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "cache_path": str(settings.sqlite_cache_path),
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception):
    logger.exception("unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/stock/{ticker}")
def get_stock(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: _fast_cached_response(_schema_cache_key("stock", symbol), settings.quote_ttl_seconds, lambda: central_stock_enrichment(symbol), lambda: _quote_aware_stock_fallback(symbol)))


@app.get("/debug/provider/{ticker}")
def get_provider_debug(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: debug_provider(symbol))


@app.get("/alpha/top")
def get_alpha_top(universe: str = Query("sp500")) -> dict:
    return _guard(lambda: _alpha_top_response(universe))


@app.get("/backtest/top-alpha")
def backtest_top_alpha(
    universe: str = Query("sp500", pattern="^(sp500|nasdaq100)$"),
    years: int = Query(3, ge=1, le=5),
) -> dict:
    return _guard(lambda: run_top_alpha_backtest(universe=universe, years=years))


@app.get("/bubble/{ticker}")
def get_bubble(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    def build() -> dict:
        stock = central_stock_enrichment(symbol)
        quote = stock.get("quote") or {}
        return {
            "ticker": symbol,
            "company_name": stock.get("company_name", symbol),
            "price": quote.get("price"),
            "sector": stock.get("sector", "US Equity"),
            "quote": quote,
            "bubble_analysis_data": stock.get("bubble_analysis_data"),
        }

    return _guard(lambda: _cached_response(_schema_cache_key("bubble", symbol), settings.fundamentals_ttl_seconds, build))


@app.get("/market/regime")
def get_market_regime() -> dict:
    return _guard(_market_regime_response)


@app.get("/market/overview")
def get_market_overview() -> dict:
    symbols = ["SPY", "QQQ", "SMH", "DIA", "IWM", "XLK", "XLF", "XLE"]
    per_symbol_budget_seconds = 2.5
    overview_budget_seconds = 5.0

    def finite_or_none(value: Any) -> float | None:
        try:
            parsed = float(value)
            return parsed if math.isfinite(parsed) else None
        except (TypeError, ValueError):
            return None

    def fallback_item(symbol: str, reason: str) -> dict:
        return {
            "ticker": symbol,
            "price": None,
            "change": None,
            "change_percent": None,
            "quote_status": "unavailable",
            "lifecycle_state": "degraded",
            "reason": reason,
        }

    def quote_item(symbol: str) -> dict:
        quote = get_quote(symbol)
        price = finite_or_none(quote.get("currentPrice") or quote.get("regularMarketPrice") or quote.get("price"))
        change = finite_or_none(quote.get("regularMarketChange") or quote.get("change"))
        change_percent = finite_or_none(quote.get("regularMarketChangePercent") or quote.get("change_percent"))
        status = str(quote.get("quoteStatus") or quote.get("quote_status") or "").lower()
        if not status:
            status = "live" if price is not None else "unavailable"
        return {
            "ticker": symbol,
            "price": round(price, 2) if price is not None else None,
            "change": round(change, 2) if change is not None else None,
            "change_percent": round(change_percent, 2) if change_percent is not None else None,
            "quote_status": status,
            "lifecycle_state": "live" if price is not None and status not in {"unavailable", "fallback"} else "degraded",
        }

    def bounded_quote(symbol: str, timeout_seconds: float) -> tuple[dict, float, str | None]:
        started = time.perf_counter()
        future = BACKGROUND_EXECUTOR.submit(lambda: quote_item(symbol))
        try:
            item = future.result(timeout=timeout_seconds)
            return item, (time.perf_counter() - started) * 1000.0, None
        except TimeoutError:
            future.cancel()
            logger.warning("market overview quote timed out symbol=%s", symbol)
            return fallback_item(symbol, "quote_timeout"), (time.perf_counter() - started) * 1000.0, f"{symbol}:timeout"
        except Exception as exc:
            logger.warning("market overview quote failed symbol=%s error=%s", symbol, exc)
            return fallback_item(symbol, "quote_error"), (time.perf_counter() - started) * 1000.0, f"{symbol}:error"

    def build() -> dict:
        started = time.perf_counter()
        tape: list[dict] = []
        degraded_sections: list[str] = []
        timing_ms: dict[str, float] = {}
        for symbol in symbols:
            remaining = overview_budget_seconds - (time.perf_counter() - started)
            if remaining <= 0:
                tape.append(fallback_item(symbol, "overview_budget_exceeded"))
                degraded_sections.append(f"{symbol}:budget")
                continue
            item, elapsed_ms, degraded = bounded_quote(symbol, min(per_symbol_budget_seconds, remaining))
            tape.append(item)
            timing_ms[symbol] = round(elapsed_ms, 2)
            if degraded:
                degraded_sections.append(degraded)
        live_count = sum(1 for item in tape if _finite_positive(item.get("price")))
        lifecycle_state = "live" if live_count == len(tape) else "partial_live" if live_count > 0 else "degraded"
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "overview_status": lifecycle_state,
            "lifecycle_state": lifecycle_state,
            "degraded_sections": degraded_sections,
            "timing_ms": {**timing_ms, "total": round((time.perf_counter() - started) * 1000.0, 2)},
            "items": tape,
        }

    return _guard(lambda: _cached_response(_schema_cache_key("market_overview_v2"), settings.market_overview_ttl_seconds, build))


@app.get("/overview")
def get_overview() -> dict:
    return get_market_overview()


@app.get("/sector/rotation")
def get_sector_rotation() -> Any:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("sector_rotation_v3"), settings.sector_rotation_ttl_seconds, _sector_rotation_response, _fallback_sector_rotation))


@app.get("/theme/top")
def get_theme_top() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v4", "top"), settings.theme_ttl_seconds, get_top_themes, _fallback_theme_top))


@app.get("/theme/emerging")
def get_theme_emerging() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v4", "emerging"), settings.theme_ttl_seconds, get_emerging_themes, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "emerging_themes": _fallback_theme_top()["themes"][:6], "summary": "Theme engine calibrating. No active emerging signal confirmed yet.", "fallback": True}))


@app.get("/theme/rotation")
def get_theme_rotation_endpoint() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v4", "rotation"), settings.theme_ttl_seconds, get_theme_rotation, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rotation_map": _fallback_theme_top()["themes"], "strengthening": [], "weakening": [], "overheated_themes": [], "undervalued_themes": [], "summary": "Theme rotation matrix is calibrating.", "fallback": True}))


@app.get("/theme/capital-flow")
def get_theme_capital_flow_endpoint() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v4", "capital_flow"), settings.theme_ttl_seconds, get_theme_capital_flow, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "capital_flow": _fallback_theme_top()["themes"][:8], "summary": "Capital flow engine warming. Awaiting finite lightweight factor inputs.", "fallback": True}))


@app.get("/theme/supply-chain")
def get_theme_supply_chain_endpoint(theme: str | None = None) -> dict:
    key = _schema_cache_key("theme_v4", "supply_chain", theme or "all")
    return _guard(lambda: _fast_cached_response(key, settings.theme_ttl_seconds, lambda: get_theme_supply_chain(theme), lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "themes": [], "summary": "Supply chain map calibrating.", "fallback": True}))


@app.get("/theme/narrative")
def get_theme_narrative_endpoint() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v4", "narrative"), settings.theme_ttl_seconds, analyze_all_narratives, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "narratives": [], "summary": "Narrative engine calibrating.", "fallback": True}))


@app.get("/theme/{theme_id:path}/stocks")
def get_theme_stocks_endpoint(theme_id: str) -> dict:
    normalized = theme_id.strip().lower()
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v4", "stocks", normalized), settings.theme_ttl_seconds, lambda: get_theme_stocks(theme_id), lambda: get_theme_stocks_static(theme_id)))


@app.get("/theme/{theme_id:path}/detail")
def get_theme_detail_endpoint(theme_id: str) -> dict:
    normalized = theme_id.strip().lower()
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v4", "detail", normalized), settings.theme_ttl_seconds, lambda: get_theme_detail(theme_id), lambda: get_theme_detail_static(theme_id)))


@app.get("/smart-money/{ticker}")
def get_smart_money(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: _cached_response(_schema_cache_key("smart_money", symbol), settings.quote_ttl_seconds, lambda: central_stock_enrichment(symbol).get("smart_money")))


@app.get("/earnings-quality/{ticker}")
def get_earnings_quality(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: _cached_response(_schema_cache_key("earnings_quality", symbol), settings.fundamentals_ttl_seconds, lambda: central_stock_enrichment(symbol).get("earnings_quality")))


@app.api_route("/warmup", methods=["GET", "POST"])
def warmup() -> dict:
    """
    Scheduled warmup: populates the SQLite cache for high-traffic endpoints.

    Memory-safe design for Render Free Tier:
    - Tasks are submitted in batches of 2 with 1-second gaps between batches.
    - Only lightweight essential endpoints are warmed (stock quotes, market overview).
    - Heavy pipelines (alpha ranking, theme, regime) are deferred to on-demand first access.
      The _fast_cached_response pattern handles them: it serves a static fallback instantly
      while the live pipeline runs in the background and populates the cache.
    - Warming alpha/theme/regime here would create a concurrent memory spike and is removed.
    """
    started = time.perf_counter()

    # Phase 1: lightweight stock quote cache only (cheap network-only fetches, no pipeline)
    phase1: dict[str, Callable[[], Any]] = {
        "market_overview": get_market_overview,
    }
    for symbol in ["NVDA", "AAPL", "MSFT", "SPY"]:
        phase1[f"stock_{symbol}"] = lambda symbol=symbol: get_stock(symbol)

    # Phase 2: heavier endpoints, submitted after phase 1 completes with a delay
    # NOTE: alpha_top, theme, and regime are intentionally NOT warmed here.
    # They self-warm on first access via _fast_cached_response.
    phase2: dict[str, Callable[[], Any]] = {
        "sector_rotation": get_sector_rotation,
    }

    scheduled: list[str] = []

    def _submit_batch(batch: list[tuple[str, Callable[[], Any]]]) -> None:
        for name, task in batch:
            scheduled.append(name)

            def run(name: str = name, task: Callable[[], Any] = task) -> None:
                try:
                    task()
                    logger.info("warmup task complete name=%s", name)
                except Exception as exc:
                    logger.warning("warmup task failed name=%s error=%s", name, exc)

            BACKGROUND_EXECUTOR.submit(run)

    # Submit phase 1 in batches of 2 with 0.5s gap
    phase1_items = list(phase1.items())
    for i in range(0, len(phase1_items), 2):
        _submit_batch(phase1_items[i:i + 2])
        if i + 2 < len(phase1_items):
            time.sleep(0.5)

    # Submit phase 2 after a 2-second delay to let phase 1 settle
    def _delayed_phase2() -> None:
        time.sleep(2.0)
        _submit_batch(list(phase2.items()))

    BACKGROUND_EXECUTOR.submit(_delayed_phase2)

    return {
        "status": "scheduled",
        "tasks": sorted(scheduled + list(phase2.keys())),
        "duration_seconds": round(time.perf_counter() - started, 3),
    }


@app.get("/search")
def search_stocks(q: str = Query(..., min_length=1)) -> list[dict]:
    symbol = q.strip().upper()
    stock = _guard(lambda: central_stock_enrichment(symbol))
    quote = stock.get("quote") or {}
    return [{
        "symbol": stock.get("ticker", symbol),
        "name": stock.get("company_name", symbol),
        "exchange": "US",
        "type": "Equity",
        "price": quote.get("price"),
        "change_percent": quote.get("change_percent"),
        "quote_status": quote.get("status") or stock.get("quote_status"),
    }]
