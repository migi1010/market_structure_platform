from __future__ import annotations

from theme_intelligence.models import ThemeMention, clamp_score


def compute_crowding_proxy(theme_name: str, mentions: list[ThemeMention], lifecycle_stage: str) -> float:
    stage_penalty = {"Seed": 4.0, "Early": 8.0, "Growth": 16.0, "Expansion": 28.0, "Mature": 40.0}.get(lifecycle_stage, 8.0)
    mention_penalty = max(0.0, len(mentions) - 8) * 2.5
    mega_cap_terms = ("nvidia", "microsoft", "amazon", "meta", "apple", "tesla")
    concentration = sum(1 for mention in mentions if any(term in mention.headline.lower() for term in mega_cap_terms))
    concentration_penalty = concentration * 3.0
    return clamp_score(stage_penalty + mention_penalty + concentration_penalty)
