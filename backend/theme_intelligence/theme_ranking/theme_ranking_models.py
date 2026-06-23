from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal


ThemeRankingLifecycle = Literal[
    "EMERGING",
    "ACCELERATING",
    "ACTIVE",
    "MONITORING",
    "DECLINING",
]

THEME_RANKING_LIFECYCLES: tuple[ThemeRankingLifecycle, ...] = (
    "EMERGING",
    "ACCELERATING",
    "ACTIVE",
    "MONITORING",
    "DECLINING",
)


def _score(value: float, field_name: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0 or parsed > 100:
        raise ValueError(f"{field_name} must be between 0 and 100")
    return round(parsed, 4)


@dataclass(frozen=True)
class ThemeRankingWeights:
    evidence: float = 0.30
    research: float = 0.20
    controller: float = 0.20
    opportunity: float = 0.20
    momentum: float = 0.10

    def __post_init__(self) -> None:
        values = self.to_dict()
        if any(not math.isfinite(value) or value < 0 for value in values.values()):
            raise ValueError("ranking weights must be finite and non-negative")
        if not math.isclose(sum(values.values()), 1.0, abs_tol=1e-9):
            raise ValueError("ranking weights must sum to 1.0")

    def to_dict(self) -> dict[str, float]:
        return {
            "evidence": float(self.evidence),
            "research": float(self.research),
            "controller": float(self.controller),
            "opportunity": float(self.opportunity),
            "momentum": float(self.momentum),
        }


@dataclass(frozen=True)
class ThemeRankingSource:
    theme_id: str
    theme_name: str
    has_active_graph: bool
    has_scout_signal: bool
    scout_theme_score: float
    scout_velocity_score: float
    scout_evidence_count: int
    scout_signal_count: int
    research_case_count: int
    approved_research_count: int
    monitoring_research_count: int
    controller_count: int
    opportunity_count: int
    graph_evidence_count: int
    updated_at: str

    def __post_init__(self) -> None:
        if not self.theme_id.strip():
            raise ValueError("theme_id is required")
        if not self.theme_name.strip():
            raise ValueError("theme_name is required")
        for field_name in (
            "scout_evidence_count",
            "scout_signal_count",
            "research_case_count",
            "approved_research_count",
            "monitoring_research_count",
            "controller_count",
            "opportunity_count",
            "graph_evidence_count",
        ):
            if int(getattr(self, field_name)) < 0:
                raise ValueError(f"{field_name} cannot be negative")
        _score(self.scout_theme_score, "scout_theme_score")
        _score(self.scout_velocity_score, "scout_velocity_score")


@dataclass(frozen=True)
class ThemeRank:
    theme_id: str
    theme_name: str
    lifecycle: ThemeRankingLifecycle
    rank_score: float
    momentum_score: float
    evidence_score: float
    research_score: float
    controller_score: float
    opportunity_score: float
    updated_at: str

    def __post_init__(self) -> None:
        if not self.theme_id.strip():
            raise ValueError("theme_id is required")
        if not self.theme_name.strip():
            raise ValueError("theme_name is required")
        if self.lifecycle not in THEME_RANKING_LIFECYCLES:
            raise ValueError(f"unsupported lifecycle: {self.lifecycle}")
        for field_name in (
            "rank_score",
            "momentum_score",
            "evidence_score",
            "research_score",
            "controller_score",
            "opportunity_score",
        ):
            object.__setattr__(self, field_name, _score(getattr(self, field_name), field_name))

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "theme_name": self.theme_name,
            "lifecycle": self.lifecycle,
            "rank_score": self.rank_score,
            "momentum_score": self.momentum_score,
            "evidence_score": self.evidence_score,
            "research_score": self.research_score,
            "controller_score": self.controller_score,
            "opportunity_score": self.opportunity_score,
            "updated_at": self.updated_at,
        }
