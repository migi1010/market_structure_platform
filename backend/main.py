from __future__ import annotations

import logging
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
from quant_engine.bubble_engine import analyze_bubble
from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, debug_provider, get_cached_value, get_history, get_quote, initialize_cache, safe_float, set_cached_value
from quant_engine.earnings_quality_engine import analyze_earnings_quality
from quant_engine.qlib_engine import run_alpha_ranking
from quant_engine.regime_engine import detect_market_regime
from quant_engine.sector_rotation_engine import analyze_sector_rotation
from quant_engine.smart_money_engine import analyze_smart_money
from quant_engine.stock_service import analyze_stock, fallback_stock_payload
from settings import get_settings
from theme_engine import (
    analyze_all_narratives,
    get_emerging_themes,
    get_theme_capital_flow,
    get_theme_rotation,
    get_theme_supply_chain,
    get_top_themes,
)

configure_logging()
logger = logging.getLogger("miji.api")
settings = get_settings()
BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=4)
CACHE_MISS_WAIT_SECONDS = 4.0


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
        return parsed > 0
    except (TypeError, ValueError):
        return False


def _cacheable_endpoint_result(cache_key: str, result: Any) -> bool:
    if not isinstance(result, (dict, list)):
        return True
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
        if _cacheable_endpoint_result(cache_key, result):
            set_cached_value(cache_key, result, ttl_seconds, "json")
        else:
            logger.warning("skipping endpoint cache write for low-quality result key=%s", cache_key)
        logger.info("endpoint cache miss key=%s duration=%.2fs", cache_key, time.perf_counter() - started)
        return result
    except Exception:
        stale = get_cached_value(cache_key, allow_expired=True)
        if stale is not None:
            logger.warning("serving stale endpoint cache key=%s", cache_key)
            return stale
        raise


def _schedule_cache_refresh(cache_key: str, ttl_seconds: int, task: Callable[[], Any]) -> None:
    def refresh() -> None:
        try:
            result = task()
            if _cacheable_endpoint_result(cache_key, result):
                set_cached_value(cache_key, result, ttl_seconds, "json")
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
        return stale
    future = BACKGROUND_EXECUTOR.submit(task)

    def store_result_when_ready(completed: Any) -> None:
        try:
            result = completed.result()
            if _cacheable_endpoint_result(cache_key, result):
                set_cached_value(cache_key, result, ttl_seconds, "json")
            else:
                logger.warning("skipping deferred cache write for low-quality result key=%s", cache_key)
            logger.info("deferred cache fill complete key=%s", cache_key)
        except Exception as exc:
            logger.warning("deferred cache fill failed key=%s error=%s", cache_key, exc)

    future.add_done_callback(store_result_when_ready)
    started = time.perf_counter()
    try:
        result = future.result(timeout=CACHE_MISS_WAIT_SECONDS)
        if _cacheable_endpoint_result(cache_key, result):
            set_cached_value(cache_key, result, ttl_seconds, "json")
        else:
            logger.warning("skipping endpoint cache write for low-quality result key=%s", cache_key)
        logger.info("endpoint cache miss key=%s duration=%.2fs", cache_key, time.perf_counter() - started)
        return result
    except TimeoutError:
        logger.warning("endpoint timed out key=%s; serving fallback", cache_key)
        return fallback()
    except Exception as exc:
        logger.warning("endpoint failed key=%s; serving fallback error=%s", cache_key, exc)
        return fallback()


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
    symbols = ["NVDA", "MSFT", "AAPL", "AMZN", "META", "AVGO", "LLY", "JPM", "XOM", "V"]
    rows = []
    for index, symbol in enumerate(symbols):
        quote: dict[str, Any] = {}
        try:
            quote = get_quote(symbol)
            history = get_history(symbol, "3mo")
            close = history["Close"].astype(float) if history is not None and not history.empty and "Close" in history else None
            ret_1m = float(close.iloc[-1] / close.iloc[-22] - 1.0) if close is not None and len(close) > 22 else 0.0
            ret_3m = float(close.iloc[-1] / close.iloc[0] - 1.0) if close is not None and len(close) > 1 else 0.0
            volume = history["Volume"].astype(float) if history is not None and not history.empty and "Volume" in history else None
            rel_volume = float(volume.iloc[-1] / max(volume.tail(45).mean(), 1.0)) if volume is not None and len(volume) > 10 else 1.0
            market_cap = safe_float(quote.get("marketCap"))
            momentum = bounded_score(48.0 + ret_3m * 150.0 + ret_1m * 80.0)
            smart_money = bounded_score(45.0 + (rel_volume - 1.0) * 24.0 + ret_1m * 75.0)
            quality = bounded_score(44.0 + safe_float(quote.get("grossMargins")) * 55.0 + safe_float(quote.get("profitMargins")) * 85.0)
            valuation = bounded_score(78.0 - max(0.0, safe_float(quote.get("trailingPE") or quote.get("forwardPE")) - 22.0) * 0.7 - max(0.0, safe_float(quote.get("priceToSalesTrailing12Months")) - 5.0) * 2.0)
            confidence = bounded_score((65.0 if close is not None and len(close) > 44 else 28.0) + min(market_cap, 200_000_000_000.0) / 200_000_000_000.0 * 20.0)
            alpha_score = bounded_score(momentum * 0.32 + quality * 0.24 + smart_money * 0.22 + valuation * 0.14 + confidence * 0.08 - (100.0 - confidence) * 0.08)
        except Exception:
            momentum = bounded_score(42.0 + index * 2.7)
            smart_money = bounded_score(39.0 + index * 1.9)
            quality = bounded_score(41.0 + index * 2.1)
            valuation = bounded_score(46.0 - index * 1.2)
            confidence = 22.0
            alpha_score = bounded_score(momentum * 0.30 + quality * 0.28 + smart_money * 0.22 + valuation * 0.12 - 6.0)
        row = {
            "ticker": symbol,
            "company_name": str(quote.get("longName") or quote.get("shortName") or symbol),
            "sector": str(quote.get("sector") or "Partial Data"),
            "alpha_score": alpha_score,
            "quality": quality,
            "growth": momentum,
            "smart_money": smart_money,
            "valuation": valuation,
            "earnings_quality": quality,
            "market_structure": momentum,
            "bubble_risk": bounded_score(100.0 - valuation),
            "sector_alignment": momentum,
            "theme_alignment": bounded_score((momentum + smart_money) / 2.0),
            "theme_strength": momentum,
            "theme_capital_flow": smart_money,
            "confidence_score": confidence,
            "confidence_label": confidence_label(confidence),
            "theme_explanation": ["Alpha engine delayed; showing neutral fallback until cached intelligence is ready."],
            "suggested_action": "Hold",
            "factor_importance": {"quality": 0.2, "growth": 0.2, "smart_money": 0.2, "valuation": 0.15, "earnings_quality": 0.15, "market_structure": 0.1},
            "bullish_factors": ["Partial price and liquidity factors are available."] if confidence >= 45 else [],
            "risk_factors": ["Live alpha engine delayed; confidence reduced until background cache completes."],
        }
        rows.append(row)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "universe": universe.upper(),
        "qlib_engine": {"available": False, "mode": "fallback", "provider": "Miji Quant", "factor_set": "Cached Alpha Fallback"},
        "market_regime": {"name": "Calibrating", "confidence": 50.0},
        "factor_importance": rows[0]["factor_importance"],
        "top_alpha": rows,
        "recommendations": rows[:5],
        "summary": "Live engine delayed. Showing cached institutional intelligence fallback while Render warms up.",
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
    return _guard(lambda: _fast_cached_response(_schema_cache_key("stock", symbol), settings.quote_ttl_seconds, lambda: analyze_stock(symbol), lambda: fallback_stock_payload(symbol)))


@app.get("/debug/provider/{ticker}")
def get_provider_debug(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: debug_provider(symbol))


@app.get("/alpha/top")
def get_alpha_top(universe: str = Query("sp500")) -> dict:
    normalized = universe.strip().lower()
    return _guard(lambda: _fast_cached_response(_schema_cache_key("alpha_v3", normalized), settings.alpha_ranking_ttl_seconds, lambda: run_alpha_ranking(normalized), lambda: _fallback_alpha(normalized)))


@app.get("/backtest/top-alpha")
def backtest_top_alpha(
    universe: str = Query("sp500", pattern="^(sp500|nasdaq100)$"),
    years: int = Query(3, ge=1, le=5),
) -> dict:
    return _guard(lambda: run_top_alpha_backtest(universe=universe, years=years))


@app.get("/bubble/{ticker}")
def get_bubble(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: _cached_response(_schema_cache_key("bubble", symbol), settings.fundamentals_ttl_seconds, lambda: analyze_bubble(symbol)))


@app.get("/market/regime")
def get_market_regime() -> dict:
    return _guard(lambda: _fast_cached_response(_schema_cache_key("market_regime"), settings.market_regime_ttl_seconds, detect_market_regime, lambda: {"name": "Calibrating", "confidence": 38.0, "confidence_label": "Low Confidence", "fallback": True}))


@app.get("/market/overview")
def get_market_overview() -> list[dict]:
    symbols = ["SPY", "QQQ", "SMH", "DIA", "IWM", "XLK", "XLF", "XLE", "XLV", "NVDA", "AAPL", "MSFT"]

    def build() -> list[dict]:
        tape = []
        for symbol in symbols:
            quote = get_quote(symbol)
            price = safe_float(quote.get("currentPrice") or quote.get("regularMarketPrice"))
            change = safe_float(quote.get("regularMarketChange"))
            change_percent = safe_float(quote.get("regularMarketChangePercent"))
            if price == 0.0 or change_percent == 0.0:
                history = get_history(symbol, "5d")
                if history is not None and not history.empty and len(history) >= 2:
                    close = history["Close"].astype(float)
                    price = float(close.iloc[-1])
                    previous = float(close.iloc[-2])
                    change = price - previous
                    change_percent = (change / previous * 100.0) if previous > 0 else 0.0
            tape.append({
                "ticker": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
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


@app.get("/smart-money/{ticker}")
def get_smart_money(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: _cached_response(_schema_cache_key("smart_money", symbol), settings.quote_ttl_seconds, lambda: analyze_smart_money(symbol)))


@app.get("/earnings-quality/{ticker}")
def get_earnings_quality(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: _cached_response(_schema_cache_key("earnings_quality", symbol), settings.fundamentals_ttl_seconds, lambda: analyze_earnings_quality(symbol)))


@app.api_route("/warmup", methods=["GET", "POST"])
def warmup() -> dict:
    started = time.perf_counter()
    tasks: dict[str, Callable[[], Any]] = {
        "sector_rotation": get_sector_rotation,
        "market_regime": get_market_regime,
        "theme_top": get_theme_top,
        "theme_emerging": get_theme_emerging,
        "theme_rotation": get_theme_rotation_endpoint,
        "theme_capital_flow": get_theme_capital_flow_endpoint,
        "alpha_top": lambda: get_alpha_top("sp500"),
        "market_overview": get_market_overview,
    }
    for symbol in ["NVDA", "AAPL", "MSFT", "SPY", "QQQ", "SMH"]:
        tasks[f"stock_{symbol}"] = lambda symbol=symbol: get_stock(symbol)

    scheduled: list[str] = []
    for name, task in tasks.items():
        scheduled.append(name)

        def run(name: str = name, task: Callable[[], Any] = task) -> None:
            try:
                task()
                logger.info("warmup task complete name=%s", name)
            except Exception as exc:
                logger.warning("warmup task failed name=%s error=%s", name, exc)

        BACKGROUND_EXECUTOR.submit(run)

    return {
        "status": "scheduled",
        "tasks": sorted(scheduled),
        "duration_seconds": round(time.perf_counter() - started, 3),
    }


@app.get("/search")
def search_stocks(q: str = Query(..., min_length=1)) -> list[dict]:
    symbol = q.strip().upper()
    stock = _guard(lambda: analyze_stock(symbol))
    return [{
        "symbol": stock.get("ticker", symbol),
        "name": stock.get("company_name", symbol),
        "exchange": "US",
        "type": "Equity",
    }]
