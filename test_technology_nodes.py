from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.technology_process_taxonomy import (
    TECHNOLOGIES,
    technology_key,
    validate_technology,
)


def test_technology_taxonomy_registers_approved_technologies() -> None:
    assert {
        "Glass Core Technology",
        "Panel Level Packaging",
        "TSV",
        "3D Memory Stacking",
        "Co-Packaged Optics",
        "Optical Interconnect",
        "Direct Liquid Cooling",
        "Immersion Cooling",
        "Machine Vision",
        "Motion Control",
        "On-Device Inference",
        "Model Compression",
    } <= TECHNOLOGIES
    assert technology_key("TSV") == "technology:tsv"
    assert technology_key("Co-Packaged Optics") == "technology:co_packaged_optics"


def test_unknown_technology_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown technology"):
        validate_technology("Invented Lithography")
