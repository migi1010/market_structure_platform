from __future__ import annotations

from typing import Any

from theme_intelligence.catalysts.catalyst_models import CatalystEvent


class CatalystRanker:
    def rank(self, events: list[CatalystEvent]) -> dict[str, list[dict[str, Any]]]:
        ranked = sorted(events, key=lambda row: row.catalyst_strength, reverse=True)
        positives = [event for event in ranked if event.polarity == "positive"]
        risks = [event for event in ranked if event.polarity == "risk"]
        future = [event for event in ranked if event.timeline_status == "future"]
        blockers = risks or [event for event in ranked if "risk" in event.description.lower() or "shortage" in event.catalyst_type.lower()]
        return {
            "top_catalysts": [event.to_api() for event in ranked[:5]],
            "top_positive_catalysts": [event.to_api() for event in positives[:5]],
            "top_risks": [event.to_api() for event in risks[:5]],
            "top_future_catalysts": [event.to_api() for event in future[:5]],
            "future_catalysts": [event.to_api() for event in future[:5]],
            "key_blockers": [event.to_api() for event in blockers[:5]],
        }
