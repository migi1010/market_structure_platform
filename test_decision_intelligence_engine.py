from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.decision_intelligence_engine import DecisionIntelligenceEngine
from theme_intelligence.research_pipeline.research_pipeline_engine import ResearchPipelineEngine
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_engine_builds_required_sections_from_completed_research_state(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "decision-intelligence.sqlite3")
    pipeline = ResearchPipelineEngine(repository)
    case = pipeline.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai-infrastructure-constraint-watch",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    for linked_type, linked_id in (
        ("THEME", "ai_infrastructure"),
        ("GRAPH_SNAPSHOT", "1"),
        ("CONTROLLER", "controller-v1"),
        ("OPPORTUNITY", "opportunity-v1"),
        ("DECISION_PACKET", "packet-v1"),
    ):
        pipeline.link_artifact(case.case_id, linked_type, linked_id)

    packet = DecisionIntelligenceEngine(repository).build_packet(case.case_id)

    assert packet.packet_id == f"decision-intelligence:{case.case_id}"
    assert packet.lineage.research_case_id == case.case_id
    assert packet.lineage.scout_candidate_id == "candidate:ai-infrastructure-constraint-watch"
    assert packet.to_dict()["answers"]["currently_known"]
    assert packet.to_dict()["answers"]["still_unknown"]
    assert packet.to_dict()["answers"]["supporting_evidence"]
    assert packet.to_dict()["answers"]["invalidation_conditions"]
    assert set(packet.to_dict()["sections"]) == {
        "summary",
        "bull_case",
        "bear_case",
        "evidence_strength",
        "research_gaps",
        "monitoring_triggers",
        "scenario_matrix",
        "open_questions",
        "lineage",
    }


def test_engine_is_deterministic_and_missing_evidence_becomes_gap(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "decision-intelligence.sqlite3")
    pipeline = ResearchPipelineEngine(repository)
    case = pipeline.create_case(
        source_type="THEME",
        source_id="theme:hbm",
        theme_id="hbm",
        title="HBM Research",
    )

    engine = DecisionIntelligenceEngine(repository)
    first = engine.build_packet(case.case_id).to_dict()
    second = engine.build_packet(case.case_id).to_dict()

    assert first == second
    assert any("missing" in str(row).lower() or "incomplete" in str(row).lower() for row in first["sections"]["research_gaps"])
    assert not str(first).lower().count("target price")
