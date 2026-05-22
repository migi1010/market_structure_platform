from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backtesting import run_top_alpha_backtest
from logging_config import configure_logging
from middleware import RateLimitMiddleware, RequestLoggingMiddleware, TimeoutMiddleware
from quant_engine.bubble_engine import analyze_bubble
from quant_engine.data_pipeline import get_history, get_quote, initialize_cache, safe_float
from quant_engine.earnings_quality_engine import analyze_earnings_quality
from quant_engine.qlib_engine import run_alpha_ranking
from quant_engine.regime_engine import detect_market_regime
from quant_engine.sector_rotation_engine import analyze_sector_rotation
from quant_engine.smart_money_engine import analyze_smart_money
from quant_engine.stock_service import analyze_stock
from settings import get_settings

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
    return _guard(lambda: analyze_stock(ticker))


@app.get("/alpha/top")
def get_alpha_top(universe: str = Query("sp500", pattern="^(sp500|nasdaq100)$")) -> dict:
    return _guard(lambda: run_alpha_ranking(universe))


@app.get("/backtest/top-alpha")
def backtest_top_alpha(
    universe: str = Query("sp500", pattern="^(sp500|nasdaq100)$"),
    years: int = Query(3, ge=1, le=5),
) -> dict:
    return _guard(lambda: run_top_alpha_backtest(universe=universe, years=years))


@app.get("/bubble/{ticker}")
def get_bubble(ticker: str) -> dict:
    return _guard(lambda: analyze_bubble(ticker))


@app.get("/market/regime")
def get_market_regime() -> dict:
    return _guard(detect_market_regime)


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

    return _guard(build)


@app.get("/sector/rotation")
def get_sector_rotation() -> list[dict]:
    return _guard(analyze_sector_rotation)


@app.get("/smart-money/{ticker}")
def get_smart_money(ticker: str) -> dict:
    return _guard(lambda: analyze_smart_money(ticker))


@app.get("/earnings-quality/{ticker}")
def get_earnings_quality(ticker: str) -> dict:
    return _guard(lambda: analyze_earnings_quality(ticker))


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
