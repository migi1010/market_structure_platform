from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.constraint_taxonomy import (
    CONSTRAINT_CATEGORIES,
    constraint_key,
    validate_constraint_category,
)


def test_constraint_taxonomy_registers_approved_categories() -> None:
    assert {
        "Yield Constraint", "Capacity Constraint", "Material Constraint",
        "Equipment Constraint", "Process Constraint", "Qualification Constraint",
        "Regulatory Constraint", "Infrastructure Constraint", "Power Constraint",
        "Supply Chain Constraint", "Customer Adoption Constraint", "Cost Constraint",
        "Testing Constraint", "Thermal Constraint",
    } == CONSTRAINT_CATEGORIES
    assert constraint_key("HBM Capacity Constraint") == "constraint:hbm_capacity"
    assert constraint_key("Glass Substrate Yield") == "constraint:glass_substrate_yield"


def test_unknown_constraint_category_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown constraint category"):
        validate_constraint_category("Talent Constraint")
