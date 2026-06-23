from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LifecycleInput:
    theme_name: str
    discovery_score: float
    emerging_score: float
    catalyst_score: float
    entity_strength_score: float
    confidence_score: float
    crowding_proxy: float
    final_ai_score: float
    key_catalysts: list[dict[str, Any]] = field(default_factory=list)
    key_bottlenecks: list[dict[str, Any]] = field(default_factory=list)
    top_beneficiaries: list[dict[str, Any]] = field(default_factory=list)
    beneficiaries: list[dict[str, Any]] = field(default_factory=list)
    source_count: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    attention_score: float | None = None
    mention_count: int | None = None
    velocity_score: float | None = None
    sentiment_score: float | None = None


@dataclass(frozen=True)
class StageDecision:
    stage: str
    matched_rules: list[str]
    deteriorating: bool


@dataclass(frozen=True)
class LifecycleExplanation:
    stage_reason: str
    positive_signals: list[str]
    negative_signals: list[str]
    stage_risks: list[str]
    next_stage_triggers: list[str]
    top_catalysts: list[dict[str, Any]] = field(default_factory=list)
    future_catalysts: list[dict[str, Any]] = field(default_factory=list)
    key_blockers: list[dict[str, Any]] = field(default_factory=list)
    primary_bottleneck: dict[str, Any] | None = None
    bottleneck_risks: list[dict[str, Any]] = field(default_factory=list)
    top_beneficiaries: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class LifecycleResult:
    theme_name: str
    lifecycle_stage: str
    lifecycle_confidence: float
    expected_next_stage: str
    time_window: str
    final_ai_score: float
    emerging_score: float
    catalyst_score: float
    entity_strength_score: float
    crowding_proxy: float
    explanation: LifecycleExplanation
    history: list[dict[str, Any]]

    @property
    def stage_reason(self) -> str:
        return self.explanation.stage_reason

    @property
    def positive_signals(self) -> list[str]:
        return self.explanation.positive_signals

    @property
    def negative_signals(self) -> list[str]:
        return self.explanation.negative_signals

    @property
    def stage_risks(self) -> list[str]:
        return self.explanation.stage_risks

    @property
    def next_stage_triggers(self) -> list[str]:
        return self.explanation.next_stage_triggers

    @property
    def top_catalysts(self) -> list[dict[str, Any]]:
        return self.explanation.top_catalysts

    @property
    def future_catalysts(self) -> list[dict[str, Any]]:
        return self.explanation.future_catalysts

    @property
    def key_blockers(self) -> list[dict[str, Any]]:
        return self.explanation.key_blockers

    @property
    def primary_bottleneck(self) -> dict[str, Any] | None:
        return self.explanation.primary_bottleneck

    @property
    def bottleneck_risks(self) -> list[dict[str, Any]]:
        return self.explanation.bottleneck_risks

    @property
    def top_beneficiaries(self) -> list[dict[str, Any]]:
        return self.explanation.top_beneficiaries
