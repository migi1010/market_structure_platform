from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..models.theme_models import normalize_theme_name


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def theme_id_for(name: str) -> str:
    return normalize_theme_name(name).lower().replace(" ", "_").replace("/", "_")


@dataclass
class ThemeScoreInput:
    theme_name: str
    discovery_score: float
    emerging_score: float
    confidence_score: float
    crowding_proxy: float
    lifecycle_stage: str
    lifecycle_confidence: float
    catalyst_strength: float
    bottleneck_strength: float
    resolution_probability: float
    beneficiary_quality: float
    beneficiary_research_importance: float
    bubble_penalty: float
    top_beneficiaries: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ThemeFinalScore:
    theme_name: str
    ai_potential_score: float
    research_importance: float
    allocation_readiness: float
    risk_adjusted_score: float
    conviction_level: str
    updated_at: str = field(default_factory=utc_now_iso)
    score_components: dict[str, Any] = field(default_factory=dict)
    why_high_score: str = ""
    why_low_score: str = ""
    major_strengths: list[str] = field(default_factory=list)
    major_risks: list[str] = field(default_factory=list)
    allocation_notes: list[str] = field(default_factory=list)
    conviction_reason: str = ""

    def to_api(self) -> dict[str, Any]:
        return {
            "theme": self.theme_name,
            "theme_id": theme_id_for(self.theme_name),
            "ai_potential_score": self.ai_potential_score,
            "research_importance": self.research_importance,
            "allocation_readiness": self.allocation_readiness,
            "risk_adjusted_score": self.risk_adjusted_score,
            "conviction_level": self.conviction_level,
            "score_components": self.score_components,
            "why_high_score": self.why_high_score,
            "why_low_score": self.why_low_score,
            "major_strengths": self.major_strengths,
            "major_risks": self.major_risks,
            "allocation_notes": self.allocation_notes,
            "conviction_reason": self.conviction_reason,
            "updated_at": self.updated_at,
        }
