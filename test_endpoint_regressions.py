from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_engine import theme_rotation
from theme_intelligence.models import ThemeMention
from theme_intelligence.scoring.velocity_score import news_velocity_score


def test_news_velocity_accepts_offset_naive_persisted_timestamps() -> None:
    mentions = [
        ThemeMention(
            "HBM",
            "market",
            "MU",
            "HBM capacity expands",
            "2026-06-13T08:00:00",
            60,
        ),
    ]

    score = news_velocity_score(
        mentions,
        now=datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc),
    )

    assert 0 <= score <= 100


def test_theme_rotation_uses_current_horizon_score_contract(
    monkeypatch: Any,
) -> None:
    definition = theme_rotation.get_theme_definitions()[0]
    calls: list[tuple[str, dict[str, Any], dict[str, float]]] = []

    monkeypatch.setattr(
        theme_rotation,
        "get_theme_definitions",
        lambda: [definition],
    )
    monkeypatch.setattr(
        theme_rotation,
        "_lightweight_theme_row",
        lambda theme: theme_rotation._fallback_theme_row(theme),
    )
    monkeypatch.setattr(
        theme_rotation,
        "enrich_universe_ranking",
        lambda row, _entity_type: row,
    )
    monkeypatch.setattr(
        theme_rotation,
        "enrich_theme_narrative",
        lambda row: row,
    )
    monkeypatch.setattr(
        theme_rotation,
        "enrich_theme_leadership",
        lambda row: row,
    )

    def horizon_scores(
        theme_name: str,
        metrics: dict[str, Any],
        raw_scores: dict[str, float],
    ) -> dict[str, float]:
        calls.append((theme_name, metrics, raw_scores))
        return {"1w": 40.0, "1m": 50.0, "3m": 60.0}

    monkeypatch.setattr(theme_rotation, "compute_horizon_scores", horizon_scores)

    rows = theme_rotation._theme_snapshot.__wrapped__(123)

    assert len(rows) == 1
    assert calls and calls[0][0] == definition.name
