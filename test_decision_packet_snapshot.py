from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.storage.theme_repository import ThemeRepository


def test_decision_packet_schema_is_additive(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "packet.sqlite3")
    repository.initialize()
    with sqlite3.connect(repository.db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "decision_packets",
            "decision_packet_paths",
            "decision_packet_evidence",
            "decision_packet_risks",
        } <= tables
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(decision_packets)")
        }
        assert {
            "packet_family_version",
            "packet_family_revision",
            "graph_snapshot_id",
            "controller_snapshot_id",
            "opportunity_snapshot_id",
            "packet_checksum",
            "family_checksum",
        } <= columns
