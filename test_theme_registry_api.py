from __future__ import annotations

import json
import sys
from pathlib import Path
from dataclasses import replace

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import main
from settings import get_settings


def test_theme_registry_api_returns_projection_only_contract(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "registry-api.sqlite3"
    settings = get_settings()
    monkeypatch.setattr(main, "settings", replace(settings, sqlite_cache_path=db_path))

    from theme_intelligence.storage.theme_repository import ThemeRepository

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
            (json.dumps(("High Bandwidth Memory",)),),
        )
        conn.execute(
            """
            INSERT INTO graph_snapshots (
                build_version, status, source_watermark, node_count, edge_count,
                checksum, activated_at, created_at
            )
            VALUES ('registry-api-build', 'active', 'seed', 1, 0, 'checksum',
                    '2026-06-20T00:00:00+00:00', '2026-06-20T00:00:00+00:00')
            """
        )
        conn.commit()

    response = TestClient(main.app).get("/api/theme/registry")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["themes"][0]["theme_id"] == "hbm"
    assert payload["themes"][0]["theme_type"] == "INDUSTRIAL"

    with repository._connect() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "theme_registry" not in tables
    assert "theme_registry_entries" not in tables
