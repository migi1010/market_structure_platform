from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.decision_intelligence_engine import DecisionIntelligenceEngine
from theme_intelligence.research_pipeline.research_pipeline_engine import ResearchPipelineEngine
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_lineage_preserves_pipeline_and_artifact_references(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "decision-intelligence.sqlite3")
    pipeline = ResearchPipelineEngine(repository)
    case = pipeline.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:constraint-watch",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    for linked_type, linked_id in (
        ("THEME", "ai_infrastructure"),
        ("GRAPH_SNAPSHOT", "42"),
        ("CONTROLLER", "controller-42"),
        ("OPPORTUNITY", "opportunity-42"),
        ("DECISION_PACKET", "packet-family-42"),
    ):
        pipeline.link_artifact(case.case_id, linked_type, linked_id)

    lineage = DecisionIntelligenceEngine(repository).build_packet(case.case_id).lineage.to_dict()

    assert lineage["scout_candidate_id"] == "candidate:constraint-watch"
    assert lineage["research_case_id"] == case.case_id
    assert lineage["theme_id"] == "ai_infrastructure"
    assert lineage["graph_snapshot_id"] == 42
    assert lineage["controller_snapshot_id"] == "controller-42"
    assert lineage["opportunity_snapshot_id"] == "opportunity-42"
    assert lineage["decision_packet_family_version"] == "packet-family-42"
