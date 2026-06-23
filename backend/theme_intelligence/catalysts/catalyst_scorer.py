from __future__ import annotations

from datetime import datetime, timezone

from theme_intelligence.catalysts.catalyst_models import CatalystEvent
from theme_intelligence.models import clamp_score


DURATION_PRIORS: dict[str, float] = {
    "Product Launch": 72.0,
    "CapEx Expansion": 88.0,
    "Earnings Call Signal": 58.0,
    "Supply Shortage": 64.0,
    "Technology Breakthrough": 82.0,
    "Customer Adoption": 76.0,
    "Policy / Regulation": 78.0,
    "Industry Demand": 70.0,
}

STAGE_RELEVANCE: dict[str, dict[str, float]] = {
    "Seed": {"Technology Breakthrough": 85, "Policy / Regulation": 72, "Industry Demand": 68},
    "Early": {"Customer Adoption": 82, "CapEx Expansion": 78, "Product Launch": 76},
    "Growth": {"Product Launch": 84, "CapEx Expansion": 82, "Supply Shortage": 72, "Industry Demand": 76},
    "Expansion": {"Earnings Call Signal": 78, "Customer Adoption": 82, "Industry Demand": 74},
    "Mature": {"Supply Shortage": 70, "Earnings Call Signal": 66, "Policy / Regulation": 62},
}


class CatalystScorer:
    def __init__(self, now_iso: str | None = None) -> None:
        self.now = self._parse_time(now_iso) if now_iso else datetime.now(timezone.utc)

    def score(self, event: CatalystEvent, lifecycle_stage: str = "Early") -> CatalystEvent:
        novelty = event.novelty_score or self._novelty(event)
        duration = event.duration_score or DURATION_PRIORS.get(event.catalyst_type, 58.0)
        relevance = event.stage_relevance or STAGE_RELEVANCE.get(lifecycle_stage, {}).get(event.catalyst_type, 55.0)
        strength = clamp_score(
            event.impact_score * 0.35
            + event.confidence_score * 0.25
            + novelty * 0.20
            + duration * 0.15
            + relevance * 0.05
        )
        return event.with_updates(
            novelty_score=clamp_score(novelty),
            duration_score=clamp_score(duration),
            stage_relevance=clamp_score(relevance),
            catalyst_strength=strength,
        )

    def score_many(self, events: list[CatalystEvent], lifecycle_stage: str = "Early") -> list[CatalystEvent]:
        return [self.score(event, lifecycle_stage) for event in events]

    def _novelty(self, event: CatalystEvent) -> float:
        created = self._parse_time(event.created_at)
        age_days = max(0.0, (self.now - created).total_seconds() / 86_400)
        if age_days <= 7:
            return 88.0
        if age_days <= 30:
            return 76.0
        if age_days <= 90:
            return 58.0
        return 34.0

    @staticmethod
    def _parse_time(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
