from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.controller_models import (
    ControllerIntelligence,
    ControllerMetric,
)


def test_controller_metric_rejects_negative_normalized_value() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        ControllerMetric(
            company_key=("Company", "company:KLAC"),
            metric_name="equipment_control",
            raw_value=1.0,
            normalized_value=-1.0,
            coverage=100.0,
        )


def test_controller_intelligence_serializes_transparent_components() -> None:
    row = ControllerIntelligence(
        company_key=("Company", "company:KLAC"),
        company_name="KLA",
        controller_types=("Equipment Controller", "Constraint Controller"),
        dependency_score=25.0,
        controller_score=30.0,
        base_score=32.0,
        constraint_influence=40.0,
        material_control=0.0,
        equipment_control=50.0,
        process_control=20.0,
        technology_control=0.0,
        resolution_influence=30.0,
        supply_chain_influence=0.0,
        coverage=50.0,
        coverage_confidence=80.0,
        evidence_ids=(1, 2),
        reasoning_paths=((("Company", "company:KLAC"), ("Equipment", "equipment:yield_inspection")),),
    )
    assert row.to_dict()["evidence_ids"] == [1, 2]
    assert row.to_dict()["base_score"] == 32.0
