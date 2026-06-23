from __future__ import annotations

from theme_intelligence.models import clamp_score


POSITIVE_TERMS = (
    "accelerate",
    "accelerates",
    "growth",
    "expansion",
    "surge",
    "record",
    "upgrade",
    "demand",
    "wins",
    "launch",
    "investment",
    "capacity",
)

NEGATIVE_TERMS = (
    "delay",
    "delays",
    "risk",
    "lawsuit",
    "shortage",
    "cut",
    "weak",
    "miss",
    "decline",
    "downgrade",
    "constraint",
)


class SentimentProcessor:
    def score(self, text: str) -> float:
        lower = text.lower()
        positive = sum(1 for term in POSITIVE_TERMS if term in lower)
        negative = sum(1 for term in NEGATIVE_TERMS if term in lower)
        return clamp_score(50.0 + positive * 8.0 - negative * 9.0, 50.0)
