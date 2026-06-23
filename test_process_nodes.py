from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.technology_process_taxonomy import (
    PROCESSES,
    process_key,
    validate_process,
)


def test_process_taxonomy_registers_approved_processes() -> None:
    assert {
        "TSV Etching",
        "Wafer Bonding",
        "Glass Processing",
        "Optical Testing",
        "Yield Inspection",
        "Packaging",
        "Thermal Management",
        "Assembly",
        "Calibration",
        "Qualification",
        "Validation",
    } == PROCESSES
    assert process_key("Wafer Bonding") == "process:wafer_bonding"


def test_unknown_process_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown process"):
        validate_process("Invented Annealing")
