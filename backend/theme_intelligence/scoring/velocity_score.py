from __future__ import annotations

from datetime import datetime, timedelta, timezone

from theme_intelligence.models import ThemeMention, clamp_score


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def news_velocity_score(mentions: list[ThemeMention], now: datetime | None = None) -> float:
    if not mentions:
        return 0.0
    current = now or datetime.now(timezone.utc)
    recent_cutoff = current - timedelta(hours=24)
    baseline_cutoff = current - timedelta(days=7)
    recent = sum(1 for mention in mentions if _parse_time(mention.mention_time) >= recent_cutoff)
    baseline = sum(1 for mention in mentions if _parse_time(mention.mention_time) >= baseline_cutoff)
    baseline_daily = max(1.0, baseline / 7.0)
    return clamp_score((recent / baseline_daily) * 25.0)
