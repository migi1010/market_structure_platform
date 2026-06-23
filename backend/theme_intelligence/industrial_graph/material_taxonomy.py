from __future__ import annotations

import re


MATERIAL_CATEGORIES = frozenset({
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
})

PROCESS_MATERIAL_RELATIONSHIPS = frozenset({
    "PROCESS_REQUIRES_MATERIAL",
    "MATERIAL_ENABLES_PROCESS",
})


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def validate_material_category(category: str) -> str:
    if category not in MATERIAL_CATEGORIES:
        raise ValueError(f"Unknown material category: {category}")
    return category


def material_key(name: str) -> str:
    key = _slug(name)
    if not key:
        raise ValueError("Material name is required")
    return f"material:{key}"
