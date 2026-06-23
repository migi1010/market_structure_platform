from __future__ import annotations

import re


EQUIPMENT_CATEGORIES = frozenset({
    "Lithography",
    "Etch",
    "Deposition",
    "Inspection",
    "Metrology",
    "Packaging",
    "Testing",
    "Assembly",
    "Material Processing",
    "Optical Equipment",
    "Thermal Equipment",
    "Automation Equipment",
    "Manufacturing Equipment",
    "Infrastructure Equipment",
})

PROCESS_EQUIPMENT_RELATIONSHIPS = frozenset({
    "PROCESS_REQUIRES_EQUIPMENT",
    "EQUIPMENT_ENABLES_PROCESS",
})


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def validate_equipment_category(category: str) -> str:
    if category not in EQUIPMENT_CATEGORIES:
        raise ValueError(f"Unknown equipment category: {category}")
    return category


def equipment_key(name: str) -> str:
    key = _slug(name)
    if not key:
        raise ValueError("Equipment name is required")
    return f"equipment:{key}"
