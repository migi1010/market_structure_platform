from __future__ import annotations

from collections import defaultdict
from statistics import mean

from theme_intelligence.models import CANONICAL_THEMES, ThemeEntity, ThemeMention, ThemeScore, clamp_score, expected_next_stage, utc_now_iso
from theme_intelligence.scoring.velocity_score import news_velocity_score


SOURCE_WEIGHTS: dict[str, float] = {
    "finnhub": 1.0,
    "fmp": 1.0,
    "sec_filings": 0.9,
    "etf_holdings": 0.75,
    "market": 0.6,
}


def score_themes(mentions: list[ThemeMention], entities: list[ThemeEntity]) -> list[ThemeScore]:
    mentions_by_theme: dict[str, list[ThemeMention]] = defaultdict(list)
    entities_by_theme: dict[str, list[ThemeEntity]] = defaultdict(list)
    for mention in mentions:
        mentions_by_theme[mention.theme_name].append(mention)
    for entity in entities:
        entities_by_theme[entity.theme_name].append(entity)

    max_mentions = max((len(rows) for rows in mentions_by_theme.values()), default=1)
    scores: list[ThemeScore] = []
    for theme in CANONICAL_THEMES:
        theme_mentions = mentions_by_theme.get(theme, [])
        theme_entities = entities_by_theme.get(theme, [])
        mention_score = clamp_score((len(theme_mentions) / max_mentions) * 100.0 if max_mentions else 0.0)
        velocity = news_velocity_score(theme_mentions)
        sentiment = clamp_score(mean([mention.sentiment for mention in theme_mentions]), 50.0) if theme_mentions else 50.0
        attention = _attention_score(theme_mentions)
        entity_strength = _entity_strength(theme_entities)
        capital_flow = _capital_flow_proxy(theme_mentions, entity_strength)
        total = clamp_score(
            mention_score * 0.24
            + velocity * 0.22
            + sentiment * 0.16
            + attention * 0.18
            + entity_strength * 0.12
            + capital_flow * 0.08
        )
        scores.append(
            ThemeScore(
                theme_name=theme,
                mention_count=int(round(mention_score)),
                news_velocity=velocity,
                capital_flow_score=capital_flow,
                attention_score=attention,
                sentiment_score=sentiment,
                total_score=total,
                lifecycle_stage="Seed",
                lifecycle_confidence=0.0,
                expected_next_stage=expected_next_stage("Seed"),
                updated_at=utc_now_iso(),
            )
        )
    return scores


def _attention_score(mentions: list[ThemeMention]) -> float:
    if not mentions:
        return 0.0
    source_score = sum(SOURCE_WEIGHTS.get(mention.source, 0.5) for mention in mentions)
    unique_sources = len({mention.source for mention in mentions})
    symbol_count = len({mention.symbol for mention in mentions if mention.symbol})
    return clamp_score(source_score * 12.0 + unique_sources * 10.0 + symbol_count * 4.0)


def _entity_strength(entities: list[ThemeEntity]) -> float:
    if not entities:
        return 0.0
    top = sorted([entity.relationship_strength for entity in entities], reverse=True)[:8]
    return clamp_score(mean(top))


def _capital_flow_proxy(mentions: list[ThemeMention], entity_strength: float) -> float:
    etf_mentions = sum(1 for mention in mentions if mention.source == "etf_holdings")
    market_mentions = sum(1 for mention in mentions if mention.source == "market")
    return clamp_score(entity_strength * 0.65 + etf_mentions * 8.0 + market_mentions * 4.0)
