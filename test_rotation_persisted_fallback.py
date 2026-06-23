from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import main


def test_rotation_endpoint_serves_expired_persisted_snapshot_as_stale(monkeypatch) -> None:
    stale = {
        "status": "live",
        "source": "sector_etf_quotes",
        "updated_at": "2026-06-12T00:00:00Z",
        "leaders": [{"sector": "Technology", "score": 70}],
        "laggards": [],
        "sector_ranking": [{"sector": "Technology", "score": 70}],
        "selected_sector": {"sector": "Technology"},
        "diagnostics": [],
        "theme_links": [],
        "data_quality": {"available_sectors": 1, "total_sectors": 11},
    }
    monkeypatch.setattr(
        main,
        "get_cached_value",
        lambda key, allow_expired=False: stale if allow_expired else None,
    )
    monkeypatch.setattr(
        main,
        "_sector_rotation_snapshot_response",
        lambda: (_ for _ in ()).throw(RuntimeError("provider unavailable")),
    )

    payload = main.get_sector_rotation()

    assert payload["status"] == "stale"
    assert payload["source"] == "persisted_cache"
    assert payload["leaders"][0]["sector"] == "Technology"

