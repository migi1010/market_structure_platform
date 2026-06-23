from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from .graph_models import NodeKey, canonical_json, normalize_canonical_key


POSITIVE_CONTROLLER_RELATIONSHIPS = frozenset({
    "EQUIPMENT_PRODUCED_BY", "MATERIAL_SUPPLIED_BY",
    "CONSTRAINT_RESOLVED_BY_COMPANY", "PROCESS_RESOLVED_BY_COMPANY",
    "EQUIPMENT_RESOLVED_BY", "MATERIAL_RESOLVED_BY",
    "SUPPLIES", "CUSTOMER_OF", "DEPENDS_ON", "USES_SUPPLIER",
})
EXCLUDED_CONTROLLER_RELATIONSHIPS = frozenset({
    "CONTROLS", "ENABLES", "COMPANY_EXPOSED_TO_CONSTRAINT",
})
DEPENDENCY_PROPAGATION_RELATIONSHIPS = frozenset({
    "USES_TECHNOLOGY", "REQUIRES_PROCESS", "TECHNOLOGY_ENABLES_PROCESS",
    "PROCESS_PRECEDES_PROCESS", "PROCESS_DEPENDS_ON_PROCESS",
    "PROCESS_REQUIRES_MATERIAL", "MATERIAL_ENABLES_PROCESS",
    "PROCESS_REQUIRES_EQUIPMENT", "EQUIPMENT_ENABLES_PROCESS",
    "THEME_DEPENDS_ON_MATERIAL", "THEME_DEPENDS_ON_EQUIPMENT",
    "THEME_LIMITED_BY_CONSTRAINT", "TECHNOLOGY_LIMITED_BY_CONSTRAINT",
    "PROCESS_LIMITED_BY_CONSTRAINT", "MATERIAL_LIMITED_BY_CONSTRAINT",
    "EQUIPMENT_LIMITED_BY_CONSTRAINT", "CONSTRAINT_DEPENDS_ON_MATERIAL",
    "CONSTRAINT_DEPENDS_ON_EQUIPMENT", "CONSTRAINT_DEPENDS_ON_PROCESS",
})
CONTROLLER_TYPE_ORDER = (
    "Technology Controller", "Process Controller", "Material Controller",
    "Equipment Controller", "Capacity Controller", "Constraint Controller",
    "Supply Chain Controller",
)


def _score(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return value


def _company_key(value: NodeKey) -> NodeKey:
    if value[0] != "Company":
        raise ValueError("controller metric endpoint must be Company")
    return "Company", normalize_canonical_key(value[1], node_type="Company")


@dataclass(frozen=True)
class ControllerMetric:
    company_key: NodeKey
    metric_name: str
    raw_value: float
    normalized_value: float
    coverage: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "company_key", _company_key(self.company_key))
        if not self.metric_name.strip() or not math.isfinite(float(self.raw_value)):
            raise ValueError("metric name and finite raw value are required")
        object.__setattr__(self, "normalized_value", _score(self.normalized_value, "normalized_value"))
        object.__setattr__(self, "coverage", _score(self.coverage, "coverage"))
        object.__setattr__(self, "metadata", dict(sorted(dict(self.metadata).items())))

    @property
    def identity_key(self) -> tuple[NodeKey, str]:
        return self.company_key, self.metric_name


@dataclass(frozen=True)
class ControllerIntelligence:
    company_key: NodeKey
    company_name: str
    controller_types: tuple[str, ...]
    dependency_score: float
    controller_score: float
    base_score: float
    constraint_influence: float
    material_control: float
    equipment_control: float
    process_control: float
    technology_control: float
    resolution_influence: float
    supply_chain_influence: float
    coverage: float
    coverage_confidence: float
    evidence_ids: tuple[int, ...]
    reasoning_paths: tuple[tuple[NodeKey, ...], ...]
    rank: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "company_key", _company_key(self.company_key))
        if not self.company_name.strip():
            raise ValueError("company name is required")
        types = tuple(sorted(set(self.controller_types), key=CONTROLLER_TYPE_ORDER.index))
        if types != self.controller_types:
            raise ValueError("controller types must be unique and deterministically ordered")
        for field_name in (
            "dependency_score", "controller_score", "base_score",
            "constraint_influence", "material_control", "equipment_control",
            "process_control", "technology_control", "resolution_influence",
            "supply_chain_influence", "coverage", "coverage_confidence",
        ):
            object.__setattr__(self, field_name, _score(getattr(self, field_name), field_name))
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(int(item) for item in self.evidence_ids))))
        object.__setattr__(self, "reasoning_paths", tuple(sorted(set(self.reasoning_paths))))
        if self.rank < 0:
            raise ValueError("rank cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_key": list(self.company_key),
            "company_name": self.company_name,
            "controller_types": list(self.controller_types),
            "dependency_score": self.dependency_score,
            "controller_score": self.controller_score,
            "base_score": self.base_score,
            "constraint_influence": self.constraint_influence,
            "material_control": self.material_control,
            "equipment_control": self.equipment_control,
            "process_control": self.process_control,
            "technology_control": self.technology_control,
            "resolution_influence": self.resolution_influence,
            "supply_chain_influence": self.supply_chain_influence,
            "coverage": self.coverage,
            "coverage_confidence": self.coverage_confidence,
            "evidence_ids": list(self.evidence_ids),
            "reasoning_paths": [[list(node) for node in path] for path in self.reasoning_paths],
            "rank": self.rank,
        }


@dataclass(frozen=True)
class ControllerBuild:
    graph_snapshot_id: int
    graph_build_version: str
    algorithm_version: str
    metrics: tuple[ControllerMetric, ...]
    controllers: tuple[ControllerIntelligence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", tuple(sorted(self.metrics, key=lambda row: row.identity_key)))
        object.__setattr__(self, "controllers", tuple(sorted(self.controllers, key=lambda row: (row.rank, row.company_key))))


@dataclass(frozen=True)
class ControllerSnapshot:
    controller_version: str
    graph_snapshot_id: int
    graph_build_version: str
    algorithm_version: str
    status: str
    checksum: str
    company_count: int
    metric_count: int
    activated_at: str | None = None
    created_at: str = ""
    id: int | None = None


def controller_build_checksum(build: ControllerBuild) -> str:
    payload = {
        "graph_snapshot_id": build.graph_snapshot_id,
        "graph_build_version": build.graph_build_version,
        "algorithm_version": build.algorithm_version,
        "metrics": [
            {
                "company_key": row.company_key, "metric_name": row.metric_name,
                "raw_value": row.raw_value, "normalized_value": row.normalized_value,
                "coverage": row.coverage, "metadata": dict(row.metadata),
            }
            for row in build.metrics
        ],
        "controllers": [row.to_dict() for row in build.controllers],
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
