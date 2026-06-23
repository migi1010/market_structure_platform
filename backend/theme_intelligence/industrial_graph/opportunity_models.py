from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from .graph_models import NodeKey, canonical_json, normalize_canonical_key


OPPORTUNITY_WEIGHTS = {
    "controller_component": 0.25,
    "constraint_component": 0.20,
    "dependency_component": 0.15,
    "resolution_component": 0.15,
    "criticality_component": 0.10,
    "market_attention_component": 0.05,
    "valuation_component": 0.05,
    "bubble_risk_component": 0.05,
}
OPPORTUNITY_TYPE_ORDER = (
    "Technology Opportunity",
    "Process Opportunity",
    "Material Opportunity",
    "Equipment Opportunity",
    "Capacity Opportunity",
    "Constraint Opportunity",
    "Supply Chain Opportunity",
    "Hybrid Opportunity",
)
MARKET_COMPONENT_NAMES = frozenset({
    "market_attention_component",
    "valuation_component",
    "bubble_risk_component",
})


def _score(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return value


def _company_key(value: NodeKey) -> NodeKey:
    if value[0] != "Company":
        raise ValueError("opportunity endpoint must be Company")
    return "Company", normalize_canonical_key(value[1], node_type="Company")


@dataclass(frozen=True)
class MarketSourceRecord:
    source_table: str
    source_record_key: Mapping[str, str]
    source_timestamp: str
    source_value: float
    availability_state: str = "available"

    def __post_init__(self) -> None:
        if not self.source_table.strip() or not self.source_timestamp.strip():
            raise ValueError("source table and timestamp are required")
        value = float(self.source_value)
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("source value must be between 0 and 100")
        if self.availability_state != "available":
            raise ValueError("admitted source records must be available")
        object.__setattr__(
            self,
            "source_record_key",
            dict(sorted((str(key), str(value)) for key, value in self.source_record_key.items())),
        )
        object.__setattr__(self, "source_value", value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_table": self.source_table,
            "source_record_key": dict(self.source_record_key),
            "source_timestamp": self.source_timestamp,
            "source_value": self.source_value,
            "availability_state": self.availability_state,
        }


@dataclass(frozen=True)
class MarketComponent:
    name: str
    raw_value: float | None
    normalized_value: float | None
    availability_state: str
    configured_weight: float
    applied_weight: float
    source_records: tuple[MarketSourceRecord, ...] = ()
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if self.name not in MARKET_COMPONENT_NAMES:
            raise ValueError(f"unknown market component: {self.name}")
        if self.availability_state not in {"available", "unavailable"}:
            raise ValueError("invalid availability state")
        if not 0 <= float(self.configured_weight) <= 1:
            raise ValueError("configured weight must be between 0 and 1")
        if not 0 <= float(self.applied_weight) <= 1:
            raise ValueError("applied weight must be between 0 and 1")
        records = tuple(sorted(
            self.source_records,
            key=lambda row: (
                row.source_table,
                tuple(row.source_record_key.items()),
                row.source_timestamp,
                row.source_value,
            ),
        ))
        object.__setattr__(self, "source_records", records)
        if self.availability_state == "unavailable":
            if self.raw_value is not None or self.normalized_value is not None or self.applied_weight != 0:
                raise ValueError("unavailable market component cannot have a favorable value")
            if records:
                raise ValueError("unavailable market component cannot admit source records")
            if not self.unavailable_reason:
                raise ValueError("unavailable market component requires a reason")
            return
        if self.raw_value is None or self.normalized_value is None:
            raise ValueError("available market component requires values")
        object.__setattr__(self, "raw_value", _score(self.raw_value, "raw_value"))
        object.__setattr__(
            self, "normalized_value", _score(self.normalized_value, "normalized_value")
        )
        if not records:
            raise ValueError("available market component requires source records")
        if self.unavailable_reason is not None:
            raise ValueError("available market component cannot have unavailable reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "availability_state": self.availability_state,
            "configured_weight": self.configured_weight,
            "applied_weight": self.applied_weight,
            "source_records": [row.to_dict() for row in self.source_records],
            "unavailable_reason": self.unavailable_reason,
        }


@dataclass(frozen=True)
class OpportunityIntelligence:
    company_key: NodeKey
    company_name: str
    opportunity_types: tuple[str, ...]
    controller_component: float
    constraint_component: float
    dependency_component: float
    resolution_component: float
    criticality_component: float
    market_attention: MarketComponent
    valuation: MarketComponent
    bubble_risk: MarketComponent
    coverage_component: float
    coverage_confidence: float
    base_score: float
    opportunity_score: float
    configured_weights: Mapping[str, float]
    applied_weights: Mapping[str, float]
    evidence_ids: tuple[int, ...]
    reasoning_paths: tuple[tuple[NodeKey, ...], ...]
    rank: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "company_key", _company_key(self.company_key))
        if not self.company_name.strip():
            raise ValueError("company name is required")
        types = tuple(
            sorted(set(self.opportunity_types), key=OPPORTUNITY_TYPE_ORDER.index)
        )
        if types != self.opportunity_types:
            raise ValueError("opportunity types must be unique and ordered")
        for name in (
            "controller_component",
            "constraint_component",
            "dependency_component",
            "resolution_component",
            "criticality_component",
            "coverage_component",
            "coverage_confidence",
            "base_score",
            "opportunity_score",
        ):
            object.__setattr__(self, name, _score(getattr(self, name), name))
        configured = dict(sorted((key, float(value)) for key, value in self.configured_weights.items()))
        applied = dict(sorted((key, float(value)) for key, value in self.applied_weights.items()))
        if configured != dict(sorted(OPPORTUNITY_WEIGHTS.items())):
            raise ValueError("configured weights do not match opportunity policy")
        if not math.isclose(sum(applied.values()), 1.0, abs_tol=1e-6):
            raise ValueError("applied weights must sum to one")
        object.__setattr__(self, "configured_weights", configured)
        object.__setattr__(self, "applied_weights", applied)
        object.__setattr__(
            self, "evidence_ids", tuple(sorted(set(int(item) for item in self.evidence_ids)))
        )
        object.__setattr__(
            self, "reasoning_paths", tuple(sorted(set(self.reasoning_paths)))
        )
        if self.rank < 0:
            raise ValueError("rank cannot be negative")

    @property
    def availability_states(self) -> dict[str, str]:
        return {
            self.market_attention.name: self.market_attention.availability_state,
            self.valuation.name: self.valuation.availability_state,
            self.bubble_risk.name: self.bubble_risk.availability_state,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_key": list(self.company_key),
            "company_name": self.company_name,
            "opportunity_types": list(self.opportunity_types),
            "controller_component": self.controller_component,
            "constraint_component": self.constraint_component,
            "dependency_component": self.dependency_component,
            "resolution_component": self.resolution_component,
            "criticality_component": self.criticality_component,
            "market_attention": self.market_attention.to_dict(),
            "valuation": self.valuation.to_dict(),
            "bubble_risk": self.bubble_risk.to_dict(),
            "coverage_component": self.coverage_component,
            "coverage_confidence": self.coverage_confidence,
            "base_score": self.base_score,
            "opportunity_score": self.opportunity_score,
            "configured_weights": dict(self.configured_weights),
            "applied_weights": dict(self.applied_weights),
            "evidence_ids": list(self.evidence_ids),
            "reasoning_paths": [[list(node) for node in path] for path in self.reasoning_paths],
            "rank": self.rank,
        }


@dataclass(frozen=True)
class OpportunityBuild:
    controller_snapshot_id: int
    controller_version: str
    graph_snapshot_id: int
    graph_build_version: str
    algorithm_version: str
    opportunities: tuple[OpportunityIntelligence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "opportunities",
            tuple(sorted(self.opportunities, key=lambda row: (row.rank, row.company_key))),
        )


@dataclass(frozen=True)
class OpportunitySnapshot:
    opportunity_version: str
    controller_snapshot_id: int
    controller_version: str
    graph_snapshot_id: int
    graph_build_version: str
    algorithm_version: str
    status: str
    checksum: str
    company_count: int
    path_count: int
    activated_at: str | None = None
    created_at: str = ""
    id: int | None = None


def opportunity_build_checksum(build: OpportunityBuild) -> str:
    payload = {
        "controller_snapshot_id": build.controller_snapshot_id,
        "controller_version": build.controller_version,
        "graph_snapshot_id": build.graph_snapshot_id,
        "graph_build_version": build.graph_build_version,
        "algorithm_version": build.algorithm_version,
        "opportunities": [row.to_dict() for row in build.opportunities],
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
