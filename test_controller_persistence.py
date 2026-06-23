from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.storage.theme_repository import ThemeRepository


def test_controller_schema_is_additive(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "controller.sqlite3")
    repository.initialize()
    with sqlite3.connect(repository.db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"graph_metrics", "controller_metrics", "controller_snapshots"} <= tables
        snapshot_columns = {row[1] for row in conn.execute("PRAGMA table_info(controller_snapshots)")}
        assert {"graph_snapshot_id", "algorithm_version", "checksum", "status"} <= snapshot_columns
