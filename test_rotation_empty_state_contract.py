from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from quant_engine.sector_rotation_engine import analyze_sector_rotation


def test_rotation_empty_state_has_no_fabricated_leaders(monkeypatch) -> None:
    monkeypatch.setattr(
        "quant_engine.sector_rotation_engine.engine._cached_quote_entry",
        lambda symbol: None,
    )

    payload = analyze_sector_rotation()

    assert payload["status"] == "unavailable"
    assert payload["leaders"] == []
    assert payload["laggards"] == []
    assert len(payload["sector_ranking"]) == 11
    assert all(row["score"] is None for row in payload["sector_ranking"])
    assert all(row["status"] == "unavailable" for row in payload["sector_ranking"])
    assert payload["selected_sector"] is None

