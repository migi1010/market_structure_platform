from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from theme_intelligence.models import clamp_score, utc_now_iso


BOTTLENECK_TYPES: tuple[str, ...] = (
    "Capacity Constraint",
    "Yield Constraint",
    "Material Constraint",
    "Equipment Constraint",
    "Talent Constraint",
    "Infrastructure Constraint",
    "Supply Chain Constraint",
    "Regulatory Constraint",
)

BOTTLENECK_TIMELINE_STATUSES: tuple[str, ...] = ("past", "current", "future")
SUPPLY_CHAIN_CONTROLLER_ROLES: tuple[str, ...] = (
    "controller",
    "equipment_supplier",
    "material_supplier",
    "capacity_owner",
    "resolution_enabler",
)


@dataclass(frozen=True)
class BottleneckRecord:
    theme_name: str
    bottleneck_name: str
    bottleneck_type: str
    severity_score: float
    duration_score: float
    resolution_probability: float
    impact_score: float
    bottleneck_strength: float
    controller_entities: list[dict[str, Any]] = field(default_factory=list)
    beneficiaries: list[dict[str, Any]] = field(default_factory=list)
    timeline_status: str = "current"
    description: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity_score", clamp_score(self.severity_score))
        object.__setattr__(self, "duration_score", clamp_score(self.duration_score))
        object.__setattr__(self, "resolution_probability", clamp_score(self.resolution_probability))
        object.__setattr__(self, "impact_score", clamp_score(self.impact_score))
        object.__setattr__(self, "bottleneck_strength", clamp_score(self.bottleneck_strength))
        status = self.timeline_status if self.timeline_status in BOTTLENECK_TIMELINE_STATUSES else "current"
        object.__setattr__(self, "timeline_status", status)
        object.__setattr__(self, "updated_at", self.updated_at or utc_now_iso())

    def with_updates(self, **updates: Any) -> "BottleneckRecord":
        return replace(self, **updates)

    def to_api(self) -> dict[str, Any]:
        return {
            "name": self.bottleneck_name,
            "type": self.bottleneck_type,
            "severity_score": clamp_score(self.severity_score),
            "duration_score": clamp_score(self.duration_score),
            "resolution_probability": clamp_score(self.resolution_probability),
            "impact_score": clamp_score(self.impact_score),
            "bottleneck_strength": clamp_score(self.bottleneck_strength),
            "timeline_status": self.timeline_status,
            "description": self.description,
            "controllers": self.controller_entities,
            "beneficiaries": self.beneficiaries,
            "what_fixes_it": what_fixes_bottleneck(self.bottleneck_type),
            "what_to_monitor": monitor_triggers(self.bottleneck_type),
        }


def what_fixes_bottleneck(bottleneck_type: str) -> list[str]:
    return {
        "Capacity Constraint": ["Capacity expansion", "New supplier qualification"],
        "Yield Constraint": ["Yield improvement", "Process maturity", "Inspection feedback loops"],
        "Material Constraint": ["Material qualification", "Supplier diversification"],
        "Equipment Constraint": ["Equipment supply expansion", "Tool qualification"],
        "Talent Constraint": ["Hiring and training", "Automation of scarce workflows"],
        "Infrastructure Constraint": ["Power and cooling expansion", "Datacenter availability"],
        "Supply Chain Constraint": ["Second sourcing", "Geographic diversification"],
        "Regulatory Constraint": ["Policy clarity", "Export license approvals"],
    }.get(bottleneck_type, ["Evidence of constraint relief"])


def monitor_triggers(bottleneck_type: str) -> list[str]:
    return {
        "Capacity Constraint": ["Capacity additions", "Lead time normalization", "Supplier utilization"],
        "Yield Constraint": ["Yield improvement", "Scrap reduction", "Qualification milestones"],
        "Material Constraint": ["Material availability", "Pricing pressure", "New supplier certification"],
        "Equipment Constraint": ["Tool shipments", "Backlog changes", "Inspection capacity"],
        "Talent Constraint": ["Hiring plans", "Engineering productivity", "Automation adoption"],
        "Infrastructure Constraint": ["Power availability", "Cooling capacity", "Datacenter buildout"],
        "Supply Chain Constraint": ["Supplier concentration", "Geographic concentration", "Second-source wins"],
        "Regulatory Constraint": ["Export controls", "Subsidy decisions", "Licensing changes"],
    }.get(bottleneck_type, ["Constraint evidence"])
