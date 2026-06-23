from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping


NODE_TYPES = frozenset({
    "Theme", "Technology", "Process", "Material", "Equipment", "Company",
    "Supplier", "Customer", "Industry", "Patent", "Standard", "Country",
    "Constraint", "Facility", "Product", "Capacity", "Certification",
})

RELATIONSHIP_TYPES = frozenset({
    "USES", "REQUIRES", "DEPENDS_ON", "SUPPLIED_BY", "PRODUCED_BY",
    "SUPPLIES", "CUSTOMER_OF", "COMPETES_WITH", "ENABLES", "CONTROLS",
    "PROTECTS", "LIMITS", "RESOLVES", "OWNS", "HAS_CAPACITY", "LICENSES",
    "PROCESS_PRECEDES_PROCESS", "MATERIAL_SUBSTITUTES_FOR",
    "USES_SUPPLIER", "SUPPLY_CHAIN_ROLE", "PART_OF_SUPPLY_CHAIN",
    "LIMITED_BY", "RESOLVED_BY",
    "USES_TECHNOLOGY", "REQUIRES_PROCESS", "PROCESS_DEPENDS_ON_PROCESS",
    "TECHNOLOGY_ENABLES_PROCESS", "PROCESS_LIMITED_BY_CONSTRAINT",
    "PROCESS_RESOLVED_BY_COMPANY",
    "PROCESS_REQUIRES_MATERIAL", "MATERIAL_SUPPLIED_BY",
    "MATERIAL_LIMITED_BY", "MATERIAL_RESOLVED_BY",
    "MATERIAL_ENABLES_PROCESS", "THEME_DEPENDS_ON_MATERIAL",
    "PROCESS_REQUIRES_EQUIPMENT", "EQUIPMENT_PRODUCED_BY",
    "EQUIPMENT_SUBSTITUTES_FOR", "EQUIPMENT_LIMITED_BY",
    "EQUIPMENT_RESOLVED_BY", "EQUIPMENT_ENABLES_PROCESS",
    "THEME_DEPENDS_ON_EQUIPMENT",
    "THEME_LIMITED_BY_CONSTRAINT", "TECHNOLOGY_LIMITED_BY_CONSTRAINT",
    "MATERIAL_LIMITED_BY_CONSTRAINT", "EQUIPMENT_LIMITED_BY_CONSTRAINT",
    "CONSTRAINT_RESOLVED_BY_COMPANY", "COMPANY_EXPOSED_TO_CONSTRAINT",
    "CONSTRAINT_DEPENDS_ON_MATERIAL", "CONSTRAINT_DEPENDS_ON_EQUIPMENT",
    "CONSTRAINT_DEPENDS_ON_PROCESS", "CONSTRAINT_RELATED_TO_CONSTRAINT",
})

NodeKey = tuple[str, str]
EvidenceKey = tuple[str, str, str]
BaseEdgeKey = tuple[NodeKey, str, NodeKey]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def normalize_canonical_key(value: str, *, node_type: str | None = None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if node_type == "Company":
        ticker = raw.split(":", 1)[-1].strip().upper()
        return f"company:{ticker}"
    if ":" in raw:
        prefix, *parts = raw.split(":")
        normalized_parts = [_slug(part) for part in parts]
        return ":".join([_slug(prefix), *[part for part in normalized_parts if part]])
    return _slug(raw)


def _validate_score(value: float, name: str) -> float:
    parsed = float(value)
    if not 0.0 <= parsed <= 100.0:
        raise ValueError(f"{name} must be between 0 and 100")
    return parsed


@dataclass(frozen=True)
class IndustrialGraphNode:
    node_type: str
    canonical_key: str
    display_name: str
    aliases: tuple[str, ...] = ()
    external_ids: Mapping[str, str] = field(default_factory=dict)
    status: str = "active"
    valid_from: str = ""
    valid_to: str | None = None
    created_at: str = ""
    updated_at: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if self.node_type not in NODE_TYPES:
            raise ValueError(f"Unsupported node type: {self.node_type}")
        key = normalize_canonical_key(self.canonical_key, node_type=self.node_type)
        if not key:
            raise ValueError("canonical key is required")
        if not str(self.display_name or "").strip():
            raise ValueError("display name is required")
        object.__setattr__(self, "canonical_key", key)
        object.__setattr__(self, "aliases", tuple(sorted({str(item).strip() for item in self.aliases if str(item).strip()})))
        object.__setattr__(
            self,
            "external_ids",
            {key: str(value) for key, value in sorted(dict(self.external_ids).items())},
        )

    @property
    def identity_key(self) -> NodeKey:
        return self.node_type, self.canonical_key

    @property
    def sort_key(self) -> NodeKey:
        return self.identity_key


@dataclass(frozen=True)
class IndustrialGraphEdge:
    source_key: NodeKey
    relationship_type: str
    target_key: NodeKey
    confidence_score: float = 100.0
    dependency_strength: float = 0.0
    status: str = "building"
    valid_from: str = ""
    valid_to: str | None = None
    build_version: str = ""
    created_at: str = ""
    updated_at: str = ""
    id: int | None = None
    source_node_id: int | None = None
    target_node_id: int | None = None

    def __post_init__(self) -> None:
        if self.relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"Unsupported relationship: {self.relationship_type}")
        source_type, source_key = self.source_key
        target_type, target_key = self.target_key
        if source_type not in NODE_TYPES or target_type not in NODE_TYPES:
            raise ValueError("edge endpoint has unsupported node type")
        source = (source_type, normalize_canonical_key(source_key, node_type=source_type))
        target = (target_type, normalize_canonical_key(target_key, node_type=target_type))
        if not source[1] or not target[1]:
            raise ValueError("edge endpoint canonical key is required")
        object.__setattr__(self, "source_key", source)
        object.__setattr__(self, "target_key", target)
        object.__setattr__(self, "confidence_score", _validate_score(self.confidence_score, "confidence_score"))
        object.__setattr__(self, "dependency_strength", _validate_score(self.dependency_strength, "dependency_strength"))

    @property
    def base_identity_key(self) -> BaseEdgeKey:
        return self.source_key, self.relationship_type, self.target_key

    @property
    def identity_key(self) -> tuple[NodeKey, str, NodeKey, str]:
        return (*self.base_identity_key, self.valid_from)

    @property
    def sort_key(self) -> tuple[NodeKey, str, NodeKey, str]:
        return self.identity_key


@dataclass(frozen=True)
class IndustrialGraphEvidence:
    source_type: str
    source_record_id: str
    content_hash: str
    citation: str
    observed_date: str | None = None
    review_status: str = "approved"
    created_at: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.source_type.strip():
            raise ValueError("source type is required")
        if not self.source_record_id.strip():
            raise ValueError("source record id is required")
        if not self.content_hash.strip():
            raise ValueError("content hash is required")
        if not self.citation.strip():
            raise ValueError("citation is required")

    @classmethod
    def from_payload(
        cls,
        source_type: str,
        source_record_id: str,
        citation: str,
        payload: Any,
        *,
        observed_date: str | None = None,
        review_status: str = "approved",
    ) -> "IndustrialGraphEvidence":
        return cls(
            source_type=source_type,
            source_record_id=source_record_id,
            content_hash=content_hash(payload),
            citation=citation,
            observed_date=observed_date,
            review_status=review_status,
        )

    @property
    def identity_key(self) -> EvidenceKey:
        return self.source_type, self.source_record_id, self.content_hash

    @property
    def sort_key(self) -> EvidenceKey:
        return self.identity_key


@dataclass(frozen=True)
class IndustrialGraphEdgeEvidence:
    edge_key: BaseEdgeKey
    evidence_key: EvidenceKey

    @property
    def sort_key(self) -> tuple[BaseEdgeKey, EvidenceKey]:
        return self.edge_key, self.evidence_key


@dataclass(frozen=True)
class IndustrialGraphSnapshot:
    build_version: str
    status: str
    source_watermark: str
    node_count: int
    edge_count: int
    checksum: str
    activated_at: str | None = None
    created_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class IndustrialGraphBuild:
    nodes: tuple[IndustrialGraphNode, ...] = ()
    edges: tuple[IndustrialGraphEdge, ...] = ()
    evidence: tuple[IndustrialGraphEvidence, ...] = ()
    edge_evidence: tuple[IndustrialGraphEdgeEvidence, ...] = ()
    source_watermark: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(sorted(self.nodes, key=lambda row: row.sort_key)))
        object.__setattr__(self, "edges", tuple(sorted(self.edges, key=lambda row: row.sort_key)))
        object.__setattr__(self, "evidence", tuple(sorted(self.evidence, key=lambda row: row.sort_key)))
        object.__setattr__(self, "edge_evidence", tuple(sorted(self.edge_evidence, key=lambda row: row.sort_key)))
