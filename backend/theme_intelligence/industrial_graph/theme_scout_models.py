from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from .graph_models import canonical_json


LIFECYCLE_STATES = frozenset(
    {"DISCOVERED", "OBSERVING", "VALIDATING", "APPROVED", "REJECTED"}
)
SNAPSHOT_STATES = frozenset(
    {"building", "validated", "active", "superseded", "failed"}
)
DOMAIN_TYPES = frozenset(
    {"Technology", "Process", "Material", "Equipment", "Constraint", "Company", "Other"}
)
PATH_TYPES = frozenset(
    {"SIGNAL_CLUSTER", "THEME_EVOLUTION", "POTENTIAL_BOTTLENECK", "RESEARCH_HANDOFF"}
)
INFLUENCE_TARGET_TYPES = frozenset(
    {
        "Technology", "Process", "Material", "Equipment", "Constraint",
        "Company", "Infrastructure", "Capacity", "Other",
    }
)
DEFAULT_SCOUT_WEIGHTS = {
    "novelty": 0.0,
    "velocity": 0.20,
    "breadth": 0.20,
    "capital": 0.20,
    "bottleneck": 0.40,
}


def _score(value: float, name: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or not 0 <= parsed <= 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return parsed


def canonical_candidate_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "")).encode(
        "ascii", "ignore"
    ).decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if not slug:
        raise ValueError("candidate name is required")
    return f"candidate:{slug}"


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ScoutEvidence:
    evidence_id: str
    source_table: str
    source_record_id: str
    source_type: str
    source_timestamp: str
    source_identifier: str
    citation: str
    domain_type: str
    cluster_key: str
    source_value: Mapping[str, Any]
    content_hash: str = ""
    availability_state: str = "available"

    def __post_init__(self) -> None:
        for name in (
            "evidence_id", "source_table", "source_record_id", "source_type",
            "source_timestamp", "source_identifier", "citation",
        ):
            if not str(getattr(self, name) or "").strip():
                raise ValueError(f"{name} is required")
        if self.domain_type not in DOMAIN_TYPES:
            raise ValueError(f"unknown evidence domain: {self.domain_type}")
        if self.availability_state != "available":
            raise ValueError("admitted evidence must be available")
        value = dict(sorted(dict(self.source_value).items()))
        object.__setattr__(self, "source_value", value)
        object.__setattr__(self, "content_hash", self.content_hash or _hash(value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_table": self.source_table,
            "source_record_id": self.source_record_id,
            "source_type": self.source_type,
            "source_timestamp": self.source_timestamp,
            "source_identifier": self.source_identifier,
            "citation": self.citation,
            "domain_type": self.domain_type,
            "cluster_key": self.cluster_key,
            "source_value": dict(self.source_value),
            "content_hash": self.content_hash,
            "availability_state": self.availability_state,
        }


@dataclass(frozen=True)
class ThemeScoutSignalCluster:
    cluster_key: str
    label: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.cluster_key.strip() or not self.label.strip():
            raise ValueError("cluster key and label are required")
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(self.evidence_ids))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_key": self.cluster_key,
            "label": self.label,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class ThemeScoutPath:
    path_type: str
    label: str
    evidence_ids: tuple[str, ...]
    steps: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if self.path_type not in PATH_TYPES:
            raise ValueError(f"unknown Scout path type: {self.path_type}")
        if not self.label.strip():
            raise ValueError("path label is required")
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(self.evidence_ids))))
        object.__setattr__(self, "steps", tuple(dict(step) for step in self.steps))

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_type": self.path_type,
            "label": self.label,
            "evidence_ids": list(self.evidence_ids),
            "steps": [dict(step) for step in self.steps],
        }


@dataclass(frozen=True)
class ThemeCandidateInfluence:
    target_type: str
    target_label: str
    evidence_ids: tuple[str, ...]
    cluster_keys: tuple[str, ...]
    hypothesis_state: str = "hypothesis"

    def __post_init__(self) -> None:
        if self.target_type not in INFLUENCE_TARGET_TYPES:
            raise ValueError(f"unknown influence target type: {self.target_type}")
        if not self.target_label.strip():
            raise ValueError("influence target label is required")
        if self.hypothesis_state != "hypothesis":
            raise ValueError("influence map must remain hypothetical")
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(self.evidence_ids))))
        object.__setattr__(self, "cluster_keys", tuple(sorted(set(self.cluster_keys))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_type": self.target_type,
            "target_label": self.target_label,
            "evidence_ids": list(self.evidence_ids),
            "cluster_keys": list(self.cluster_keys),
            "hypothesis_state": self.hypothesis_state,
        }


@dataclass(frozen=True)
class ThemeScoutProposalCandidate:
    name: str
    description: str
    evidence_ids: tuple[str, ...]
    signal_clusters: tuple[ThemeScoutSignalCluster, ...] = ()
    paths: tuple[ThemeScoutPath, ...] = ()
    influence_map: tuple[ThemeCandidateInfluence, ...] = ()
    bottleneck_evidence_ids: tuple[str, ...] = ()
    generated_summary: str = ""
    status: str = "DISCOVERED"

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.description.strip():
            raise ValueError("candidate name and description are required")
        if self.status != "DISCOVERED":
            raise ValueError("provider candidates must start DISCOVERED")
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(self.evidence_ids))))
        object.__setattr__(
            self, "bottleneck_evidence_ids",
            tuple(sorted(set(self.bottleneck_evidence_ids))),
        )


@dataclass(frozen=True)
class ThemeScoutProposal:
    provider_name: str
    provider_model: str
    prompt_version: str
    candidates: tuple[ThemeScoutProposalCandidate, ...]

    def __post_init__(self) -> None:
        for value in (self.provider_name, self.provider_model, self.prompt_version):
            if not value.strip():
                raise ValueError("proposal provider metadata is required")
        object.__setattr__(
            self, "candidates",
            tuple(sorted(self.candidates, key=lambda row: canonical_candidate_key(row.name))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "provider_model": self.provider_model,
            "prompt_version": self.prompt_version,
            "candidates": [
                {
                    "name": row.name,
                    "description": row.description,
                    "evidence_ids": list(row.evidence_ids),
                    "signal_clusters": [item.to_dict() for item in row.signal_clusters],
                    "paths": [item.to_dict() for item in row.paths],
                    "influence_map": [item.to_dict() for item in row.influence_map],
                    "bottleneck_evidence_ids": list(row.bottleneck_evidence_ids),
                    "generated_summary": row.generated_summary,
                    "status": row.status,
                }
                for row in self.candidates
            ],
        }


class ThemeScoutProposalProvider(Protocol):
    provider_name: str
    provider_model: str
    prompt_version: str

    def propose(self, evidence: tuple[ScoutEvidence, ...]) -> ThemeScoutProposal: ...


@dataclass(frozen=True)
class ThemeScoutMetrics:
    confidence: float
    novelty: float
    velocity: float
    breadth: float
    capital: float
    bottleneck: float
    serendipity: float
    theme_score: float
    coverage: float
    raw_values: Mapping[str, Any]
    normalized_values: Mapping[str, float]
    applied_weights: Mapping[str, float]

    def __post_init__(self) -> None:
        for name in (
            "confidence", "novelty", "velocity", "breadth", "capital",
            "bottleneck", "serendipity", "theme_score", "coverage",
        ):
            object.__setattr__(self, name, _score(getattr(self, name), name))
        weights = dict(sorted((key, float(value)) for key, value in self.applied_weights.items()))
        if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-6):
            raise ValueError("Scout weights must sum to one")
        object.__setattr__(self, "applied_weights", weights)
        object.__setattr__(self, "raw_values", dict(sorted(self.raw_values.items())))
        object.__setattr__(
            self, "normalized_values",
            dict(sorted((key, _score(value, key)) for key, value in self.normalized_values.items())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "novelty": self.novelty,
            "velocity": self.velocity,
            "breadth": self.breadth,
            "capital": self.capital,
            "bottleneck": self.bottleneck,
            "serendipity": self.serendipity,
            "theme_score": self.theme_score,
            "coverage": self.coverage,
            "raw_values": dict(self.raw_values),
            "normalized_values": dict(self.normalized_values),
            "applied_weights": dict(self.applied_weights),
        }


@dataclass(frozen=True)
class ThemeScoutReadiness:
    technology: float
    process: float
    material: float
    equipment: float
    constraint: float
    company: float
    overall: float

    def __post_init__(self) -> None:
        for name in (
            "technology", "process", "material", "equipment",
            "constraint", "company", "overall",
        ):
            object.__setattr__(self, name, _score(getattr(self, name), name))

    @classmethod
    def from_evidence(cls, evidence: tuple[ScoutEvidence, ...]) -> "ThemeScoutReadiness":
        values: dict[str, float] = {}
        for domain in ("Technology", "Process", "Material", "Equipment", "Constraint", "Company"):
            rows = [row for row in evidence if row.domain_type == domain]
            evidence_strength = min(100.0, len({row.evidence_id for row in rows}) / 3 * 100)
            source_diversity = min(100.0, len({row.source_type for row in rows}) / 2 * 100)
            values[domain.lower()] = round(0.6 * evidence_strength + 0.4 * source_diversity, 4)
        overall = round(sum(values.values()) / 6, 4)
        return cls(**values, overall=overall)

    def to_dict(self) -> dict[str, float]:
        return {
            "technology": self.technology,
            "process": self.process,
            "material": self.material,
            "equipment": self.equipment,
            "constraint": self.constraint,
            "company": self.company,
            "overall": self.overall,
        }


@dataclass(frozen=True)
class ThemeScoutCandidate:
    candidate_key: str
    name: str
    description: str
    status: str
    metrics: ThemeScoutMetrics
    readiness: ThemeScoutReadiness
    evidence: tuple[ScoutEvidence, ...]
    signal_clusters: tuple[ThemeScoutSignalCluster, ...]
    paths: tuple[ThemeScoutPath, ...]
    influence_map: tuple[ThemeCandidateInfluence, ...]
    rank: int
    generated_summary: str = ""
    status_actor: str = "theme_scout"
    status_reason: str = "evidence-backed proposal"
    status_changed_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        key = canonical_candidate_key(self.name)
        if self.candidate_key != key:
            raise ValueError("candidate key does not match name")
        if self.status not in LIFECYCLE_STATES:
            raise ValueError("unknown candidate status")
        if self.rank < 1:
            raise ValueError("candidate rank must be positive")
        object.__setattr__(self, "evidence", tuple(sorted(
            {row.evidence_id: row for row in self.evidence}.values(),
            key=lambda row: row.evidence_id,
        )))

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def source_count(self) -> int:
        return len({row.source_identifier for row in self.evidence})

    @property
    def signal_count(self) -> int:
        return len(self.signal_clusters)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_key": self.candidate_key,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "metrics": self.metrics.to_dict(),
            "readiness": self.readiness.to_dict(),
            "evidence": [row.to_dict() for row in self.evidence],
            "signal_clusters": [row.to_dict() for row in self.signal_clusters],
            "paths": [row.to_dict() for row in self.paths],
            "influence_map": [row.to_dict() for row in self.influence_map],
            "rank": self.rank,
            "generated_summary": self.generated_summary,
            "status_actor": self.status_actor,
            "status_reason": self.status_reason,
            "status_changed_at": self.status_changed_at,
            "signal_count": self.signal_count,
            "evidence_count": self.evidence_count,
            "source_count": self.source_count,
        }


@dataclass(frozen=True)
class ThemeScoutBuild:
    algorithm_version: str
    provider_name: str
    provider_model: str
    prompt_version: str
    source_watermark: str
    evidence_bundle_checksum: str
    proposal_checksum: str
    candidates: tuple[ThemeScoutCandidate, ...]
    weights: Mapping[str, float] = field(default_factory=lambda: DEFAULT_SCOUT_WEIGHTS)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "candidates", tuple(sorted(self.candidates, key=lambda row: row.rank))
        )

    @property
    def checksum(self) -> str:
        return scout_build_checksum(self)


@dataclass(frozen=True)
class ThemeScoutSnapshot:
    scout_version: str
    algorithm_version: str
    provider_name: str
    provider_model: str
    prompt_version: str
    source_watermark: str
    evidence_bundle_checksum: str
    proposal_checksum: str
    checksum: str
    candidate_count: int
    status: str
    activated_at: str | None = None
    created_at: str = ""
    id: int | None = None


def candidate_checksum(candidate: ThemeScoutCandidate) -> str:
    return _hash(candidate.to_dict())


def scout_build_checksum(build: ThemeScoutBuild) -> str:
    return _hash({
        "algorithm_version": build.algorithm_version,
        "provider_name": build.provider_name,
        "provider_model": build.provider_model,
        "prompt_version": build.prompt_version,
        "source_watermark": build.source_watermark,
        "evidence_bundle_checksum": build.evidence_bundle_checksum,
        "proposal_checksum": build.proposal_checksum,
        "weights": dict(sorted(build.weights.items())),
        "candidates": [row.to_dict() for row in build.candidates],
    })
