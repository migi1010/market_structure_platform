from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_repository import ThemeScoutRepository
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_initialize_creates_five_scout_tables(tmp_path) -> None:
    repository = ThemeRepository(tmp_path / "scout.sqlite3")
    repository.initialize()
    with repository._connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {
        "theme_scout_snapshots",
        "theme_candidates",
        "theme_candidate_evidence",
        "theme_candidate_paths",
        "theme_candidate_influence_maps",
    } <= tables


def test_scout_repository_does_not_require_graph_snapshot(tmp_path) -> None:
    repository = ThemeScoutRepository(ThemeRepository(tmp_path / "scout.sqlite3"))
    repository.initialize()
    assert repository.get_active_snapshot() is None
