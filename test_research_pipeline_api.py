from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import main
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_pipeline_api_create_list_detail_and_transition(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "pipeline.sqlite3"
    monkeypatch.setattr(main, "ThemeRepository", lambda *_: ThemeRepository(db_path))
    client = TestClient(main.app)

    created = client.post(
        "/api/research/pipeline",
        json={
            "source_type": "SCOUT_CANDIDATE",
            "source_id": "candidate:ai-infrastructure-constraint-watch",
            "theme_id": "ai_infrastructure",
            "title": "AI Infrastructure Constraint Watch",
        },
    )
    assert created.status_code == 200
    case_id = created.json()["case"]["case_id"]

    listed = client.get("/api/research/pipeline")
    assert listed.status_code == 200
    assert listed.json()["cases"][0]["case_id"] == case_id
    assert listed.json()["cases"][0]["progress"]["percent"] == 0

    detail = client.get(f"/api/research/pipeline/{case_id}")
    assert detail.status_code == 200
    assert detail.json()["case"]["status"] == "DISCOVERED"
    assert detail.json()["timeline"][0]["new_status"] == "DISCOVERED"

    transitioned = client.post(
        f"/api/research/pipeline/{case_id}/transition",
        json={"new_status": "OBSERVING", "reason": "manual observe"},
    )
    assert transitioned.status_code == 200
    assert transitioned.json()["case"]["status"] == "OBSERVING"


def test_pipeline_api_rejects_illegal_transition(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "pipeline.sqlite3"
    monkeypatch.setattr(main, "ThemeRepository", lambda *_: ThemeRepository(db_path))
    client = TestClient(main.app)

    case_id = client.post(
        "/api/research/pipeline",
        json={
            "source_type": "SCOUT_CANDIDATE",
            "source_id": "candidate:ai",
            "theme_id": "ai_infrastructure",
            "title": "AI Infrastructure Constraint Watch",
        },
    ).json()["case"]["case_id"]
    response = client.post(
        f"/api/research/pipeline/{case_id}/transition",
        json={"new_status": "VALIDATING", "reason": "skip"},
    )
    assert response.status_code == 400


def test_pipeline_api_links_artifact_and_updates_progress(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "pipeline.sqlite3"
    monkeypatch.setattr(main, "ThemeRepository", lambda *_: ThemeRepository(db_path))
    client = TestClient(main.app)

    case_id = client.post(
        "/api/research/pipeline",
        json={
            "source_type": "SCOUT_CANDIDATE",
            "source_id": "candidate:ai",
            "theme_id": "ai_infrastructure",
            "title": "AI Infrastructure Constraint Watch",
        },
    ).json()["case"]["case_id"]
    linked = client.post(
        f"/api/research/pipeline/{case_id}/links",
        json={"linked_type": "THEME", "linked_id": "ai_infrastructure"},
    )
    assert linked.status_code == 200
    assert linked.json()["progress"]["percent"] == 20
    assert [row["linked_type"] for row in linked.json()["links"]] == ["SCOUT_CANDIDATE", "THEME"]
