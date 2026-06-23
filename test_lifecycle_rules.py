from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.lifecycle.lifecycle_models import LifecycleInput
from theme_intelligence.lifecycle.lifecycle_rules import classify_stage, compute_expected_next_stage


def _input(**overrides) -> LifecycleInput:
    base = {
        "theme_name": "Test Theme",
        "discovery_score": 40,
        "emerging_score": 30,
        "catalyst_score": 20,
        "entity_strength_score": 20,
        "confidence_score": 35,
        "crowding_proxy": 10,
        "final_ai_score": 35,
        "key_catalysts": [],
        "beneficiaries": [],
        "source_count": 1,
        "history": [],
    }
    base.update(overrides)
    return LifecycleInput(**base)


def test_lifecycle_stage_rules() -> None:
    assert classify_stage(_input()).stage == "Seed"
    assert classify_stage(_input(emerging_score=68, catalyst_score=52, entity_strength_score=45, confidence_score=62, crowding_proxy=20, final_ai_score=66)).stage == "Early"
    assert classify_stage(_input(emerging_score=72, catalyst_score=64, entity_strength_score=62, confidence_score=68, crowding_proxy=34, final_ai_score=72)).stage == "Growth"
    assert classify_stage(_input(discovery_score=82, emerging_score=66, catalyst_score=70, entity_strength_score=76, confidence_score=76, crowding_proxy=55, final_ai_score=82)).stage == "Expansion"
    assert classify_stage(_input(emerging_score=38, catalyst_score=58, entity_strength_score=82, confidence_score=78, crowding_proxy=78, final_ai_score=72)).stage == "Mature"


def test_expected_next_stage() -> None:
    assert compute_expected_next_stage("Seed", deteriorating=False) == "Early"
    assert compute_expected_next_stage("Early", deteriorating=False) == "Growth"
    assert compute_expected_next_stage("Growth", deteriorating=False) == "Expansion"
    assert compute_expected_next_stage("Expansion", deteriorating=False) == "Mature"
    assert compute_expected_next_stage("Mature", deteriorating=False) == "Mature"
    assert compute_expected_next_stage("Growth", deteriorating=True) == "Growth"
    assert compute_expected_next_stage("Expansion", deteriorating=True) == "Expansion"
