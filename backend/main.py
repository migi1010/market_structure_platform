from __future__ import annotations

import logging
import math
import time
from concurrent.futures import TimeoutError, ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from alpha_engine.scoring import bounded_score, confidence_label
from backtesting import run_top_alpha_backtest
from logging_config import configure_logging
from middleware import RateLimitMiddleware, RequestLoggingMiddleware, TimeoutMiddleware
from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, debug_provider, get_cached_value, get_history, get_quote, initialize_cache, safe_float, set_cached_value
from quant_engine.qlib_engine import run_alpha_ranking
from quant_engine.regime_engine import detect_market_regime
from quant_engine.sector_rotation_engine import analyze_sector_rotation
from quant_engine.stock_service import central_stock_enrichment, fallback_stock_payload
from qlib_engine.pipeline import SP500_UNIVERSE, UNIVERSE_PRESETS
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
    if ":market_overview" in lowered_key and isinstance(result, list):
        return any(_finite_positive(item.get("price")) for item in result if isinstance(item, dict))
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
        logger.info("endpoint cache hit key=%s", cache_key)
        return cached
    stale = get_cached_value(cache_key, allow_expired=True)
    if stale is not None:
        logger.info("endpoint stale cache hit key=%s", cache_key)
        _schedule_cache_refresh(cache_key, ttl_seconds, task)
        return _with_lifecycle(cache_key, stale, "recovery")
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
        return _with_lifecycle(cache_key, fallback(), "degraded")
    except Exception as exc:
        logger.warning("endpoint failed key=%s; serving fallback error=%s", cache_key, exc)
        return _with_lifecycle(cache_key, fallback(), "degraded")


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
    sectors = [
        ("Technology", "XLK"), ("Energy", "XLE"), ("Healthcare", "XLV"), ("Financials", "XLF"),
        ("Industrials", "XLI"), ("Utilities", "XLU"), ("Consumer Discretionary", "XLY"),
        ("Consumer Staples", "XLP"), ("Materials", "XLB"), ("Real Estate", "XLRE"),
        ("Communication Services", "XLC"), ("Defense", "ITA"), ("Infrastructure", "PAVE"),
        ("Commodities", "DBC"), ("Nuclear", "URA"), ("Shipping", "IYT"), ("Copper", "COPX"),
        ("Aerospace", "ITA"),
    ]
    rows: list[dict] = []
    for index, (sector, etf) in enumerate(sectors):
        try:
            history = get_history(etf, "3mo")
            close = history["Close"].astype(float) if history is not None and not history.empty and "Close" in history else None
            volume = history["Volume"].astype(float) if history is not None and not history.empty and "Volume" in history else None
            ret = float(close.iloc[-1] / close.iloc[0] - 1.0) if close is not None and len(close) > 1 else 0.0
            ret_1m = float(close.iloc[-1] / close.iloc[-22] - 1.0) if close is not None and len(close) > 22 else ret / 2.0
            rel_volume = float(volume.iloc[-1] / max(volume.tail(45).mean(), 1.0)) if volume is not None and len(volume) > 10 else 1.0
            score = bounded_score(48.0 + ret * 165.0 + (rel_volume - 1.0) * 18.0)
            flow = bounded_score(48.0 + ret_1m * 180.0 + (rel_volume - 1.0) * 20.0)
            confidence = bounded_score(35.0 + (65.0 if close is not None and len(close) > 44 else 15.0))
        except Exception:
            score = bounded_score(40.0 + index * 2.3)
            flow = bounded_score(38.0 + index * 1.7)
            confidence = 25.0
        rows.append({
            "sector": sector,
            "score": score,
            "relative_strength": score,
            "flow": flow,
            "rotation_state": "Partial Data" if confidence < 55 else "Accumulation" if score >= 65 else "Weakening" if score < 42 else "Neutral",
            "confidence_score": confidence,
            "confidence_label": confidence_label(confidence),
            "companies": [],
            "fallback": True,
            "message": "Using cached ETF rotation proxies while live sector engine refreshes.",
        })
    return sorted(rows, key=lambda row: row["score"], reverse=True)


def _fallback_theme_top() -> dict:
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
        try:
            history = get_history(etf, "3mo")
            close = history["Close"].astype(float) if history is not None and not history.empty and "Close" in history else None
            volume = history["Volume"].astype(float) if history is not None and not history.empty and "Volume" in history else None
            ret = float(close.iloc[-1] / close.iloc[0] - 1.0) if close is not None and len(close) > 1 else 0.0
            acceleration = float(close.iloc[-1] / close.iloc[-22] - 1.0) - ret / 3.0 if close is not None and len(close) > 22 else 0.0
            rel_volume = float(volume.iloc[-1] / max(volume.tail(45).mean(), 1.0)) if volume is not None and len(volume) > 10 else 1.0
            adjustment = theme_specificity.get(theme, 0.0)
            strength = bounded_score(46.0 + ret * 72.0 + acceleration * 35.0 + (rel_volume - 1.0) * 10.0 + adjustment)
            flow = bounded_score(44.0 + ret * 30.0 + acceleration * 72.0 + (rel_volume - 1.0) * 18.0 + adjustment * 0.45)
            emerging = bounded_score((strength * 0.56 + flow * 0.44) + max(0.0, acceleration) * 36.0 - max(0.0, ret - 0.34) * 18.0)
            confidence = bounded_score(32.0 + (62.0 if close is not None and len(close) > 44 else 15.0))
        except Exception:
            strength = bounded_score(41.0 + index * 2.4)
            flow = bounded_score(39.0 + index * 1.9)
            emerging = bounded_score(38.0 + index * 2.1)
            confidence = 24.0
        overheating = bounded_score(max(18.0, strength - 16.0) + max(0.0, flow - 70.0) * 0.40)
        strength = bounded_score(strength - max(0.0, overheating - 70.0) * 0.12)
        rows.append({
            "theme": theme,
            "category": "Universal Theme",
            "description": "Live theme signal is calibrating.",
            "theme_strength_score": strength,
            "theme_capital_flow_score": flow,
            "emerging_score": emerging,
            "overheating_score": overheating,
            "status": "Leadership" if strength >= 78 and flow >= 65 else "Emerging" if emerging >= 65 else "Accumulating" if strength >= 58 else "Cooling" if strength < 42 else "Watchlist",
            "confidence_score": confidence,
            "confidence_label": confidence_label(confidence),
            "data_completeness": confidence,
            "relative_momentum": 0.0,
            "etf_relative_strength": 0.0,
            "volume_expansion": 1.0,
            "institutional_accumulation": flow,
            "earnings_acceleration": 0.0,
            "revenue_acceleration": 0.0,
            "capex_trend": strength,
            "smart_money_accumulation": flow,
            "narrative_strength": 45.0,
            "narrative_acceleration": 45.0,
            "narrative_saturation": 35.0,
            "narrative_bubble_risk": 30.0,
            "breadth_participation": confidence,
            "leadership_concentration": 0.0,
            "relative_strength_vs_spy": 0.0,
            "options_activity": flow,
            "supply_chain_acceleration": emerging,
            "macro_alignment": strength,
            "leaders": [],
            "etfs": [],
            "macro_tags": [],
            "explainability": ["Theme engine is using ETF and liquidity proxies while full supply-chain scoring refreshes."],
            "risks": ["Confidence is reduced until full constituent, narrative, and macro data are refreshed."],
            "fallback": True,
        })
    rows = sorted(rows, key=lambda row: row["theme_strength_score"], reverse=True)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cross_asset_regime": {
            "risk_on_off": "Calibrating",
            "risk_on_score": 50.0,
            "liquidity_regime": "Calibrating",
            "liquidity_score": 50.0,
            "volatility_regime": "Calibrating",
            "volatility_score": 50.0,
            "inflation_regime": "Calibrating",
            "inflation_score": 50.0,
            "AI_capex_regime": "Calibrating",
            "AI_capex_score": 50.0,
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
        rows.append({
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
        })
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
        "summary": "Alpha pipeline warming up. Static institutional fallback shown. Scores update when live engine completes.",
        "fallback": True,
    }


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
    normalized = universe.strip().lower()
    return _guard(lambda: _fast_cached_response(_schema_cache_key("alpha_v4", normalized), settings.alpha_ranking_ttl_seconds, lambda: run_alpha_ranking(normalized), lambda: _fallback_alpha(normalized)))


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
    return _guard(lambda: _fast_cached_response(_schema_cache_key("market_regime"), settings.market_regime_ttl_seconds, detect_market_regime, lambda: {"name": "Calibrating", "confidence": 38.0, "confidence_label": "Low Confidence", "fallback": True}))


@app.get("/market/overview")
def get_market_overview() -> list[dict]:
    symbols = ["SPY", "QQQ", "SMH", "DIA", "IWM", "XLK", "XLF", "XLE", "XLV", "NVDA", "AAPL", "MSFT"]

    def finite_or_none(value: Any) -> float | None:
        try:
            parsed = float(value)
            return parsed if math.isfinite(parsed) else None
        except (TypeError, ValueError):
            return None

    def build() -> list[dict]:
        tape = []
        for symbol in symbols:
            enriched = central_stock_enrichment(symbol)
            quote = enriched.get("quote") or {}
            price = finite_or_none(quote.get("price"))
            change = finite_or_none(quote.get("change"))
            change_percent = finite_or_none(quote.get("change_percent"))
            tape.append({
                "ticker": symbol,
                "price": round(price, 2) if price is not None else None,
                "change": round(change, 2) if change is not None else None,
                "change_percent": round(change_percent, 2) if change_percent is not None else None,
                "quote_status": quote.get("status") or enriched.get("quote_status") or "unavailable",
            })
        return tape

    return _guard(lambda: _cached_response(_schema_cache_key("market_overview"), settings.market_overview_ttl_seconds, build))


@app.get("/sector/rotation")
def get_sector_rotation() -> list[dict]:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("sector_rotation"), settings.sector_rotation_ttl_seconds, analyze_sector_rotation, _fallback_sector_rotation))


@app.get("/theme/top")
def get_theme_top() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v3", "top"), settings.theme_ttl_seconds, get_top_themes, _fallback_theme_top))


@app.get("/theme/emerging")
def get_theme_emerging() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v3", "emerging"), settings.theme_ttl_seconds, get_emerging_themes, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "emerging_themes": _fallback_theme_top()["themes"][:6], "summary": "Theme engine calibrating. No active emerging signal confirmed yet.", "fallback": True}))


@app.get("/theme/rotation")
def get_theme_rotation_endpoint() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v3", "rotation"), settings.theme_ttl_seconds, get_theme_rotation, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rotation_map": _fallback_theme_top()["themes"], "strengthening": [], "weakening": [], "overheated_themes": [], "undervalued_themes": [], "summary": "Theme rotation matrix is calibrating.", "fallback": True}))


@app.get("/theme/capital-flow")
def get_theme_capital_flow_endpoint() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v3", "capital_flow"), settings.theme_ttl_seconds, get_theme_capital_flow, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "capital_flow": _fallback_theme_top()["themes"][:8], "summary": "Capital flow temporarily unavailable. Using latest cached institutional intelligence.", "fallback": True}))


@app.get("/theme/supply-chain")
def get_theme_supply_chain_endpoint(theme: str | None = None) -> dict:
    key = _schema_cache_key("theme_v3", "supply_chain", theme or "all")
    return _guard(lambda: _fast_cached_response(key, settings.theme_ttl_seconds, lambda: get_theme_supply_chain(theme), lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "themes": [], "summary": "Supply chain map calibrating.", "fallback": True}))


@app.get("/theme/narrative")
def get_theme_narrative_endpoint() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v3", "narrative"), settings.theme_ttl_seconds, analyze_all_narratives, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "narratives": [], "summary": "Narrative engine calibrating.", "fallback": True}))


@app.get("/theme/{theme_id:path}/stocks")
def get_theme_stocks_endpoint(theme_id: str) -> dict:
    normalized = theme_id.strip().lower()
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v3", "stocks", normalized), settings.theme_ttl_seconds, lambda: get_theme_stocks(theme_id), lambda: get_theme_stocks_static(theme_id)))


@app.get("/theme/{theme_id:path}/detail")
def get_theme_detail_endpoint(theme_id: str) -> dict:
    normalized = theme_id.strip().lower()
    return _guard(lambda: _fast_cached_response(_schema_cache_key("theme_v3", "detail", normalized), settings.theme_ttl_seconds, lambda: get_theme_detail(theme_id), lambda: get_theme_detail_static(theme_id)))


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
