from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.models import LIFECYCLE_STAGES, clamp_score, expected_next_stage, validate_lifecycle_stage


def test_lifecycle_stage_ordering() -> None:
    assert LIFECYCLE_STAGES == ("Seed", "Early", "Growth", "Expansion", "Mature")


def test_lifecycle_confidence_bounds() -> None:
    assert clamp_score(-20) == 0
    assert clamp_score(87) == 87
    assert clamp_score(140) == 100


def test_expected_next_stage_logic() -> None:
    assert expected_next_stage("Seed") == "Early"
    assert expected_next_stage("Early") == "Growth"
    assert expected_next_stage("Growth") == "Expansion"
    assert expected_next_stage("Expansion") == "Mature"
    assert expected_next_stage("Mature") == "Mature"


def test_lifecycle_stage_validation() -> None:
    assert validate_lifecycle_stage("early") == "Early"
    assert validate_lifecycle_stage("unknown") == "Seed"
