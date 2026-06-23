from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from .graph_models import NodeKey, canonical_json


PACKET_TYPE_ORDER = (
    "ThemeDecisionPacket",
    "CompanyDecisionPacket",
    "OpportunityDecisionPacket",
)
PACKET_STATUSES = frozenset(
    {"draft", "validated", "active", "superseded", "archived"}
)
RISK_CODES = frozenset({
    "CANONICAL_CONSTRAINT", "UNRESOLVED_CONSTRAINT_PATH",
    "MATCHED_PERSISTED_BOTTLENECK", "MARKET_ATTENTION_UNAVAILABLE",
    "VALUATION_UNAVAILABLE", "BUBBLE_UNAVAILABLE",
    "LOW_CONTROLLER_COVERAGE", "LOW_OPPORTUNITY_COVERAGE",
    "MISSING_GRAPH_EVIDENCE", "MISSING_PATH_EVIDENCE",
    "SOURCE_RECORD_UNAVAILABLE",
})
FORBIDDEN_PACKET_KEYS = frozenset({
    "summary", "narrative", "recommendation", "buy", "sell", "target_price",
    "why_high_score", "why_low_score", "major_risks", "conviction_reason",
    "allocation_notes", "generated_explanation",
})


def _score(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return value


def reject_forbidden_narrative(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_PACKET_KEYS:
                raise ValueError(f"forbidden narrative field: {path}.{key}")
            reject_forbidden_narrative(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            reject_forbidden_narrative(child, f"{path}[{index}]")


@dataclass(frozen=True)
class DecisionPacketPath:
    path_kind: str
    source_opportunity_path_order: int
    path: tuple[NodeKey, ...]
    evidence_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.path_kind or self.source_opportunity_path_order < 1 or not self.path:
            raise ValueError("complete packet path is required")
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(self.evidence_ids))))


@dataclass(frozen=True)
class DecisionPacketEvidence:
    evidence_kind: str
    original_graph_evidence_id: int | None
    source_table: str
    source_record_key: Mapping[str, str]
    source_timestamp: str | None
    source_value: Any
    source_type: str
    source_record_id: str
    content_hash: str
    citation: str | None
    review_status: str | None
    availability_state: str

    def __post_init__(self) -> None:
        if self.evidence_kind not in {"graph_evidence", "persisted_scalar", "persisted_bottleneck"}:
            raise ValueError("unsupported evidence kind")
        if not self.source_table or not self.content_hash:
            raise ValueError("evidence provenance is required")
        object.__setattr__(self, "source_record_key", dict(sorted(self.source_record_key.items())))


@dataclass(frozen=True)
class DecisionPacketRisk:
    risk_category: str
    risk_code: str
    risk_state: str
    subject_key: str
    constraint_key: str | None = None
    source_table: str | None = None
    source_record_key: Mapping[str, str] = field(default_factory=dict)
    source_timestamp: str | None = None
    source_value: Any = None
    path_orders: tuple[int, ...] = ()
    evidence_orders: tuple[int, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.risk_code not in RISK_CODES:
            raise ValueError("unsupported risk code")
        if self.risk_state not in {"known", "unresolved", "unknown", "missing", "unavailable"}:
            raise ValueError("unsupported risk state")
        reject_forbidden_narrative(self.metadata, "risk.metadata")
        object.__setattr__(self, "source_record_key", dict(sorted(self.source_record_key.items())))
        object.__setattr__(self, "metadata", dict(sorted(self.metadata.items())))


@dataclass(frozen=True)
class DecisionPacket:
    packet_type: str
    subject_type: str
    subject_key: str
    coverage: float
    evidence_coverage: float
    payload: Mapping[str, Any]
    paths: tuple[DecisionPacketPath, ...]
    evidence: tuple[DecisionPacketEvidence, ...]
    risks: tuple[DecisionPacketRisk, ...]

    def __post_init__(self) -> None:
        if self.packet_type not in PACKET_TYPE_ORDER:
            raise ValueError("unsupported packet type")
        if not self.subject_key:
            raise ValueError("packet subject is required")
        object.__setattr__(self, "coverage", _score(self.coverage, "coverage"))
        object.__setattr__(self, "evidence_coverage", _score(self.evidence_coverage, "evidence_coverage"))
        reject_forbidden_narrative(self.payload)
        object.__setattr__(self, "payload", dict(sorted(self.payload.items())))
        object.__setattr__(self, "paths", tuple(self.paths))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "risks", tuple(self.risks))

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_type": self.packet_type, "subject_type": self.subject_type,
            "subject_key": self.subject_key, "coverage": self.coverage,
            "evidence_coverage": self.evidence_coverage, "payload": dict(self.payload),
            "paths": [
                {"path_kind": p.path_kind, "source_opportunity_path_order": p.source_opportunity_path_order,
                 "path": p.path, "evidence_ids": p.evidence_ids} for p in self.paths
            ],
            "evidence": [e.__dict__ for e in self.evidence],
            "risks": [r.__dict__ for r in self.risks],
        }


@dataclass(frozen=True)
class DecisionPacketBuild:
    graph_snapshot_id: int
    graph_build_version: str
    controller_snapshot_id: int
    controller_version: str
    opportunity_snapshot_id: int
    opportunity_version: str
    algorithm_version: str
    packets: tuple[DecisionPacket, ...]

    def __post_init__(self) -> None:
        order = {name: index for index, name in enumerate(PACKET_TYPE_ORDER)}
        object.__setattr__(self, "packets", tuple(sorted(
            self.packets, key=lambda p: (order[p.packet_type], p.subject_key)
        )))


@dataclass(frozen=True)
class DecisionPacketFamily:
    packet_family_version: str
    packet_family_revision: int
    graph_snapshot_id: int
    controller_snapshot_id: int
    opportunity_snapshot_id: int
    algorithm_version: str
    status: str
    family_checksum: str
    packet_count: int
    path_count: int
    evidence_count: int
    risk_count: int
    activated_at: str | None = None
    created_at: str = ""


def packet_checksum(packet: DecisionPacket) -> str:
    return hashlib.sha256(canonical_json(packet.to_dict()).encode()).hexdigest()


def packet_build_checksum(build: DecisionPacketBuild) -> str:
    payload = {
        "graph_snapshot_id": build.graph_snapshot_id,
        "graph_build_version": build.graph_build_version,
        "controller_snapshot_id": build.controller_snapshot_id,
        "controller_version": build.controller_version,
        "opportunity_snapshot_id": build.opportunity_snapshot_id,
        "opportunity_version": build.opportunity_version,
        "algorithm_version": build.algorithm_version,
        "packets": [p.to_dict() for p in build.packets],
    }
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()
