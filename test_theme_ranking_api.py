from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import main
from settings import get_settings
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_theme_ranking_api_returns_read_only_projection(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "ranking-api.sqlite3"
    monkeypatch.setattr(main, "settings", replace(get_settings(), sqlite_cache_path=db_path))
    repository = ThemeRepository(db_path)
    repository.initialize()
    with repository._connect() as conn:
        conn.execute(
            """
            INSERT INTO graph_nodes (
                node_type, canonical_key, display_name, aliases_json, external_ids_json,
                status, valid_from, valid_to, created_at, updated_at
            )
            VALUES ('Theme', 'hbm', 'HBM', ?, '{}', 'active',
                    '2026-06-20T00:00:00+00:00', NULL,
                    '2026-06-20T00:00:00+00:00', '2026-06-20T00:00:00+00:00')
            """,
            (json.dumps(("HBM",)),),
        )
        conn.execute(
            """
            INSERT INTO graph_snapshots (
                build_version, status, source_watermark, node_count, edge_count,
                checksum, activated_at, created_at
            )
            VALUES ('ranking-api-build', 'active', 'seed', 1, 0, 'checksum',
                    '2026-06-20T00:00:00+00:00', '2026-06-20T00:00:00+00:00')
            """
        )
        conn.commit()

    response = TestClient(main.app).get("/api/theme/ranking")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["algorithm_version"] == "theme-ranking-v1"
    assert payload["weights"]["evidence"] == 0.30
    assert payload["themes"][0]["theme_id"] == "hbm"
    assert set(payload["themes"][0]) == {
        "theme_id",
        "theme_name",
        "lifecycle",
        "rank_score",
        "momentum_score",
        "evidence_score",
        "research_score",
        "controller_score",
        "opportunity_score",
        "updated_at",
    }

    with repository._connect() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "theme_ranking" not in tables
    assert "theme_ranking_entries" not in tables
