from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any


PORTFOLIO_TYPES: tuple[str, ...] = (
    "maximum_conviction",
    "balanced_growth",
    "low_bubble",
    "early_opportunity",
    "institutional",
)


PORTFOLIO_NAMES: dict[str, str] = {
    "maximum_conviction": "Maximum Conviction Theme Portfolio",
    "balanced_growth": "Balanced Growth Theme Portfolio",
    "low_bubble": "Low Bubble Theme Portfolio",
    "early_opportunity": "Early Opportunity Theme Portfolio",
    "institutional": "Institutional Theme Portfolio",
}


LIFECYCLE_TARGETS: dict[str, dict[str, float]] = {
    "maximum_conviction": {"Seed": 0.0, "Early": 25.0, "Growth": 45.0, "Expansion": 25.0, "Mature": 5.0},
    "balanced_growth": {"Seed": 10.0, "Early": 35.0, "Growth": 35.0, "Expansion": 15.0, "Mature": 5.0},
    "low_bubble": {"Seed": 0.0, "Early": 20.0, "Growth": 30.0, "Expansion": 35.0, "Mature": 15.0},
    "early_opportunity": {"Seed": 30.0, "Early": 50.0, "Growth": 15.0, "Expansion": 5.0, "Mature": 0.0},
    "institutional": {"Seed": 5.0, "Early": 30.0, "Growth": 35.0, "Expansion": 20.0, "Mature": 10.0},
}


CONVICTION_SCORES: dict[str, float] = {
    "Very High Conviction": 100.0,
    "High Conviction": 82.0,
    "Medium Conviction": 62.0,
    "Watchlist": 40.0,
    "Avoid": 0.0,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def round_score(value: float) -> float:
    return round(clamp_score(value), 2)


def theme_id_for(name: str) -> str:
    return name.strip().lower().replace("/", " ").replace("&", "and").replace("-", " ").replace(" ", "_")


@dataclass(frozen=True)
class PortfolioThemeCandidate:
    theme_name: str
    theme_id: str
    ai_potential_score: float
    research_importance: float
    allocation_readiness: float
    risk_adjusted_score: float
    conviction_level: str
    lifecycle_stage: str
    confidence_score: float
    bubble_penalty: float
    crowding_penalty: float
    unresolved_bottleneck_penalty: float
    bottleneck_overlap_keys: list[str] = field(default_factory=list)
    beneficiary_overlap_keys: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "theme_id", self.theme_id or theme_id_for(self.theme_name))
        for field_name in (
            "ai_potential_score",
            "research_importance",
            "allocation_readiness",
            "risk_adjusted_score",
            "confidence_score",
            "bubble_penalty",
            "crowding_penalty",
            "unresolved_bottleneck_penalty",
        ):
            object.__setattr__(self, field_name, clamp_score(float(getattr(self, field_name))))

    @property
    def conviction_score(self) -> float:
        return CONVICTION_SCORES.get(self.conviction_level, 0.0)

    @property
    def eligible_score(self) -> float:
        return round_score(
            self.risk_adjusted_score * 0.35
            + self.allocation_readiness * 0.25
            + self.ai_potential_score * 0.20
            + self.research_importance * 0.10
            + self.conviction_score * 0.10
        )

    def with_updates(self, **updates: Any) -> "PortfolioThemeCandidate":
        return replace(self, **updates)


@dataclass(frozen=True)
class PortfolioAllocation:
    theme: str
    theme_id: str
    weight: float
    allocation_rationale: str

    def to_api(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "theme_id": self.theme_id,
            "weight": round(self.weight, 2),
            "allocation_rationale": self.allocation_rationale,
        }


@dataclass(frozen=True)
class PortfolioRiskResult:
    risk_score: float
    risk_profile: str
    weighted_bubble_penalty: float
    weighted_crowding_penalty: float
    weighted_unresolved_bottleneck_penalty: float
    lifecycle_risk: float
    confidence_gap: float


@dataclass(frozen=True)
class DiversificationResult:
    diversification_score: float
    lifecycle_mix: dict[str, float]
    lifecycle_balance: float
    bottleneck_overlap_penalty: float
    beneficiary_overlap_penalty: float
    diversification_notes: list[str]


@dataclass(frozen=True)
class PortfolioResult:
    portfolio_name: str
    portfolio_type: str
    themes: list[PortfolioAllocation]
    risk_profile: str
    lifecycle_mix: dict[str, float]
    bubble_exposure: float
    portfolio_score: float
    allocation_quality: float
    diversification_score: float
    risk_score: float
    lifecycle_balance: float
    constraints: dict[str, Any] = field(default_factory=dict)
    why_selected: list[str] = field(default_factory=list)
    why_excluded: list[str] = field(default_factory=list)
    risk_sources: list[str] = field(default_factory=list)
    bubble_sources: list[str] = field(default_factory=list)
    diversification_notes: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_api(self) -> dict[str, Any]:
        return {
            "portfolio_type": self.portfolio_type,
            "portfolio_name": self.portfolio_name,
            "portfolio_score": round_score(self.portfolio_score),
            "risk_profile": self.risk_profile,
            "bubble_exposure": round_score(self.bubble_exposure),
            "allocation_quality": round_score(self.allocation_quality),
            "diversification_score": round_score(self.diversification_score),
            "risk_score": round_score(self.risk_score),
            "lifecycle_balance": round_score(self.lifecycle_balance),
            "lifecycle_mix": {key: round(value, 2) for key, value in self.lifecycle_mix.items() if value > 0},
            "themes": [theme.to_api() for theme in self.themes],
            "why_selected": self.why_selected,
            "why_excluded": self.why_excluded,
            "risk_sources": self.risk_sources,
            "bubble_sources": self.bubble_sources,
            "diversification_notes": self.diversification_notes,
            "constraints": self.constraints,
            "updated_at": self.updated_at,
        }
