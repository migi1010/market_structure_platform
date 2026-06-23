from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.material_taxonomy import (
    MATERIAL_CATEGORIES,
    material_key,
    validate_material_category,
)


def test_material_taxonomy_registers_approved_categories() -> None:
    assert {
        "Raw Material",
        "Chemical",
        "Substrate",
        "Packaging Material",
        "Optical Material",
        "Thermal Material",
        "Semiconductor Material",
        "Metal",
        "Specialty Chemical",
        "Adhesive",
        "Coating",
        "Encapsulation Material",
        "Advanced Material",
    } == MATERIAL_CATEGORIES
    assert material_key("Ultra Thin Glass") == "material:ultra_thin_glass"
    assert material_key("Thermal Interface Material") == "material:thermal_interface_material"


def test_unknown_material_category_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown material category"):
        validate_material_category("Imaginary Material")
