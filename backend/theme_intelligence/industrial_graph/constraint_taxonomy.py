from __future__ import annotations

import re


CONSTRAINT_CATEGORIES = frozenset({
    "Yield Constraint",
    "Capacity Constraint",
    "Material Constraint",
    "Equipment Constraint",
    "Process Constraint",
    "Qualification Constraint",
    "Regulatory Constraint",
    "Infrastructure Constraint",
    "Power Constraint",
    "Supply Chain Constraint",
    "Customer Adoption Constraint",
    "Cost Constraint",
    "Testing Constraint",
    "Thermal Constraint",
})


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def validate_constraint_category(category: str) -> str:
    if category not in CONSTRAINT_CATEGORIES:
        raise ValueError(f"Unknown constraint category: {category}")
    return category


def constraint_key(name: str) -> str:
    key = _slug(name)
    for suffix in ("_constraint", "_bottleneck"):
        if key.endswith(suffix):
            key = key[: -len(suffix)]
            break
    if not key:
        raise ValueError("Constraint name is required")
    return f"constraint:{key}"


def persisted_constraint_name(theme_name: str, constraint_name: str) -> str:
    theme_slug = _slug(theme_name)
    name_slug = _slug(constraint_name)
    if theme_slug and (name_slug == theme_slug or name_slug.startswith(f"{theme_slug}_")):
        return constraint_name
    return f"{theme_name} {constraint_name}".strip()
