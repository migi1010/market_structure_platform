from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from quant_engine.sector_rotation_engine import analyze_sector_rotation


def _entry(change: float, volume_ratio: float = 1.0) -> dict:
    return {
        "value": {
            "change_percent": change,
            "volume": volume_ratio * 100,
            "averageVolume": 100,
            "quoteStatus": "live",
            "source": "test_provider",
        },
        "updated_at": 1_781_300_000,
        "cache_age_seconds": 10,
        "is_expired": False,
    }


def test_sector_ranking_orders_only_evidence_backed_rows(monkeypatch) -> None:
    entries = {
        "SPY": _entry(0.5),
        "XLK": _entry(2.0, 1.5),
        "XLE": _entry(-1.0, 0.7),
    }
    monkeypatch.setattr(
        "quant_engine.sector_rotation_engine.engine._cached_quote_entry",
        lambda symbol: entries.get(symbol),
    )

    payload = analyze_sector_rotation()
    scored = [row for row in payload["sector_ranking"] if row["score"] is not None]

    assert [row["sector"] for row in scored] == ["Technology", "Energy"]
    assert payload["leaders"][0]["sector"] == "Technology"
    assert payload["laggards"][0]["sector"] == "Energy"
    assert payload["selected_sector"]["sector"] == "Technology"
    assert all(row["rotation_score"] == row["score"] for row in scored)
    assert all("rotation_confidence" in row for row in payload["sector_ranking"])
