from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from theme_intelligence.models import ThemeMention, clamp_score


@dataclass(frozen=True)
class EmergingScoreResult:
    score: float
    recent_count: int
    baseline_count: int
    acceleration: float
    unique_sources: int


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def compute_emerging_score(mentions: list[ThemeMention], now: datetime | None = None) -> EmergingScoreResult:
    if not mentions:
        return EmergingScoreResult(0.0, 0, 0, 0.0, 0)
    current = now or datetime.now(timezone.utc)
    recent_cutoff = current - timedelta(days=7)
    baseline_cutoff = current - timedelta(days=35)
    recent_mentions = [mention for mention in mentions if parse_time(mention.mention_time) >= recent_cutoff]
    baseline_mentions = [
        mention
        for mention in mentions
        if baseline_cutoff <= parse_time(mention.mention_time) < recent_cutoff
    ]
    recent_count = len(recent_mentions)
    baseline_count = len(baseline_mentions)
    recent_rate = recent_count / 7.0
    baseline_rate = max(baseline_count / 28.0, 0.25)
    acceleration = recent_rate / baseline_rate if recent_count else 0.0
    unique_sources = len({mention.source for mention in recent_mentions})
    duplicate_penalty = max(0.0, len(mentions) - len({mention.mention_hash or mention.headline for mention in mentions})) * 4.0
    score = clamp_score(45.0 + math.log2(max(acceleration, 0.25)) * 18.0 + unique_sources * 4.0 - duplicate_penalty)
    return EmergingScoreResult(score, recent_count, baseline_count, round(acceleration, 4), unique_sources)
