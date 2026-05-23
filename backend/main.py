from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from quant_engine.stock_service import analyze_stock
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
    return _guard(lambda: _cached_response(_cache_key("stock", symbol), settings.quote_ttl_seconds, lambda: analyze_stock(symbol)))


@app.get("/alpha/top")
def get_alpha_top(universe: str = Query("sp500", pattern="^(sp500|nasdaq100)$")) -> dict:
    return _guard(lambda: _cached_response(_cache_key("alpha_top", universe), settings.alpha_ranking_ttl_seconds, lambda: run_alpha_ranking(universe)))


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
    return _guard(lambda: _cached_response(_cache_key("market_regime"), settings.market_regime_ttl_seconds, detect_market_regime))


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
    return _guard(lambda: _cached_response(_cache_key("sector_rotation"), settings.sector_rotation_ttl_seconds, analyze_sector_rotation))


@app.get("/theme/top")
def get_theme_top() -> dict:
    return _guard(lambda: _cached_response(_cache_key("theme_top"), settings.theme_ttl_seconds, get_top_themes))


@app.get("/theme/emerging")
def get_theme_emerging() -> dict:
    return _guard(lambda: _cached_response(_cache_key("theme_emerging"), settings.theme_ttl_seconds, get_emerging_themes))


@app.get("/theme/rotation")
def get_theme_rotation_endpoint() -> dict:
    return _guard(lambda: _cached_response(_cache_key("theme_rotation"), settings.theme_ttl_seconds, get_theme_rotation))


@app.get("/theme/capital-flow")
def get_theme_capital_flow_endpoint() -> dict:
    return _guard(lambda: _cached_response(_cache_key("theme_capital_flow"), settings.theme_ttl_seconds, get_theme_capital_flow))


@app.get("/theme/supply-chain")
def get_theme_supply_chain_endpoint(theme: str | None = None) -> dict:
    key = _cache_key("theme_supply_chain", theme or "all")
    return _guard(lambda: _cached_response(key, settings.theme_ttl_seconds, lambda: get_theme_supply_chain(theme)))


@app.get("/theme/narrative")
def get_theme_narrative_endpoint() -> dict:
    return _guard(lambda: _cached_response(_cache_key("theme_narrative"), settings.theme_ttl_seconds, analyze_all_narratives))


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
    tasks: dict[str, Callable[[], Any]] = {
        "sector_rotation": get_sector_rotation,
        "market_regime": get_market_regime,
        "theme_top": get_theme_top,
        "theme_emerging": get_theme_emerging,
    }
    for symbol in ["NVDA", "AAPL", "MSFT", "SPY", "QQQ", "SMH"]:
        tasks[f"stock_{symbol}"] = lambda symbol=symbol: get_stock(symbol)

    warmed: list[str] = []
    failed: dict[str, str] = {}
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {executor.submit(task): name for name, task in tasks.items()}
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                future.result()
                warmed.append(name)
            except Exception as exc:
                logger.warning("warmup failed task=%s error=%s", name, exc)
                failed[name] = str(exc)

    return {
        "status": "ok",
        "warmed": sorted(warmed),
        "failed": failed,
        "duration_seconds": round(time.perf_counter() - started, 2),
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
