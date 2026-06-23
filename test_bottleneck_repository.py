from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_theme_repository_creates_bottleneck_table_and_indexes(tmp_path: Path) -> None:
    db_path = tmp_path / "theme.sqlite3"
    repo = ThemeRepository(db_path)
    repo.initialize()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(theme_bottlenecks)").fetchall()}
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(theme_bottlenecks)").fetchall()}

    assert "bottleneck_strength" in columns
    assert "controller_entities_json" in columns
    assert "idx_theme_bottlenecks_theme_strength" in indexes
    assert "idx_theme_bottlenecks_theme_type" in indexes
    assert "idx_theme_bottlenecks_theme_timeline" in indexes


def test_theme_repository_upserts_bottlenecks(tmp_path: Path) -> None:
    repo = ThemeRepository(tmp_path / "theme.sqlite3")
    repo.initialize()
    row = BottleneckRecord(
        theme_name="Glass Substrate",
        bottleneck_name="Yield",
        bottleneck_type="Yield Constraint",
        severity_score=88,
        duration_score=76,
        resolution_probability=65,
        impact_score=84,
        bottleneck_strength=81,
        controller_entities=[{"ticker": "GLW", "role": "controller"}],
        beneficiaries=[{"ticker": "AMAT", "role": "beneficiary"}],
        timeline_status="current",
        description="Yield limits scalable adoption.",
        evidence=[{"source": "finnhub"}],
        updated_at="2026-06-05T00:00:00+00:00",
    )

    assert repo.save_bottlenecks([row]) == 1
    assert repo.save_bottlenecks([row.with_updates(severity_score=90, bottleneck_strength=83)]) == 1

    saved = repo.get_bottlenecks()
    assert len(saved) == 1
    assert saved[0].severity_score == 90
    assert saved[0].controller_entities[0]["ticker"] == "GLW"

