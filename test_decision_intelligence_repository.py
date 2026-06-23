from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.decision_intelligence_repository import DecisionIntelligenceRepository
from theme_intelligence.research_pipeline.research_pipeline_engine import ResearchPipelineEngine
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_repository_is_read_only_and_lists_pipeline_cases(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "decision-intelligence.sqlite3")
    pipeline = ResearchPipelineEngine(repository)
    case = pipeline.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai-infrastructure-constraint-watch",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    pipeline.link_artifact(case.case_id, "THEME", "ai_infrastructure")

    before_counts = DecisionIntelligenceRepository(repository).source_table_counts()
    cases = DecisionIntelligenceRepository(repository).list_research_cases()
    after_counts = DecisionIntelligenceRepository(repository).source_table_counts()

    assert cases[0].case.case_id == case.case_id
    assert before_counts == after_counts
    assert not any(name.startswith("decision_intelligence") for name in before_counts)
