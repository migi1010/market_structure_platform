from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.research_pipeline.research_pipeline_models import (
    PIPELINE_BOARD_STATUSES,
    PIPELINE_STATUSES,
    PipelineTransitionError,
    validate_transition,
)


def test_pipeline_status_taxonomy_is_ordered_and_board_scoped() -> None:
    assert PIPELINE_STATUSES == (
        "DISCOVERED",
        "OBSERVING",
        "RESEARCHING",
        "VALIDATING",
        "REVIEW_READY",
        "APPROVED_RESEARCH",
        "MONITORING",
        "ARCHIVED",
    )
    assert PIPELINE_BOARD_STATUSES == (
        "DISCOVERED",
        "OBSERVING",
        "RESEARCHING",
        "VALIDATING",
        "REVIEW_READY",
        "MONITORING",
    )


def test_validate_transition_accepts_next_step_and_archive() -> None:
    validate_transition("DISCOVERED", "OBSERVING", linked_types=set(), progress=0, reason="")
    validate_transition("RESEARCHING", "ARCHIVED", linked_types=set(), progress=0, reason="")


def test_validate_transition_rejects_skipped_state() -> None:
    with pytest.raises(PipelineTransitionError):
        validate_transition("DISCOVERED", "VALIDATING", linked_types=set(), progress=0, reason="")


def test_validate_transition_requires_evidence_for_validation() -> None:
    with pytest.raises(PipelineTransitionError):
        validate_transition("RESEARCHING", "VALIDATING", linked_types=set(), progress=0, reason="")
    with pytest.raises(PipelineTransitionError):
        validate_transition("RESEARCHING", "VALIDATING", linked_types={"SCOUT_CANDIDATE"}, progress=0, reason="")
    validate_transition("RESEARCHING", "VALIDATING", linked_types={"THEME"}, progress=20, reason="")


def test_validate_transition_requires_complete_progress_for_review_ready() -> None:
    with pytest.raises(PipelineTransitionError):
        validate_transition("VALIDATING", "REVIEW_READY", linked_types={"THEME"}, progress=80, reason="")
    validate_transition("VALIDATING", "REVIEW_READY", linked_types={"THEME"}, progress=100, reason="")


def test_validate_transition_requires_manual_reason_for_approved_research() -> None:
    with pytest.raises(PipelineTransitionError):
        validate_transition("REVIEW_READY", "APPROVED_RESEARCH", linked_types={"THEME"}, progress=100, reason="")
    validate_transition("REVIEW_READY", "APPROVED_RESEARCH", linked_types={"THEME"}, progress=100, reason="human approved thesis")
