from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from quant_engine.data_pipeline import market_data


def _quote(price: float, *, status: str = "live", source: str = "test_provider") -> dict:
    return {
        "symbol": "NVDA",
        "currentPrice": price,
        "regularMarketPrice": price,
        "previousClose": price - 1,
        "regularMarketPreviousClose": price - 1,
        "quoteStatus": status,
        "quoteSource": source,
    }


def _set_cache_age(cache: market_data.SQLiteCache, cache_key: str, age_seconds: int, expired: bool) -> None:
    now = int(time.time())
    with sqlite3.connect(cache.path) as conn:
        conn.execute(
            "UPDATE kv_cache SET updated_at = ?, expires_at = ? WHERE cache_key = ?",
            (now - age_seconds, now - 1 if expired else now + 60, cache_key),
        )
        conn.commit()


def test_expired_quote_cache_is_labeled_stale_with_age_metadata(tmp_path: Path, monkeypatch) -> None:
    cache = market_data.SQLiteCache(tmp_path / "quotes.sqlite3")
    key = f"quote:{market_data.CACHE_SCHEMA_VERSION}:NVDA"
    cache.set(key, "json", json.dumps(_quote(100)).encode(), 60)
    _set_cache_age(cache, key, age_seconds=480, expired=True)
    monkeypatch.setattr(market_data, "_cache", lambda: cache)
    monkeypatch.setattr(
        market_data,
        "robust_quote_fetch",
        lambda symbol, cached_last_good=None: {"symbol": symbol, "quoteStatus": "unavailable"},
    )

    result = market_data.get_quote("NVDA")

    assert result["quoteStatus"] == "stale"
    assert result["is_stale"] is True
    assert result["cache_age_seconds"] >= 480
    assert result["source"] == "stale_cache"
    assert result["fetched_at"]
    assert result["updated_at"]
    assert result["expires_at"]


def test_last_known_good_is_labeled_fallback(tmp_path: Path, monkeypatch) -> None:
    cache = market_data.SQLiteCache(tmp_path / "quotes.sqlite3")
    key = f"quote_lkg:{market_data.CACHE_SCHEMA_VERSION}:NVDA"
    cache.set(key, "json", json.dumps(_quote(95)).encode(), 86_400)
    _set_cache_age(cache, key, age_seconds=1_200, expired=False)
    monkeypatch.setattr(market_data, "_cache", lambda: cache)
    monkeypatch.setattr(
        market_data,
        "robust_quote_fetch",
        lambda symbol, cached_last_good=None: {"symbol": symbol, "quoteStatus": "unavailable"},
    )

    result = market_data.get_quote("NVDA")

    assert result["quoteStatus"] == "fallback"
    assert result["is_stale"] is True
    assert result["source"] == "last_known_good"
    assert result["cache_age_seconds"] >= 1_200


def test_force_refresh_bypasses_fresh_quote_cache_and_updates_it(tmp_path: Path, monkeypatch) -> None:
    cache = market_data.SQLiteCache(tmp_path / "quotes.sqlite3")
    key = f"quote:{market_data.CACHE_SCHEMA_VERSION}:NVDA"
    cache.set(key, "json", json.dumps(_quote(100)).encode(), 60)
    monkeypatch.setattr(market_data, "_cache", lambda: cache)
    calls: list[str] = []

    def fetch(symbol: str, cached_last_good=None) -> dict:
        calls.append(symbol)
        return _quote(110, source="fresh_provider")

    monkeypatch.setattr(market_data, "robust_quote_fetch", fetch)

    cached = market_data.get_quote("NVDA")
    refreshed = market_data.get_quote("NVDA", force_refresh=True)
    stored = market_data.get_quote("NVDA")

    assert cached["currentPrice"] == 100
    assert refreshed["currentPrice"] == 110
    assert refreshed["quoteStatus"] == "live"
    assert refreshed["is_stale"] is False
    assert refreshed["source"] == "fresh_provider"
    assert stored["currentPrice"] == 110
    assert calls == ["NVDA"]


def test_market_aware_quote_ttl_policy() -> None:
    assert market_data.quote_ttl_seconds(is_market_open_context=True) == 60
    assert market_data.quote_ttl_seconds(is_market_open_context=False) == 600
    assert market_data.quote_ttl_seconds(is_market_open_context=None) == 60
