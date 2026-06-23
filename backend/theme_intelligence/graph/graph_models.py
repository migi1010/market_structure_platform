from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from theme_intelligence.discovery.discovery_models import theme_id


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def normalize_graph_id(value: str) -> str:
    normalized = theme_id(str(value or ""))
    return "_".join(part for part in normalized.split("_") if part)


@dataclass(frozen=True)
class GraphEdge:
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship_type: str
    strength_score: float
    evidence_source: str
    updated_at: str = field(default_factory=utc_now)
    id: int | None = None

    @property
    def identity_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.source_type,
            self.source_id,
            self.target_type,
            self.target_id,
            self.relationship_type,
        )

    @property
    def sort_key(self) -> tuple[str, str, str, str, str]:
        return self.identity_key

    def to_api(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "strength_score": round(max(0.0, min(100.0, float(self.strength_score))), 2),
            "evidence_source": self.evidence_source,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ThemeOverlap:
    theme_id: str
    related_theme_id: str
    overlap_score: float
    components: dict[str, float]
    shared_beneficiaries: list[str]
    shared_controllers: list[str]
    shared_bottlenecks: list[str]
    shared_catalysts: list[str]
    shared_portfolios: list[str]
    shared_supply_chain_roles: list[str]

    def to_api(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "related_theme_id": self.related_theme_id,
            "overlap_score": round(self.overlap_score, 2),
            "components": self.components,
            "shared_beneficiaries": self.shared_beneficiaries,
            "shared_controllers": self.shared_controllers,
            "shared_bottlenecks": self.shared_bottlenecks,
            "shared_catalysts": self.shared_catalysts,
            "shared_portfolios": self.shared_portfolios,
            "shared_supply_chain_roles": self.shared_supply_chain_roles,
        }
