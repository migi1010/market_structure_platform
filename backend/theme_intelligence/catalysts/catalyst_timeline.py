from __future__ import annotations

from datetime import datetime, timezone

from theme_intelligence.catalysts.catalyst_models import CatalystEvent


FUTURE_TERMS = ("will", "plan", "plans", "expected", "roadmap", "next-gen", "next generation", "2027", "2028", "hbm4")
PAST_TERMS = ("completed", "previous", "last quarter", "last year", "prior", "announced last")


class CatalystTimeline:
    def __init__(self, now_iso: str | None = None) -> None:
        self.now = self._parse_time(now_iso) if now_iso else datetime.now(timezone.utc)

    def assign(self, events: list[CatalystEvent]) -> list[CatalystEvent]:
        return [event.with_updates(timeline_status=self.status_for(event)) for event in events]

    def status_for(self, event: CatalystEvent) -> str:
        text = f"{event.catalyst_name} {event.description}".lower()
        if any(term in text for term in FUTURE_TERMS):
            return "future"
        if any(term in text for term in PAST_TERMS):
            return "past"
        created = self._parse_time(event.created_at)
        age_days = max(0.0, (self.now - created).total_seconds() / 86_400)
        if age_days > 90:
            return "past"
        return "current"

    @staticmethod
    def _parse_time(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
