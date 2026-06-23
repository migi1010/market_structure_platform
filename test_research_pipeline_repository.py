from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.research_pipeline.research_pipeline_repository import ResearchPipelineRepository
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_initialize_creates_research_pipeline_tables(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "pipeline.sqlite3")
    repository.initialize()
    with repository._connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {
        "research_pipeline_cases",
        "research_pipeline_events",
        "research_pipeline_links",
    } <= tables


def test_repository_creates_case_event_and_lineage(tmp_path: Path) -> None:
    repository = ResearchPipelineRepository(ThemeRepository(tmp_path / "pipeline.sqlite3"))
    case = repository.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai-infrastructure-constraint-watch",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )

    detail = repository.get_case(case.case_id)
    assert detail is not None
    assert detail.case.case_id == case.case_id
    assert detail.case.status == "DISCOVERED"
    assert detail.case.lineage_checksum
    assert len(detail.events) == 1
    assert detail.events[0].previous_status is None
    assert detail.events[0].new_status == "DISCOVERED"


def test_repository_links_artifacts_and_keeps_unique_link_identity(tmp_path: Path) -> None:
    repository = ResearchPipelineRepository(ThemeRepository(tmp_path / "pipeline.sqlite3"))
    case = repository.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    first = repository.link_artifact(case.case_id, "THEME", "ai_infrastructure")
    second = repository.link_artifact(case.case_id, "THEME", "ai_infrastructure")

    detail = repository.get_case(case.case_id)
    assert first.link_id == second.link_id
    assert detail is not None
    assert [link.linked_type for link in detail.links] == ["SCOUT_CANDIDATE", "THEME"]


def test_repository_case_creation_is_idempotent_by_source(tmp_path: Path) -> None:
    repository = ResearchPipelineRepository(ThemeRepository(tmp_path / "pipeline.sqlite3"))
    first = repository.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    second = repository.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    assert first.case_id == second.case_id
