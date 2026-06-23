from __future__ import annotations

import re


TECHNOLOGIES = frozenset({
    "Glass Core Technology",
    "Panel Level Packaging",
    "TSV",
    "Advanced Packaging",
    "3D Memory Stacking",
    "Co-Packaged Optics",
    "Optical Interconnect",
    "Direct Liquid Cooling",
    "Immersion Cooling",
    "Machine Vision",
    "Motion Control",
    "On-Device Inference",
    "Model Compression",
})

PROCESSES = frozenset({
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
})

TECHNOLOGY_PROCESS_RELATIONSHIPS = frozenset({
    "REQUIRES_PROCESS",
    "TECHNOLOGY_ENABLES_PROCESS",
})

PROCESS_DEPENDENCY_RELATIONSHIPS = frozenset({
    "PROCESS_PRECEDES_PROCESS",
    "PROCESS_DEPENDS_ON_PROCESS",
})


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def validate_technology(name: str) -> str:
    if name not in TECHNOLOGIES:
        raise ValueError(f"Unknown technology: {name}")
    return name


def validate_process(name: str) -> str:
    if name not in PROCESSES:
        raise ValueError(f"Unknown process: {name}")
    return name


def technology_key(name: str) -> str:
    return f"technology:{_slug(validate_technology(name))}"


def process_key(name: str) -> str:
    return f"process:{_slug(validate_process(name))}"
