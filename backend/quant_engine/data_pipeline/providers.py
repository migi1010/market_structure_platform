from __future__ import annotations

import logging
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Dict, List


import requests
import yfinance as yf

from settings import get_settings

logger = logging.getLogger("miji.providers")
PROVIDER_TIMEOUT_SECONDS = 8.0
PROVIDER_RETRY_COUNT = 2
# Phase 2.7 fix: 4 workers caused a thread-pool self-deadlock.
# fetch_yfinance_quote() makes 3 sequential blocking _run_with_timeout() calls
# (ticker.info, ticker.fast_info, ticker.history). central_stock_enrichment()
# also calls get_history() + get_statements() x3 — totalling up to 11 simultaneous
# PROVIDER_EXECUTOR submissions from a single /stock request.
# With max_workers=4, all 4 slots fill with blocking future.result() calls,
# leaving no workers available to run the submitted tasks -> deadlock -> timeout -> fallback.
# 6 workers breaks the deadlock (4 is the minimum to deadlock, 5 is the absolute minimum safe).
# The memory savings from Phase 2.6 come from vectorbt lazy-load + 1 gunicorn worker;
# thread count has negligible additional memory impact (~1-2MB per thread).
# Override via RENDER_PROVIDER_WORKERS env var.
PROVIDER_EXECUTOR = ThreadPoolExecutor(max_workers=int(os.getenv("RENDER_PROVIDER_WORKERS", "6")))



def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def finite_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        parsed = float(value)
        if math.isnan(parsed) or math.isinf(parsed):
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _run_with_timeout(task: Any, timeout_seconds: float = PROVIDER_TIMEOUT_SECONDS) -> Any:
    future = PROVIDER_EXECUTOR.submit(task)
    try:
        return future.result(timeout=timeout_seconds)
    except TimeoutError:
        # Cancel the pending future to release the worker slot as soon as the task
        # can be interrupted. Log at WARNING so Render logs show provider timing issues.
        future.cancel()
        logger.warning("provider task timed out after %.1fs (executor workers=%d)",
                       timeout_seconds, PROVIDER_EXECUTOR._max_workers)  # noqa: SLF001
        raise


def _quality_quote(quote: Dict[str, Any]) -> bool:
    price = finite_float(quote.get("currentPrice") or quote.get("regularMarketPrice"))
    previous = finite_float(quote.get("previousClose") or quote.get("regularMarketPreviousClose"))
    return price is not None and price > 0 and (previous is None or previous > 0)


def _quote_from_history_frame(history: Any) -> Dict[str, Any]:
    if history is None or getattr(history, "empty", True) or "Close" not in history:
        return {}
    close = history["Close"].dropna()
    if close.empty:
        return {}
    latest = finite_float(close.iloc[-1])
    previous = finite_float(close.iloc[-2]) if len(close) > 1 else latest
    if latest is None or latest <= 0:
        return {}
    change = latest - previous if previous is not None else None
    change_percent = (change / previous * 100.0) if previous and previous > 0 and change is not None else None
    return {
        "currentPrice": latest,
        "regularMarketPrice": latest,
        "previousClose": previous,
        "regularMarketPreviousClose": previous,
        "regularMarketChange": change,
        "regularMarketChangePercent": change_percent,
        "quoteSource": "yfinance_history",
    }


def _request_json(url: str, params: Dict[str, Any] | None = None) -> Any:
    settings = get_settings()
    last_error: Exception | None = None
    retry_count = min(settings.provider_retry_count, PROVIDER_RETRY_COUNT)
    for attempt in range(retry_count):
        try:
            response = requests.get(url, params=params, timeout=settings.provider_timeout_seconds)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            sleep_seconds = settings.provider_retry_backoff_seconds * (attempt + 1)
            logger.warning("provider request failed %s attempt=%s error=%s", url, attempt + 1, exc)
            time.sleep(sleep_seconds)
    if last_error is not None:
        raise last_error
    return None


def fetch_yfinance_quote(symbol: str) -> Dict[str, Any]:
    ticker = yf.Ticker(symbol)
    info: Dict[str, Any] = {}
    try:
        info.update(_run_with_timeout(lambda: ticker.info or {}) or {})
        if info:
            info.setdefault("quoteSource", "yfinance_info")
    except Exception as exc:
        logger.warning("yfinance info failed symbol=%s error=%s", symbol, exc)
    try:
        fast_info = _run_with_timeout(lambda: ticker.fast_info)
        if fast_info:
            def fast_value(*names: str) -> Any:
                for name in names:
                    value = getattr(fast_info, name, None)
                    if value is not None:
                        return value
                    getter = getattr(fast_info, "get", None)
                    if callable(getter):
                        value = getter(name)
                        if value is not None:
                            return value
                return None

            last_price = finite_float(fast_value("last_price", "lastPrice"))
            previous = finite_float(fast_value("previous_close", "previousClose"))
            if last_price is not None:
                info["currentPrice"] = last_price
                info["regularMarketPrice"] = last_price
            if previous is not None:
                info["previousClose"] = previous
                info["regularMarketPreviousClose"] = previous
            if last_price is not None and previous is not None and previous > 0:
                info["regularMarketChange"] = last_price - previous
                info["regularMarketChangePercent"] = (last_price - previous) / previous * 100.0
            market_cap = finite_float(fast_value("market_cap", "marketCap"))
            if market_cap is not None:
                info["marketCap"] = market_cap
            info.setdefault("currency", fast_value("currency"))
            info["quoteSource"] = "yfinance_fast_info"
    except Exception as exc:
        logger.warning("yfinance fast_info failed symbol=%s error=%s", symbol, exc)
    if not _quality_quote(info):
        try:
            history = _run_with_timeout(lambda: ticker.history(period="5d", interval="1d", auto_adjust=True))
            info.update(_quote_from_history_frame(history))
        except Exception as exc:
            logger.warning("yfinance quote history failed symbol=%s error=%s", symbol, exc)
    return info


def fetch_yfinance_download_quote(symbol: str) -> Dict[str, Any]:
    try:
        data = _run_with_timeout(
            lambda: yf.download(symbol, period="5d", interval="1d", progress=False, threads=False, auto_adjust=True),
            timeout_seconds=PROVIDER_TIMEOUT_SECONDS,
        )
        quote = _quote_from_history_frame(data)
        if quote:
            quote["quoteSource"] = "yfinance_download"
        return quote
    except Exception as exc:
        logger.warning("yfinance download quote failed symbol=%s error=%s", symbol, exc)
        return {}


def robust_quote_fetch(symbol: str, cached_last_good: Dict[str, Any] | None = None) -> Dict[str, Any]:
    normalized = symbol.strip().upper()
    merged: Dict[str, Any] = {"symbol": normalized}
    for fetcher in (
        fetch_yfinance_quote,
        fetch_yfinance_download_quote,
        fetch_fmp_quote,
        fetch_finnhub_quote,
        fetch_alpha_vantage_overview,
    ):
        try:
            data = {key: value for key, value in fetcher(normalized).items() if value not in (None, "")}
            merged.update(data)
            if _quality_quote(merged):
                merged["quoteStatus"] = "live"
                return merged
        except Exception as exc:
            logger.warning("robust quote fallback failed symbol=%s provider=%s error=%s", normalized, fetcher.__name__, exc)
    if isinstance(cached_last_good, dict) and _quality_quote(cached_last_good):
        cached = dict(cached_last_good)
        cached["quoteStatus"] = "cached"
        return cached
    merged["quoteStatus"] = "unavailable"
    return merged


def fetch_fmp_quote(symbol: str) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.fmp_api_key:
        return {}
    payload = _request_json(
        f"https://financialmodelingprep.com/api/v3/quote/{symbol}",
        {"apikey": settings.fmp_api_key},
    )
    if not payload:
        return {}
    row = payload[0]
    return {
        "regularMarketPrice": safe_float(row.get("price")),
        "regularMarketChangePercent": safe_float(row.get("changesPercentage")),
        "marketCap": safe_float(row.get("marketCap")),
        "longName": row.get("name") or symbol,
        "symbol": row.get("symbol") or symbol,
    }


def fetch_finnhub_quote(symbol: str) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.finnhub_api_key:
        return {}
    quote = _request_json(
        "https://finnhub.io/api/v1/quote",
        {"symbol": symbol, "token": settings.finnhub_api_key},
    )
    profile = _request_json(
        "https://finnhub.io/api/v1/stock/profile2",
        {"symbol": symbol, "token": settings.finnhub_api_key},
    )
    return {
        "regularMarketPrice": safe_float(quote.get("c")),
        "regularMarketChangePercent": safe_float(quote.get("dp")),
        "longName": profile.get("name") or symbol,
        "marketCap": safe_float(profile.get("marketCapitalization")) * 1_000_000.0,
        "sector": profile.get("finnhubIndustry") or "Unknown",
    }


def fetch_alpha_vantage_overview(symbol: str) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.alpha_vantage_api_key:
        return {}
    payload = _request_json(
        "https://www.alphavantage.co/query",
        {"function": "OVERVIEW", "symbol": symbol, "apikey": settings.alpha_vantage_api_key},
    )
    if not payload or "Symbol" not in payload:
        return {}
    return {
        "longName": payload.get("Name") or symbol,
        "sector": payload.get("Sector") or "Unknown",
        "trailingPE": safe_float(payload.get("PERatio")),
        "priceToSalesTrailing12Months": safe_float(payload.get("PriceToSalesRatioTTM")),
        "marketCap": safe_float(payload.get("MarketCapitalization")),
        "profitMargins": safe_float(payload.get("ProfitMargin")),
    }


def fetch_quote_with_fallbacks(symbol: str) -> Dict[str, Any]:
    return robust_quote_fetch(symbol)


def fetch_yfinance_history(symbol: str, period: str) -> Any:
    try:
        history = _run_with_timeout(lambda: yf.Ticker(symbol).history(period=period, auto_adjust=True))
        if history is not None and not history.empty:
            return history
    except Exception as exc:
        logger.warning("yfinance history failed symbol=%s period=%s error=%s", symbol, period, exc)
    try:
        return _run_with_timeout(lambda: yf.download(symbol, period=period, interval="1d", auto_adjust=True, progress=False, threads=False))
    except Exception as exc:
        logger.warning("yfinance download history failed symbol=%s period=%s error=%s", symbol, period, exc)
        raise


def fetch_yfinance_statements(symbol: str) -> tuple[Any, Any, Any]:
    ticker = yf.Ticker(symbol)
    financials = _run_with_timeout(lambda: ticker.financials)
    cashflow = _run_with_timeout(lambda: ticker.cashflow)
    balance_sheet = _run_with_timeout(lambda: ticker.balance_sheet)
    if getattr(financials, "empty", True):
        try:
            financials = _run_with_timeout(lambda: ticker.quarterly_financials)
        except Exception:
            pass
    if getattr(cashflow, "empty", True):
        try:
            cashflow = _run_with_timeout(lambda: ticker.quarterly_cashflow)
        except Exception:
            pass
    if getattr(balance_sheet, "empty", True):
        try:
            balance_sheet = _run_with_timeout(lambda: ticker.quarterly_balance_sheet)
        except Exception:
            pass
    return financials, cashflow, balance_sheet


def provider_diagnostics(symbol: str, environment: str = "development") -> Dict[str, Any]:
    normalized = symbol.strip().upper()
    ticker = yf.Ticker(normalized)
    timings: Dict[str, int] = {}
    errors: list[str] = []

    def measure(name: str, task: Any) -> tuple[bool, Any]:
        started = time.perf_counter()
        try:
            result = _run_with_timeout(task)
            timings[f"{name}_ms"] = int((time.perf_counter() - started) * 1000)
            return True, result
        except TimeoutError as exc:
            timings[f"{name}_ms"] = int((time.perf_counter() - started) * 1000)
            errors.append(f"{name}: timeout after {PROVIDER_TIMEOUT_SECONDS}s")
            return False, None
        except Exception as exc:
            timings[f"{name}_ms"] = int((time.perf_counter() - started) * 1000)
            errors.append(f"{name}: {exc}")
            return False, None

    fast_success, fast_info = measure("fast_info", lambda: ticker.fast_info)
    info_success, info = measure("info", lambda: ticker.info or {})
    history_success, history = measure("history", lambda: ticker.history(period="5d", interval="1d", auto_adjust=True))
    financials_success, financials = measure("financials", lambda: ticker.financials)
    cashflow_success, cashflow = measure("cashflow", lambda: ticker.cashflow)
    balance_success, balance = measure("balance_sheet", lambda: ticker.balance_sheet)
    download_success, download = measure("download", lambda: yf.download(normalized, period="5d", interval="1d", progress=False, threads=False, auto_adjust=True))
    sample_quote = robust_quote_fetch(normalized)

    return {
        "ticker": normalized,
        "environment": environment,
        "provider": "yfinance",
        "fast_info_success": bool(fast_success and fast_info),
        "info_success": bool(info_success and info),
        "history_success": bool(history_success and history is not None and not getattr(history, "empty", True)),
        "financials_success": bool(financials_success and financials is not None and not getattr(financials, "empty", True)),
        "cashflow_success": bool(cashflow_success and cashflow is not None and not getattr(cashflow, "empty", True)),
        "balance_sheet_success": bool(balance_success and balance is not None and not getattr(balance, "empty", True)),
        "download_success": bool(download_success and download is not None and not getattr(download, "empty", True)),
        "last_error": errors[-1] if errors else None,
        "errors": errors,
        "timings": timings,
        "sample_quote": {
            "symbol": sample_quote.get("symbol") or normalized,
            "currentPrice": sample_quote.get("currentPrice"),
            "regularMarketPrice": sample_quote.get("regularMarketPrice"),
            "previousClose": sample_quote.get("previousClose"),
            "regularMarketChange": sample_quote.get("regularMarketChange"),
            "regularMarketChangePercent": sample_quote.get("regularMarketChangePercent"),
            "marketCap": sample_quote.get("marketCap"),
            "longName": sample_quote.get("longName"),
            "sector": sample_quote.get("sector"),
            "quoteStatus": sample_quote.get("quoteStatus"),
            "quoteSource": sample_quote.get("quoteSource"),
        },
    }


def fetch_yfinance_news(symbol: str) -> List[Dict[str, Any]]:
    try:
        return yf.Ticker(symbol).news or []
    except Exception:
        return []
