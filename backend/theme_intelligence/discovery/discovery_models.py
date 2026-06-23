from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


THEME_ZH: dict[str, str] = {
    "Glass Substrate": "玻璃基板",
    "HBM": "高頻寬記憶體",
    "CoWoS": "CoWoS先進封裝",
    "AI Infrastructure": "AI基礎設施",
    "Advanced Packaging": "先進封裝",
    "Power Grid": "電力電網",
    "CPO Photonics": "CPO光子互連",
    "Robotics": "機器人",
    "Edge AI": "邊緣AI",
    "Data Center Cooling": "資料中心冷卻",
    "Optical Interconnect": "光通訊互連",
    "Nuclear": "核能",
    "Humanoid Robot": "人形機器人",
    "Satellite": "衛星",
    "Quantum": "量子科技",
}


def theme_id(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", name.strip().lower())
    return normalized.strip("_")


@dataclass(slots=True)
class DiscoveryBrief:
    why_now: str
    signals: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    watch_triggers: list[str] = field(default_factory=list)

    def to_api(self) -> dict[str, Any]:
        return {
            "why_now": self.why_now,
            "signals": list(self.signals),
            "risks": list(self.risks),
            "watch_triggers": list(self.watch_triggers),
        }


@dataclass(slots=True)
class DiscoveryTheme:
    name: str
    discovery_score: float
    emerging_score: float
    catalyst_score: float
    entity_strength_score: float
    confidence_score: float
    crowding_proxy: float
    final_ai_score: float
    lifecycle_stage: str
    lifecycle_confidence: float
    expected_next_stage: str
    time_window: str
    lifecycle_reason: str
    key_catalysts: list[dict[str, Any]] = field(default_factory=list)
    primary_bottleneck: dict[str, Any] | None = None
    bottleneck_strength: float = 0.0
    resolution_probability: float = 0.0
    top_beneficiaries: list[dict[str, Any]] = field(default_factory=list)
    beneficiary_research_importance: float = 0.0
    beneficiaries: list[dict[str, Any]] = field(default_factory=list)
    brief: DiscoveryBrief | dict[str, Any] | None = None
    updated_at: str = ""

    def to_api(self) -> dict[str, Any]:
        brief = self.brief.to_api() if isinstance(self.brief, DiscoveryBrief) else (self.brief or {})
        return {
            "theme_id": theme_id(self.name),
            "name": self.name,
            "name_zh": THEME_ZH.get(self.name, self.name),
            "ai_score": round(self.final_ai_score),
            "discovery_score": round(self.discovery_score),
            "emerging_score": round(self.emerging_score),
            "catalyst_score": round(self.catalyst_score),
            "entity_strength_score": round(self.entity_strength_score),
            "confidence_score": round(self.confidence_score),
            "crowding_proxy": round(self.crowding_proxy),
            "final_ai_score": round(self.final_ai_score),
            "lifecycle_stage": self.lifecycle_stage,
            "lifecycle_confidence": round(self.lifecycle_confidence),
            "expected_next_stage": self.expected_next_stage,
            "time_window": self.time_window,
            "lifecycle_reason": self.lifecycle_reason,
            "key_catalysts": list(self.key_catalysts),
            "primary_bottleneck": self.primary_bottleneck,
            "bottleneck_strength": round(self.bottleneck_strength),
            "resolution_probability": round(self.resolution_probability),
            "top_beneficiaries": list(self.top_beneficiaries),
            "beneficiary_research_importance": round(self.beneficiary_research_importance),
            "beneficiaries": list(self.beneficiaries),
            "brief": brief,
            "updated_at": self.updated_at,
        }
