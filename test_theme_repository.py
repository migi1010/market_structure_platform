from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeEntity, ThemeMention, ThemeScore
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_theme_repository_creates_all_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "theme.sqlite3"
    repo = ThemeRepository(db_path)
    repo.initialize()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }

    assert "theme_mentions" in tables
    assert "theme_scores" in tables
    assert "theme_entities" in tables
    assert "theme_catalysts" in tables
    assert "theme_beneficiaries" in tables


def test_theme_repository_persists_theme_intelligence_rows(tmp_path: Path) -> None:
    repo = ThemeRepository(tmp_path / "theme.sqlite3")
    repo.initialize()

    assert repo.save_mentions([ThemeMention("HBM", "finnhub", "NVDA", "HBM demand growth", "2026-06-05T00:00:00+00:00", 75)]) == 1
    assert repo.save_entities([ThemeEntity("HBM", "company", "NVIDIA Corporation", "NVDA", 120)]) == 1
    assert repo.save_catalysts([CatalystRecord("HBM", "NVIDIA Blackwell", "product_cycle", "finnhub", 88, 91)]) == 1
    assert repo.save_beneficiaries([ThemeBeneficiary("HBM", "NVDA", "NVIDIA Corporation", 93, 89)]) == 1
    assert repo.upsert_scores([ThemeScore("HBM", 84, 77, 73, 81, 69, 78, "Early", 150, "Growth")]) == 1

    scores = repo.get_scores()
    assert scores[0]["name"] == "HBM"
    assert scores[0]["lifecycle_stage"] == "Early"
    assert scores[0]["lifecycle_confidence"] == 100
    assert scores[0]["expected_next_stage"] == "Growth"
    assert scores[0]["total_score"] == 78
