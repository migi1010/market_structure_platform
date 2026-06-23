from __future__ import annotations

import json
import logging
import pickle
import sqlite3
import threading
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

import pandas as pd

logger = logging.getLogger("miji.market_data")

from quant_engine.data_pipeline.providers import (
    fetch_quote_with_fallbacks,
    fetch_yfinance_history,
    fetch_yfinance_news,
    fetch_yfinance_statements,
    finite_float,
    provider_diagnostics,
    robust_quote_fetch,
    safe_float,
)
from settings import get_settings

CACHE_SCHEMA_VERSION = "stock_v6"
_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[str, threading.Lock] = {}


def _lock_for(cache_key: str) -> threading.Lock:
    with _LOCKS_GUARD:
        if cache_key not in _LOCKS:
            _LOCKS[cache_key] = threading.Lock()
        return _LOCKS[cache_key]


class SQLiteCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=20, check_same_thread=False)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kv_cache (
                    cache_key TEXT PRIMARY KEY,
                    content_type TEXT NOT NULL,
                    payload BLOB NOT NULL,
                    expires_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_meta (
                    meta_key TEXT PRIMARY KEY,
                    meta_value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get(self, cache_key: str, allow_expired: bool = False) -> tuple[str, bytes] | None:
        entry = self.get_entry(cache_key, allow_expired=allow_expired)
        if entry is None:
            return None
        content_type, payload, _, _ = entry
        return content_type, payload

    def get_entry(
        self,
        cache_key: str,
        allow_expired: bool = False,
    ) -> tuple[str, bytes, int, int] | None:
        now = int(time.time())
        with self._connect() as conn:
            row = conn.execute(
                "SELECT content_type, payload, expires_at, updated_at FROM kv_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if row is None:
                return None
            content_type, payload, expires_at, updated_at = row
            if int(expires_at) < now and not allow_expired:
                return None
            return str(content_type), bytes(payload), int(expires_at), int(updated_at)

    def set(self, cache_key: str, content_type: str, payload: bytes, ttl_seconds: int) -> None:
        now = int(time.time())
        expires_at = now + ttl_seconds
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO kv_cache (cache_key, content_type, payload, expires_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    content_type = excluded.content_type,
                    payload = excluded.payload,
                    expires_at = excluded.expires_at,
                    updated_at = excluded.updated_at
                """,
                (cache_key, content_type, payload, expires_at, now),
            )
            conn.commit()

    def get_meta(self, meta_key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT meta_value FROM cache_meta WHERE meta_key = ?",
                (meta_key,),
            ).fetchone()
            return str(row[0]) if row else None

    def set_meta(self, meta_key: str, meta_value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cache_meta (meta_key, meta_value)
                VALUES (?, ?)
                ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
                """,
                (meta_key, meta_value),
            )
            conn.commit()

    def delete_stale_schema_entries(self, current_schema: str) -> int:
        stale_endpoint_prefix = f"endpoint:{current_schema}:%"
        current_data_prefixes = (
            f"quote:{current_schema}:%",
            f"quote_lkg:{current_schema}:%",
            f"history:{current_schema}:%",
            f"financials:{current_schema}:%",
            f"news:{current_schema}:%",
        )
        with self._connect() as conn:
            before = int(conn.execute("SELECT COUNT(*) FROM kv_cache").fetchone()[0])
            conn.execute(
                """
                DELETE FROM kv_cache
                WHERE (
                    cache_key LIKE 'endpoint:%'
                    AND cache_key NOT LIKE ?
                )
                OR cache_key LIKE 'quote_v%'
                OR cache_key LIKE 'history_v%'
                OR cache_key LIKE 'financials_v%'
                OR cache_key LIKE 'news_v%'
                OR (
                    (cache_key LIKE 'quote:%' OR cache_key LIKE 'quote_lkg:%' OR cache_key LIKE 'history:%' OR cache_key LIKE 'financials:%' OR cache_key LIKE 'news:%')
                    AND cache_key NOT LIKE ?
                    AND cache_key NOT LIKE ?
                    AND cache_key NOT LIKE ?
                    AND cache_key NOT LIKE ?
                    AND cache_key NOT LIKE ?
                )
                """,
                (stale_endpoint_prefix, *current_data_prefixes),
            )
            conn.commit()
            after = int(conn.execute("SELECT COUNT(*) FROM kv_cache").fetchone()[0])
            return max(0, before - after)


@lru_cache(maxsize=1)
def _cache() -> SQLiteCache:
    return SQLiteCache(get_settings().sqlite_cache_path)


def initialize_cache() -> None:
    cache = _cache()
    previous_schema = cache.get_meta("cache_schema_version")
    if previous_schema != CACHE_SCHEMA_VERSION:
        cache.delete_stale_schema_entries(CACHE_SCHEMA_VERSION)
        cache.set_meta("cache_schema_version", CACHE_SCHEMA_VERSION)


def _get_cached(cache_key: str, allow_expired: bool = False) -> Any | None:
    item = _cache().get(cache_key, allow_expired=allow_expired)
    if item is None:
        return None
    content_type, payload = item
    if content_type == "json":
        return json.loads(payload.decode("utf-8"))
    if content_type == "pickle":
        return pickle.loads(payload)
    return None


def _get_cached_entry(cache_key: str, allow_expired: bool = False) -> dict[str, Any] | None:
    item = _cache().get_entry(cache_key, allow_expired=allow_expired)
    if item is None:
        return None
    content_type, payload, expires_at, updated_at = item
    if content_type == "json":
        value = json.loads(payload.decode("utf-8"))
    elif content_type == "pickle":
        value = pickle.loads(payload)
    else:
        return None
    now = int(time.time())
    return {
        "value": value,
        "expires_at": expires_at,
        "updated_at": updated_at,
        "cache_age_seconds": max(0, now - updated_at),
        "is_expired": expires_at < now,
    }


def _set_cached(cache_key: str, value: Any, ttl_seconds: int, content_type: str = "json") -> None:
    if content_type == "json":
        payload = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    else:
        payload = pickle.dumps(value)
    _cache().set(cache_key, content_type, payload, ttl_seconds)


def get_cached_value(cache_key: str, allow_expired: bool = False) -> Any | None:
    return _get_cached(cache_key, allow_expired=allow_expired)


def get_cached_entry(cache_key: str, allow_expired: bool = False) -> dict[str, Any] | None:
    return _get_cached_entry(cache_key, allow_expired=allow_expired)


def set_cached_value(cache_key: str, value: Any, ttl_seconds: int, content_type: str = "json") -> None:
    _set_cached(cache_key, value, ttl_seconds, content_type)


def _quote_has_price(quote: Dict[str, Any] | None) -> bool:
    if not isinstance(quote, dict):
        return False
    price = finite_float(quote.get("currentPrice") or quote.get("regularMarketPrice"))
    return price is not None and price > 0


def _iso_timestamp(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def is_market_open_context() -> bool | None:
    try:
        market_time = datetime.now(ZoneInfo("America/New_York"))
        return (
            market_time.weekday() < 5
            and (market_time.hour, market_time.minute) >= (9, 30)
            and (market_time.hour, market_time.minute) < (16, 0)
        )
    except Exception:
        return None


def quote_ttl_seconds(is_market_open_context: bool | None = None) -> int:
    return 600 if is_market_open_context is False else 60


def _quote_with_freshness(
    quote: Dict[str, Any],
    *,
    status: str,
    source: str,
    updated_at: int,
    expires_at: int,
) -> Dict[str, Any]:
    result = dict(quote)
    now = int(time.time())
    result["quoteStatus"] = status
    result["quote_status"] = status
    result["quoteSource"] = source
    result["source"] = source
    result["fetched_at"] = _iso_timestamp(updated_at)
    result["updated_at"] = _iso_timestamp(updated_at)
    result["expires_at"] = _iso_timestamp(expires_at)
    result["cache_age_seconds"] = max(0, now - updated_at)
    result["is_stale"] = status != "live"
    return result


def _cached_quote(
    entry: dict[str, Any] | None,
    *,
    status: str,
    source: str,
) -> Dict[str, Any] | None:
    if entry is None or not _quote_has_price(entry.get("value")):
        return None
    return _quote_with_freshness(
        entry["value"],
        status=status,
        source=source,
        updated_at=entry["updated_at"],
        expires_at=entry["expires_at"],
    )


def _statements_available(statements: Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] | Any) -> bool:
    if not isinstance(statements, tuple) or len(statements) != 3:
        return False
    return any(frame is not None and not getattr(frame, "empty", True) for frame in statements)


def get_quote(symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
    normalized = symbol.strip().upper()
    cache_key = f"quote:{CACHE_SCHEMA_VERSION}:{normalized}"
    last_good_key = f"quote_lkg:{CACHE_SCHEMA_VERSION}:{normalized}"
    cached_entry = None if force_refresh else _get_cached_entry(cache_key)
    cached = _cached_quote(
        cached_entry,
        status=str(cached_entry["value"].get("quoteStatus") or "live") if cached_entry else "live",
        source=str(cached_entry["value"].get("source") or cached_entry["value"].get("quoteSource") or "quote_cache")
        if cached_entry
        else "quote_cache",
    )
    if cached is not None:
        logger.debug("get_quote cache hit symbol=%s", normalized)
        return cached
    stale_entry = _get_cached_entry(cache_key, allow_expired=True)
    last_good_entry = _get_cached_entry(last_good_key, allow_expired=True)
    with _lock_for(cache_key):
        if not force_refresh:
            cached_entry = _get_cached_entry(cache_key)
            cached = _cached_quote(
                cached_entry,
                status=str(cached_entry["value"].get("quoteStatus") or "live") if cached_entry else "live",
                source=str(cached_entry["value"].get("source") or cached_entry["value"].get("quoteSource") or "quote_cache")
                if cached_entry
                else "quote_cache",
            )
            if cached is not None:
                return cached
        stale_entry = _get_cached_entry(cache_key, allow_expired=True)
        last_good_entry = _get_cached_entry(last_good_key, allow_expired=True)
        quote = robust_quote_fetch(normalized, None) or {}
        if _quote_has_price(quote) and str(quote.get("quoteStatus") or "").lower() == "live":
            logger.info("get_quote live fetch succeeded symbol=%s source=%s",
                        normalized, quote.get("quoteSource") or quote.get("quoteStatus"))
            ttl_seconds = quote_ttl_seconds(is_market_open_context())
            source = str(quote.get("quoteSource") or "provider")
            _set_cached(cache_key, quote, ttl_seconds, "json")
            _set_cached(last_good_key, quote, max(ttl_seconds * 288, 86400), "json")
            now = int(time.time())
            return _quote_with_freshness(
                quote,
                status="live",
                source=source,
                updated_at=now,
                expires_at=now + ttl_seconds,
            )
        stale = _cached_quote(stale_entry, status="stale", source="stale_cache")
        if stale is not None:
            logger.warning("get_quote serving stale cache symbol=%s", normalized)
            return stale
        last_good = _cached_quote(last_good_entry, status="fallback", source="last_known_good")
        if last_good is not None:
            logger.warning("get_quote serving last-known-good symbol=%s", normalized)
            return last_good
        logger.warning("get_quote all providers failed symbol=%s status=%s",
                       normalized, quote.get("quoteStatus"))
        return quote if isinstance(quote, dict) else {"symbol": normalized, "quoteStatus": "unavailable"}


def _bounded_history_period(period: str | None) -> str:
    allowed = {"5d", "10d", "1mo", "3mo"}
    normalized = (period or "3mo").strip().lower()
    return normalized if normalized in allowed else "3mo"


def get_history(symbol: str, period: str = "3mo") -> pd.DataFrame:
    normalized = symbol.strip().upper()
    period = _bounded_history_period(period)
    cache_key = f"history:{CACHE_SCHEMA_VERSION}:{normalized}:{period}"
    lightweight_mode = get_settings().miji_lightweight_mode
    stale = None
    if not lightweight_mode:
        cached = _get_cached(cache_key)
        if isinstance(cached, pd.DataFrame):
            return cached
        stale = _get_cached(cache_key, allow_expired=True)
    with _lock_for(cache_key):
        if not lightweight_mode:
            cached = _get_cached(cache_key)
            if isinstance(cached, pd.DataFrame):
                return cached
            stale = _get_cached(cache_key, allow_expired=True)
        try:
            df = fetch_yfinance_history(normalized, period)
        except Exception:
            if isinstance(stale, pd.DataFrame):
                return stale
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        result = df.dropna()
        if not result.empty:
            if not get_settings().miji_lightweight_mode:
                _set_cached(cache_key, result, get_settings().history_ttl_seconds, "pickle")
            return result
        if isinstance(stale, pd.DataFrame):
            return stale
        return result


def get_statements(symbol: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    normalized = symbol.strip().upper()
    cache_key = f"financials:{CACHE_SCHEMA_VERSION}:{normalized}"
    cached = _get_cached(cache_key)
    if _statements_available(cached):
        return cached
    stale = _get_cached(cache_key, allow_expired=True)
    with _lock_for(cache_key):
        cached = _get_cached(cache_key)
        if _statements_available(cached):
            return cached
        stale = _get_cached(cache_key, allow_expired=True)
        try:
            statements = fetch_yfinance_statements(normalized)
        except Exception:
            if _statements_available(stale):
                return stale
            empty = pd.DataFrame()
            return empty, empty, empty
        if _statements_available(statements):
            _set_cached(cache_key, statements, get_settings().statement_ttl_seconds, "pickle")
            return statements
        if _statements_available(stale):
            return stale
        return statements


def get_news(symbol: str) -> List[Dict[str, Any]]:
    normalized = symbol.strip().upper()
    cache_key = f"news:{CACHE_SCHEMA_VERSION}:{normalized}"
    cached = _get_cached(cache_key)
    if isinstance(cached, list):
        return cached
    with _lock_for(cache_key):
        cached = _get_cached(cache_key)
        if isinstance(cached, list):
            return cached
        news = fetch_yfinance_news(normalized)
        _set_cached(cache_key, news, get_settings().news_ttl_seconds, "json")
        return news


def refresh_symbols(symbols: List[str]) -> Dict[str, int]:
    refreshed = 0
    failed = 0
    for symbol in symbols:
        try:
            get_quote(symbol)
            get_history(symbol)
            get_statements(symbol)
            get_news(symbol)
            refreshed += 1
        except Exception:
            failed += 1
    return {"refreshed": refreshed, "failed": failed}


def statement_value(statement: pd.DataFrame, names: List[str], offset: int = 0) -> float:
    if statement is None or statement.empty:
        return 0.0
    for name in names:
        if name in statement.index:
            series = statement.loc[name]
            if hasattr(series, "iloc") and len(series) > offset:
                return safe_float(series.iloc[offset])
    return 0.0


def previous_statement_value(statement: pd.DataFrame, names: List[str]) -> float:
    return statement_value(statement, names, offset=1)


def debug_provider(symbol: str) -> Dict[str, Any]:
    return provider_diagnostics(symbol, get_settings().environment)
