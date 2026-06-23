from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


CANONICAL_THEMES: tuple[str, ...] = (
    "HBM",
    "CoWoS",
    "Glass Substrate",
    "AI Infrastructure",
    "Power Grid",
    "Nuclear",
    "Robotics",
    "Humanoid Robot",
    "Satellite",
    "Quantum",
    "Optical Interconnect",
    "Advanced Packaging",
    "CPO Photonics",
    "Edge AI",
    "Data Center Cooling",
)

LIFECYCLE_STAGES: tuple[str, ...] = ("Seed", "Early", "Growth", "Expansion", "Mature")

THEME_ALIAS_MAP: dict[str, str] = {
    "hbm": "HBM",
    "high bandwidth memory": "HBM",
    "high-bandwidth memory": "HBM",
    "cowos": "CoWoS",
    "chip on wafer on substrate": "CoWoS",
    "glass substrate": "Glass Substrate",
    "glass core substrate": "Glass Substrate",
    "glass substrates": "Glass Substrate",
    "advanced substrate": "Glass Substrate",
    "ai infrastructure": "AI Infrastructure",
    "ai infra": "AI Infrastructure",
    "ai server": "AI Infrastructure",
    "ai servers": "AI Infrastructure",
    "ai datacenter": "AI Infrastructure",
    "ai data center": "AI Infrastructure",
    "data center ai": "AI Infrastructure",
    "power grid": "Power Grid",
    "electric grid": "Power Grid",
    "grid infrastructure": "Power Grid",
    "grid modernization": "Power Grid",
    "nuclear": "Nuclear",
    "nuclear energy": "Nuclear",
    "uranium": "Nuclear",
    "small modular reactor": "Nuclear",
    "smr": "Nuclear",
    "robotics": "Robotics",
    "robots": "Robotics",
    "automation robotics": "Robotics",
    "humanoid robot": "Humanoid Robot",
    "humanoid robotics": "Humanoid Robot",
    "humanoid robots": "Humanoid Robot",
    "satellite": "Satellite",
    "satellites": "Satellite",
    "space network": "Satellite",
    "quantum": "Quantum",
    "quantum computing": "Quantum",
    "quantum computer": "Quantum",
    "optical interconnect": "Optical Interconnect",
    "optical interconnects": "Optical Interconnect",
    "silicon photonics": "Optical Interconnect",
    "cpo": "CPO Photonics",
    "cpo photonics": "CPO Photonics",
    "co packaged optics": "CPO Photonics",
    "co-packaged optics": "CPO Photonics",
    "silicon photonics cpo": "CPO Photonics",
    "advanced packaging": "Advanced Packaging",
    "chip packaging": "Advanced Packaging",
    "semiconductor packaging": "Advanced Packaging",
    "packaging capacity": "Advanced Packaging",
    "edge ai": "Edge AI",
    "on device ai": "Edge AI",
    "on-device ai": "Edge AI",
    "ai pc": "Edge AI",
    "edge inference": "Edge AI",
    "embedded ai": "Edge AI",
    "data center cooling": "Data Center Cooling",
    "datacenter cooling": "Data Center Cooling",
    "liquid cooling": "Data Center Cooling",
    "immersion cooling": "Data Center Cooling",
    "thermal management": "Data Center Cooling",
    "ai cooling": "Data Center Cooling",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp_score(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        parsed = default
    return round(max(0.0, min(100.0, parsed)), 2)


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def normalize_theme_name(value: str | None) -> str | None:
    if not value:
        return None
    compact = _compact(value)
    if not compact:
        return None
    if compact in THEME_ALIAS_MAP:
        return THEME_ALIAS_MAP[compact]
    for canonical in CANONICAL_THEMES:
        if compact == _compact(canonical):
            return canonical
    return None


def validate_lifecycle_stage(stage: str | None, default: str = "Seed") -> str:
    if stage in LIFECYCLE_STAGES:
        return str(stage)
    normalized = (stage or "").strip().lower()
    for item in LIFECYCLE_STAGES:
        if item.lower() == normalized:
            return item
    return default


def expected_next_stage(stage: str | None) -> str:
    current = validate_lifecycle_stage(stage)
    index = LIFECYCLE_STAGES.index(current)
    if index >= len(LIFECYCLE_STAGES) - 1:
        return current
    return LIFECYCLE_STAGES[index + 1]


@dataclass(frozen=True)
class CollectorItem:
    source: str
    symbol: str | None
    headline: str
    published_at: str
    url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ThemeMention:
    theme_name: str
    source: str
    symbol: str | None
    headline: str
    mention_time: str
    sentiment: float
    created_at: str = field(default_factory=utc_now_iso)
    mention_hash: str | None = None
    canonical_headline: str | None = None
    provider_event_id: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class ThemeEntity:
    theme_name: str
    entity_type: str
    company: str
    ticker: str
    relationship_strength: float
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class CatalystRecord:
    theme_name: str
    catalyst_name: str
    catalyst_type: str
    source: str
    impact_score: float
    confidence_score: float
    description: str = ""
    novelty_score: float = 0.0
    duration_score: float = 0.0
    stage_relevance: float = 0.0
    catalyst_strength: float = 0.0
    cluster_key: str = ""
    timeline_status: str = "current"
    polarity: str = "positive"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_api(self) -> dict[str, object]:
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
            "cluster_key": self.cluster_key,
            "timeline_status": self.timeline_status,
            "polarity": self.polarity,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ThemeBeneficiary:
    theme_name: str
    ticker: str
    company_name: str
    beneficiary_score: float
    relationship_strength: float
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class ThemeScoreSnapshot:
    captured_at: str
    mention_score: float
    velocity_score: float
    sentiment_score: float
    attention_score: float
    entity_strength_score: float
    total_score: float


@dataclass(frozen=True)
class ThemeScore:
    theme_name: str
    mention_count: int
    news_velocity: float
    capital_flow_score: float
    attention_score: float
    sentiment_score: float
    total_score: float
    lifecycle_stage: str = "Seed"
    lifecycle_confidence: float = 0.0
    expected_next_stage: str = "Early"
    score_history_json: str = "[]"
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def mention_score(self) -> float:
        return clamp_score(self.mention_count)

    @property
    def velocity_score(self) -> float:
        return clamp_score(self.news_velocity)
