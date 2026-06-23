from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from quant_engine.sector_rotation_engine import analyze_sector_rotation
from quant_engine.sector_rotation_engine import engine


def _entry(change: float, *, expired: bool = False) -> dict:
    return {
        "value": {
            "change_percent": change,
            "volume": 120,
            "averageVolume": 100,
            "quoteStatus": "stale" if expired else "live",
            "source": "test_cache",
        },
        "updated_at": 1_781_300_000,
        "cache_age_seconds": 900 if expired else 30,
        "is_expired": expired,
    }


def test_mixed_rotation_coverage_is_partial_and_never_live(monkeypatch) -> None:
    entries = {"SPY": _entry(0.4), "XLK": _entry(1.2)}
    monkeypatch.setattr(
        "quant_engine.sector_rotation_engine.engine._cached_quote_entry",
        lambda symbol: entries.get(symbol),
    )

    payload = analyze_sector_rotation()

    assert payload["status"] == "partial"
    assert payload["leaders"][0]["status"] == "partial"
    assert payload["data_quality"]["available_sectors"] == 1
    assert not any(row["status"] == "live" for row in payload["sector_ranking"])


def test_expired_rotation_quotes_are_stale_not_live(monkeypatch) -> None:
    monkeypatch.setattr(
        "quant_engine.sector_rotation_engine.engine._cached_quote_entry",
        lambda symbol: _entry(0.6, expired=True),
    )

    payload = analyze_sector_rotation()

    assert payload["status"] == "stale"
    assert payload["leaders"]
    assert all(row["status"] == "stale" for row in payload["leaders"])


def test_last_known_good_rotation_quote_is_stale_even_with_live_provider_marker(monkeypatch) -> None:
    lkg = _entry(0.6)
    monkeypatch.setattr(
        engine,
        "get_cached_entry",
        lambda key, allow_expired=False: lkg if key.startswith("quote_lkg:") else None,
    )

    entry = engine._cached_quote_entry("XLK")

    assert engine._entry_status(entry) == "stale"
