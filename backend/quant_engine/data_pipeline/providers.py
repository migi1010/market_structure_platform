from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List

import requests
import yfinance as yf

from settings import get_settings

logger = logging.getLogger("miji.providers")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _request_json(url: str, params: Dict[str, Any] | None = None) -> Any:
    settings = get_settings()
    last_error: Exception | None = None
    for attempt in range(settings.provider_retry_count):
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
    return yf.Ticker(symbol).info or {}


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
    merged: Dict[str, Any] = {}
    for fetcher in (
        fetch_yfinance_quote,
        fetch_fmp_quote,
        fetch_finnhub_quote,
        fetch_alpha_vantage_overview,
    ):
        try:
            merged.update({key: value for key, value in fetcher(symbol).items() if value not in (None, "")})
        except Exception as exc:
            logger.warning("quote fallback failed symbol=%s provider=%s error=%s", symbol, fetcher.__name__, exc)
    return merged


def fetch_yfinance_history(symbol: str, period: str) -> Any:
    return yf.Ticker(symbol).history(period=period, auto_adjust=True)


def fetch_yfinance_statements(symbol: str) -> tuple[Any, Any, Any]:
    ticker = yf.Ticker(symbol)
    return ticker.financials, ticker.cashflow, ticker.balance_sheet


def fetch_yfinance_news(symbol: str) -> List[Dict[str, Any]]:
    try:
        return yf.Ticker(symbol).news or []
    except Exception:
        return []
