from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.research_pipeline.research_pipeline_engine import ResearchPipelineEngine
from theme_intelligence.research_pipeline.research_pipeline_models import PipelineTransitionError
from theme_intelligence.storage.theme_repository import ThemeRepository


def engine_for(tmp_path: Path) -> ResearchPipelineEngine:
    return ResearchPipelineEngine(ThemeRepository(tmp_path / "pipeline.sqlite3"))


def test_engine_creates_case_with_scout_origin_link(tmp_path: Path) -> None:
    engine = engine_for(tmp_path)
    case = engine.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai-infrastructure-constraint-watch",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    detail = engine.get_case(case.case_id)
    assert detail.case.status == "DISCOVERED"
    assert {link.linked_type for link in detail.links} == {"SCOUT_CANDIDATE"}


def test_engine_rejects_illegal_transition_and_accepts_manual_next_step(tmp_path: Path) -> None:
    engine = engine_for(tmp_path)
    case = engine.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )

    with pytest.raises(PipelineTransitionError):
        engine.transition_case(case.case_id, "VALIDATING", reason="skip")

    updated = engine.transition_case(case.case_id, "OBSERVING", reason="manual observe")
    assert updated.status == "OBSERVING"


def test_engine_calculates_progress_from_artifact_links(tmp_path: Path) -> None:
    engine = engine_for(tmp_path)
    case = engine.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    for linked_type in ("THEME", "SUPPLY_CHAIN_VALIDATION", "CONTROLLER", "OPPORTUNITY", "DECISION_PACKET"):
        engine.link_artifact(case.case_id, linked_type, f"{linked_type.lower()}:1")

    detail = engine.get_case(case.case_id)
    assert detail.progress.percent == 100
    assert detail.progress.sections["theme_narrative"] is True
    assert detail.progress.sections["supply_chain_validation"] is True
    assert detail.progress.sections["controller_review"] is True
    assert detail.progress.sections["opportunity_review"] is True
    assert detail.progress.sections["decision_packet_link"] is True


def test_engine_requires_complete_progress_before_review_ready(tmp_path: Path) -> None:
    engine = engine_for(tmp_path)
    case = engine.create_case(
        source_type="SCOUT_CANDIDATE",
        source_id="candidate:ai",
        theme_id="ai_infrastructure",
        title="AI Infrastructure Constraint Watch",
    )
    engine.link_artifact(case.case_id, "THEME", "ai_infrastructure")
    engine.transition_case(case.case_id, "OBSERVING", reason="manual")
    engine.transition_case(case.case_id, "RESEARCHING", reason="manual")
    engine.transition_case(case.case_id, "VALIDATING", reason="manual")

    with pytest.raises(PipelineTransitionError):
        engine.transition_case(case.case_id, "REVIEW_READY", reason="manual")
