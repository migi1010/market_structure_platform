from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.equipment_taxonomy import (
    EQUIPMENT_CATEGORIES,
    equipment_key,
    validate_equipment_category,
)


def test_equipment_taxonomy_registers_approved_categories() -> None:
    assert {
        "Lithography", "Etch", "Deposition", "Inspection", "Metrology",
        "Packaging", "Testing", "Assembly", "Material Processing",
        "Optical Equipment", "Thermal Equipment", "Automation Equipment",
        "Manufacturing Equipment", "Infrastructure Equipment",
    } == EQUIPMENT_CATEGORIES
    assert equipment_key("Advanced Etch") == "equipment:advanced_etch"
    assert equipment_key("Optical Testing Equipment") == "equipment:optical_testing_equipment"


def test_unknown_equipment_category_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown equipment category"):
        validate_equipment_category("Imaginary Equipment")
