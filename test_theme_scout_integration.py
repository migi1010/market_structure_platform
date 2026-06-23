from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import main
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_scout_list_returns_truthful_unavailable_state(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "empty.sqlite3"
    monkeypatch.setattr(main, "ThemeRepository", lambda *_: ThemeRepository(db_path))
    response = TestClient(main.app).get("/api/theme/scout")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert payload["candidates"] == []


def test_scout_detail_unknown_candidate_is_404(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "empty.sqlite3"
    monkeypatch.setattr(main, "ThemeRepository", lambda *_: ThemeRepository(db_path))
    response = TestClient(main.app).get("/api/theme/scout/candidate:missing")
    assert response.status_code == 404
