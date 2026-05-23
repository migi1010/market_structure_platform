from __future__ import annotations

import logging
import time
from concurrent.futures import TimeoutError, ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backtesting import run_top_alpha_backtest
from logging_config import configure_logging
from middleware import RateLimitMiddleware, RequestLoggingMiddleware, TimeoutMiddleware
from quant_engine.bubble_engine import analyze_bubble
from quant_engine.data_pipeline import get_cached_value, get_history, get_quote, initialize_cache, safe_float, set_cached_value
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


def _cached_response(cache_key: str, ttl_seconds: int, task: Callable[[], Any]) -> Any:
    cached = get_cached_value(cache_key)
    if cached is not None:
        logger.info("endpoint cache hit key=%s", cache_key)
        return cached
    started = time.perf_counter()
    try:
        result = task()
        set_cached_value(cache_key, result, ttl_seconds, "json")
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
            set_cached_value(cache_key, result, ttl_seconds, "json")
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
            set_cached_value(cache_key, result, ttl_seconds, "json")
            logger.info("deferred cache fill complete key=%s", cache_key)
        except Exception as exc:
            logger.warning("deferred cache fill failed key=%s error=%s", cache_key, exc)

    future.add_done_callback(store_result_when_ready)
    started = time.perf_counter()
    try:
        result = future.result(timeout=CACHE_MISS_WAIT_SECONDS)
        set_cached_value(cache_key, result, ttl_seconds, "json")
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
        "Technology", "Energy", "Healthcare", "Financials", "Industrials", "Utilities",
        "Consumer Discretionary", "Consumer Staples", "Materials", "Real Estate", "Communication Services",
    ]
    return [
        {
            "sector": sector,
            "score": 50.0,
            "relative_strength": 50.0,
            "flow": 50.0,
            "rotation_state": "Calibrating",
            "companies": [],
            "fallback": True,
            "message": "Using latest cached institutional intelligence while live sector data warms up.",
        }
        for sector in sectors
    ]


def _fallback_theme_top() -> dict:
    themes = [
        "AI Infrastructure", "Semiconductor", "Electric Grid", "Nuclear Energy", "Energy",
        "Defense", "Healthcare", "Financials", "Shipping", "Commodities",
    ]
    rows = [
        {
            "theme": theme,
            "category": "Universal Theme",
            "description": "Live theme signal is calibrating.",
            "theme_strength_score": 50.0,
            "theme_capital_flow_score": 50.0,
            "emerging_score": 45.0,
            "overheating_score": 35.0,
            "relative_momentum": 0.0,
            "etf_relative_strength": 0.0,
            "volume_expansion": 1.0,
            "institutional_accumulation": 50.0,
            "earnings_acceleration": 0.0,
            "revenue_acceleration": 0.0,
            "capex_trend": 50.0,
            "smart_money_accumulation": 50.0,
            "narrative_strength": 45.0,
            "narrative_acceleration": 45.0,
            "narrative_saturation": 35.0,
            "narrative_bubble_risk": 30.0,
            "breadth_participation": 50.0,
            "leadership_concentration": 0.0,
            "relative_strength_vs_spy": 0.0,
            "options_activity": 50.0,
            "supply_chain_acceleration": 50.0,
            "macro_alignment": 50.0,
            "leaders": [],
            "etfs": [],
            "macro_tags": [],
            "explainability": ["Theme engine calibrating; showing neutral institutional fallback."],
            "status": "Calibrating",
            "fallback": True,
        }
        for theme in themes
    ]
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
    rows = [
        {
            "ticker": symbol,
            "company_name": symbol,
            "sector": "Calibrating",
            "alpha_score": 50.0,
            "quality": 50.0,
            "growth": 50.0,
            "smart_money": 50.0,
            "valuation": 50.0,
            "earnings_quality": 50.0,
            "market_structure": 50.0,
            "bubble_risk": 50.0,
            "sector_alignment": 50.0,
            "theme_alignment": 50.0,
            "theme_strength": 50.0,
            "theme_capital_flow": 50.0,
            "theme_explanation": ["Alpha engine delayed; showing neutral fallback until cached intelligence is ready."],
            "suggested_action": "Hold",
            "factor_importance": {"quality": 0.2, "growth": 0.2, "smart_money": 0.2, "valuation": 0.15, "earnings_quality": 0.15, "market_structure": 0.1},
        }
        for symbol in symbols
    ]
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
    return _guard(lambda: _fast_cached_response(_cache_key("stock_v2", symbol), settings.quote_ttl_seconds, lambda: analyze_stock(symbol), lambda: fallback_stock_payload(symbol)))


@app.get("/alpha/top")
def get_alpha_top(universe: str = Query("sp500")) -> dict:
    normalized = universe.strip().lower()
    return _guard(lambda: _fast_cached_response(_cache_key("alpha_top", normalized), settings.alpha_ranking_ttl_seconds, lambda: run_alpha_ranking(normalized), lambda: _fallback_alpha(normalized)))


@app.get("/backtest/top-alpha")
def backtest_top_alpha(
    universe: str = Query("sp500", pattern="^(sp500|nasdaq100)$"),
    years: int = Query(3, ge=1, le=5),
) -> dict:
    return _guard(lambda: run_top_alpha_backtest(universe=universe, years=years))


@app.get("/bubble/{ticker}")
def get_bubble(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: _cached_response(_cache_key("bubble", symbol), settings.fundamentals_ttl_seconds, lambda: analyze_bubble(symbol)))


@app.get("/market/regime")
def get_market_regime() -> dict:
    return _guard(lambda: _fast_cached_response(_cache_key("market_regime"), settings.market_regime_ttl_seconds, detect_market_regime, lambda: {"name": "Calibrating", "confidence": 50.0, "fallback": True}))


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

    return _guard(lambda: _cached_response(_cache_key("market_overview"), settings.market_overview_ttl_seconds, build))


@app.get("/sector/rotation")
def get_sector_rotation() -> list[dict]:
    return _guard(lambda: _fast_cached_response(_cache_key("sector_rotation"), settings.sector_rotation_ttl_seconds, analyze_sector_rotation, _fallback_sector_rotation))


@app.get("/theme/top")
def get_theme_top() -> dict:
    return _guard(lambda: _fast_cached_response(_cache_key("theme_top"), settings.theme_ttl_seconds, get_top_themes, _fallback_theme_top))


@app.get("/theme/emerging")
def get_theme_emerging() -> dict:
    return _guard(lambda: _fast_cached_response(_cache_key("theme_emerging"), settings.theme_ttl_seconds, get_emerging_themes, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "emerging_themes": _fallback_theme_top()["themes"][:6], "summary": "Theme engine calibrating. No active emerging signal confirmed yet.", "fallback": True}))


@app.get("/theme/rotation")
def get_theme_rotation_endpoint() -> dict:
    return _guard(lambda: _fast_cached_response(_cache_key("theme_rotation"), settings.theme_ttl_seconds, get_theme_rotation, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rotation_map": _fallback_theme_top()["themes"], "strengthening": [], "weakening": [], "overheated_themes": [], "undervalued_themes": [], "summary": "Theme rotation matrix is calibrating.", "fallback": True}))


@app.get("/theme/capital-flow")
def get_theme_capital_flow_endpoint() -> dict:
    return _guard(lambda: _fast_cached_response(_cache_key("theme_capital_flow"), settings.theme_ttl_seconds, get_theme_capital_flow, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "capital_flow": _fallback_theme_top()["themes"][:8], "summary": "Capital flow temporarily unavailable. Using latest cached institutional intelligence.", "fallback": True}))


@app.get("/theme/supply-chain")
def get_theme_supply_chain_endpoint(theme: str | None = None) -> dict:
    key = _cache_key("theme_supply_chain", theme or "all")
    return _guard(lambda: _fast_cached_response(key, settings.theme_ttl_seconds, lambda: get_theme_supply_chain(theme), lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "themes": [], "summary": "Supply chain map calibrating.", "fallback": True}))


@app.get("/theme/narrative")
def get_theme_narrative_endpoint() -> dict:
    return _guard(lambda: _fast_cached_response(_cache_key("theme_narrative"), settings.theme_ttl_seconds, analyze_all_narratives, lambda: {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "narratives": [], "summary": "Narrative engine calibrating.", "fallback": True}))


@app.get("/smart-money/{ticker}")
def get_smart_money(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: _cached_response(_cache_key("smart_money", symbol), settings.quote_ttl_seconds, lambda: analyze_smart_money(symbol)))


@app.get("/earnings-quality/{ticker}")
def get_earnings_quality(ticker: str) -> dict:
    symbol = ticker.strip().upper()
    return _guard(lambda: _cached_response(_cache_key("earnings_quality", symbol), settings.fundamentals_ttl_seconds, lambda: analyze_earnings_quality(symbol)))


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
