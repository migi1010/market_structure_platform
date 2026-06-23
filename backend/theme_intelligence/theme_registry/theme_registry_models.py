from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ThemeRegistryStatus = Literal["ACTIVE", "DISCOVERED", "ARCHIVED"]
ThemeRegistrySource = Literal["GRAPH", "SCOUT", "MANUAL"]
ThemeRegistryType = Literal[
    "INDUSTRIAL",
    "TECHNOLOGY",
    "INFRASTRUCTURE",
    "SUPPLY_CHAIN",
    "EMERGING",
]

REGISTRY_STATUSES: tuple[ThemeRegistryStatus, ...] = ("ACTIVE", "DISCOVERED", "ARCHIVED")
REGISTRY_SOURCES: tuple[ThemeRegistrySource, ...] = ("GRAPH", "SCOUT", "MANUAL")
REGISTRY_THEME_TYPES: tuple[ThemeRegistryType, ...] = (
    "INDUSTRIAL",
    "TECHNOLOGY",
    "INFRASTRUCTURE",
    "SUPPLY_CHAIN",
    "EMERGING",
)


@dataclass(frozen=True)
class ThemeRegistryEntry:
    theme_id: str
    theme_name: str
    status: ThemeRegistryStatus
    source: ThemeRegistrySource
    theme_type: ThemeRegistryType
    rank: float
    research_case_count: int
    graph_snapshot_count: int
    controller_count: int
    opportunity_count: int
    updated_at: str

    def __post_init__(self) -> None:
        if not self.theme_id.strip():
            raise ValueError("theme_id is required")
        if not self.theme_name.strip():
            raise ValueError("theme_name is required")
        if self.status not in REGISTRY_STATUSES:
            raise ValueError(f"unsupported registry status: {self.status}")
        if self.source not in REGISTRY_SOURCES:
            raise ValueError(f"unsupported registry source: {self.source}")
        if self.theme_type not in REGISTRY_THEME_TYPES:
            raise ValueError(f"unsupported registry theme_type: {self.theme_type}")
        for name in (
            "research_case_count",
            "graph_snapshot_count",
            "controller_count",
            "opportunity_count",
        ):
            if int(getattr(self, name)) < 0:
                raise ValueError(f"{name} cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "theme_name": self.theme_name,
            "status": self.status,
            "source": self.source,
            "theme_type": self.theme_type,
            "rank": self.rank,
            "research_case_count": self.research_case_count,
            "graph_snapshot_count": self.graph_snapshot_count,
            "controller_count": self.controller_count,
            "opportunity_count": self.opportunity_count,
            "updated_at": self.updated_at,
        }
