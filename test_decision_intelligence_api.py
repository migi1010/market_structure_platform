from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import main
from theme_intelligence.research_pipeline.research_pipeline_engine import ResearchPipelineEngine
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_decision_intelligence_api_lists_and_details_read_only(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "decision-intelligence.sqlite3"
    repository = ThemeRepository(db_path)
    pipeline = ResearchPipelineEngine(repository)
    case = pipeline.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai-infrastructure-constraint-watch",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    pipeline.link_artifact(case.case_id, "THEME", "ai_infrastructure")
    before = _counts(repository)

    monkeypatch.setattr(main, "ThemeRepository", lambda *_: ThemeRepository(db_path))
    client = TestClient(main.app)

    listed = client.get("/api/decision-intelligence")
    assert listed.status_code == 200
    assert listed.json()["available"] is True
    packet_id = listed.json()["packets"][0]["packet_id"]

    detail = client.get(f"/api/decision-intelligence/{packet_id}")
    assert detail.status_code == 200
    assert detail.json()["packet"]["packet_id"] == packet_id
    assert "buy" not in str(detail.json()).lower()
    assert "target price" not in str(detail.json()).lower()
    assert before == _counts(repository)


def test_decision_intelligence_api_returns_404_for_unknown_packet(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "decision-intelligence.sqlite3"
    monkeypatch.setattr(main, "ThemeRepository", lambda *_: ThemeRepository(db_path))
    client = TestClient(main.app)

    response = client.get("/api/decision-intelligence/decision-intelligence:missing")

    assert response.status_code == 404


def _counts(repository: ThemeRepository) -> dict[str, int]:
    repository.initialize()
    with repository._connect() as conn:
        return {
            row["name"]: int(conn.execute(f"SELECT COUNT(*) AS count FROM {row['name']}").fetchone()["count"])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        }
