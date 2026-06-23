from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import main
from quant_engine.stock_service import _normalized_quote, _resolve_price_snapshot


def _raw_quote(price: float, status: str, source: str) -> dict:
    return {
        "symbol": "NVDA",
        "currentPrice": price,
        "previousClose": price - 1,
        "quoteStatus": status,
        "source": source,
        "fetched_at": "2026-06-11T01:00:00Z",
        "updated_at": "2026-06-11T01:00:00Z",
        "expires_at": "2026-06-11T01:01:00Z",
        "cache_age_seconds": 480,
        "is_stale": status != "live",
    }


def test_stock_normalization_preserves_stale_status_and_freshness() -> None:
    raw = _raw_quote(100, "stale", "stale_cache")

    normalized = _normalized_quote("NVDA", raw, _resolve_price_snapshot("NVDA", raw, {}))

    assert normalized["price"] == 100
    assert normalized["status"] == "stale"
    assert normalized["source"] == "stale_cache"
    assert normalized["is_stale"] is True
    assert normalized["cache_age_seconds"] == 480
    assert normalized["updated_at"] == "2026-06-11T01:00:00Z"


def test_quote_aware_fallback_does_not_promote_fallback_price(monkeypatch) -> None:
    monkeypatch.setattr(main, "get_quote", lambda _: _raw_quote(95, "fallback", "last_known_good"))

    payload = main._quote_aware_stock_fallback("NVDA")

    assert payload["quote_status"] == "fallback"
    assert payload["quote"]["status"] == "fallback"
    assert payload["quote"]["source"] == "last_known_good"
    assert payload["quote"]["is_stale"] is True


def test_quote_only_refresh_reuses_research_payload(monkeypatch) -> None:
    cached = {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "price": 100,
        "quote_status": "stale",
        "quote": {"ticker": "NVDA", "price": 100, "status": "stale"},
        "bubble_analysis_data": {"bubble_index": 42},
        "earnings_quality": {"earnings_quality_score": 81},
        "smart_money": {"smart_money_score": 72},
        "news": [{"title": "persisted research"}],
    }
    fresh = _raw_quote(110, "live", "fresh_provider")
    monkeypatch.setattr(main, "get_quote", lambda _, force_refresh=False: fresh)

    result = main._refresh_stock_quote("NVDA", cached)

    assert result["price"] == 110
    assert result["quote_status"] == "live"
    assert result["quote"]["source"] == "fresh_provider"
    assert result["bubble_analysis_data"] is cached["bubble_analysis_data"]
    assert result["earnings_quality"] is cached["earnings_quality"]
    assert result["smart_money"] is cached["smart_money"]
    assert result["news"] is cached["news"]


def test_expired_stock_endpoint_cache_is_downgraded_before_return(monkeypatch) -> None:
    stale = {
        "ticker": "NVDA",
        "price": 100,
        "quote_status": "live",
        "quote": {"ticker": "NVDA", "price": 100, "status": "live", "source": "provider"},
        "bubble_analysis_data": {"bubble_index": 42},
        "earnings_quality": {"earnings_quality_score": 81},
        "smart_money": {"smart_money_score": 72},
    }
    reads = iter([None, stale])
    monkeypatch.setattr(main, "get_cached_value", lambda *args, **kwargs: next(reads))
    monkeypatch.setattr(main, "_schedule_cache_refresh", lambda *args, **kwargs: None)

    result = main._fast_cached_response(
        "endpoint:stock_v6:STOCK:NVDA",
        60,
        lambda: stale,
        lambda: stale,
    )

    assert result["quote_status"] == "stale"
    assert result["is_stale"] is True
    assert result["quote"]["status"] == "stale"
    assert result["quote"]["source"] == "stale_endpoint_cache"
    assert result["lifecycle_state"] == "recovery"
