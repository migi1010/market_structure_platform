from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from theme_intelligence.models import clamp_score, utc_now_iso


CATALYST_TYPES: tuple[str, ...] = (
    "Product Launch",
    "CapEx Expansion",
    "Earnings Call Signal",
    "Supply Shortage",
    "Technology Breakthrough",
    "Customer Adoption",
    "Policy / Regulation",
    "Industry Demand",
)

TIMELINE_STATUSES: tuple[str, ...] = ("past", "current", "future")
POLARITIES: tuple[str, ...] = ("positive", "risk")


@dataclass(frozen=True)
class CatalystEvent:
    theme_name: str
    catalyst_name: str
    catalyst_type: str
    source: str
    description: str
    impact_score: float
    confidence_score: float
    novelty_score: float = 0.0
    duration_score: float = 0.0
    stage_relevance: float = 0.0
    catalyst_strength: float = 0.0
    cluster_key: str = ""
    timeline_status: str = "current"
    polarity: str = "positive"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        created = self.created_at or utc_now_iso()
        updated = self.updated_at or created
        object.__setattr__(self, "impact_score", clamp_score(self.impact_score))
        object.__setattr__(self, "confidence_score", clamp_score(self.confidence_score))
        object.__setattr__(self, "novelty_score", clamp_score(self.novelty_score))
        object.__setattr__(self, "duration_score", clamp_score(self.duration_score))
        object.__setattr__(self, "stage_relevance", clamp_score(self.stage_relevance))
        object.__setattr__(self, "catalyst_strength", clamp_score(self.catalyst_strength))
        object.__setattr__(self, "timeline_status", self.timeline_status if self.timeline_status in TIMELINE_STATUSES else "current")
        object.__setattr__(self, "polarity", self.polarity if self.polarity in POLARITIES else "positive")
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "updated_at", updated)

    def with_updates(self, **updates: Any) -> "CatalystEvent":
        return replace(self, **updates)

    def to_api(self) -> dict[str, Any]:
        return {
            "name": self.catalyst_name,
            "type": self.catalyst_type,
            "source": self.source,
            "description": self.description,
            "impact_score": clamp_score(self.impact_score),
            "confidence_score": clamp_score(self.confidence_score),
            "novelty_score": clamp_score(self.novelty_score),
            "duration_score": clamp_score(self.duration_score),
            "stage_relevance": clamp_score(self.stage_relevance),
            "catalyst_strength": clamp_score(self.catalyst_strength),
            "timeline_status": self.timeline_status,
            "polarity": self.polarity,
        }
