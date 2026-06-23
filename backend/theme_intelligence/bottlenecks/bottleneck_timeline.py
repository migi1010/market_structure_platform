from __future__ import annotations

from datetime import datetime, timezone

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord


FUTURE_TERMS = ("will", "plans", "expected", "relief", "2027", "2028", "roadmap", "future")
PAST_TERMS = ("completed", "previous", "prior", "last quarter", "last year", "announced last")


class BottleneckTimeline:
    def __init__(self, now_iso: str | None = None) -> None:
        self.now = self._parse_time(now_iso) if now_iso else datetime.now(timezone.utc)

    def assign(self, records: list[BottleneckRecord]) -> list[BottleneckRecord]:
        return [record.with_updates(timeline_status=self.status_for(record)) for record in records]

    def status_for(self, record: BottleneckRecord) -> str:
        text = f"{record.bottleneck_name} {record.description} {' '.join(str(item.get('text', '')) for item in record.evidence)}".lower()
        if any(term in text for term in FUTURE_TERMS):
            return "future"
        if any(term in text for term in PAST_TERMS):
            return "past"
        updated = self._parse_time(record.updated_at)
        age_days = max(0.0, (self.now - updated).total_seconds() / 86_400)
        return "past" if age_days > 120 else "current"

    @staticmethod
    def _parse_time(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
