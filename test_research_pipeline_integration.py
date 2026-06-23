from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.research_pipeline.research_pipeline_engine import ResearchPipelineEngine
from theme_intelligence.storage.theme_repository import ThemeRepository


DOWNSTREAM_TABLES = (
    "graph_snapshots",
    "controller_snapshots",
    "opportunity_snapshots",
    "decision_packets",
)


def downstream_counts(repository: ThemeRepository) -> dict[str, int]:
    repository.initialize()
    with repository._connect() as conn:
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in DOWNSTREAM_TABLES
        }


def test_research_pipeline_case_creation_does_not_mutate_downstream_tables(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "pipeline.sqlite3")
    before = downstream_counts(repository)
    engine = ResearchPipelineEngine(repository)

    case = engine.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai-infrastructure-constraint-watch",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    engine.link_artifact(case.case_id, "THEME", "ai_infrastructure")
    engine.transition_case(case.case_id, "OBSERVING", reason="manual observe")

    assert downstream_counts(repository) == before
