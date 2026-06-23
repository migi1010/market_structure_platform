from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import mean
from typing import Any

from theme_intelligence.discovery.brief_generator import BriefGenerator
from theme_intelligence.discovery.discovery_models import DiscoveryTheme
from theme_intelligence.lifecycle.lifecycle_engine import LifecycleEngine
from theme_intelligence.lifecycle.lifecycle_models import LifecycleInput
from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeEntity, ThemeMention, clamp_score, expected_next_stage, utc_now_iso
from theme_intelligence.scoring.catalyst_score import compute_catalyst_score
from theme_intelligence.scoring.crowding_proxy import compute_crowding_proxy
from theme_intelligence.scoring.emerging_score import compute_emerging_score


def rank_discovery_themes(
    mentions: list[ThemeMention],
    catalysts: list[CatalystRecord],
    entities: list[ThemeEntity],
    beneficiaries: list[ThemeBeneficiary],
    bottlenecks: list[Any] | None = None,
    beneficiary_scores: list[Any] | None = None,
    now: datetime | None = None,
) -> list[DiscoveryTheme]:
    mention_map: dict[str, list[ThemeMention]] = defaultdict(list)
    catalyst_map: dict[str, list[CatalystRecord]] = defaultdict(list)
    entity_map: dict[str, list[ThemeEntity]] = defaultdict(list)
    beneficiary_map: dict[str, list[ThemeBeneficiary]] = defaultdict(list)
    bottleneck_map: dict[str, list[Any]] = defaultdict(list)
    beneficiary_score_map: dict[str, list[Any]] = defaultdict(list)
    for mention in mentions:
        mention_map[mention.theme_name].append(mention)
    for catalyst in catalysts:
        catalyst_map[catalyst.theme_name].append(catalyst)
    for entity in entities:
        entity_map[entity.theme_name].append(entity)
    for beneficiary in beneficiaries:
        beneficiary_map[beneficiary.theme_name].append(beneficiary)
    for bottleneck in bottlenecks or []:
        bottleneck_map[bottleneck.theme_name].append(bottleneck)
    for score in beneficiary_scores or []:
        beneficiary_score_map[score.theme_name].append(score)

    names = sorted(set(mention_map) | set(catalyst_map) | set(entity_map) | set(beneficiary_map) | set(bottleneck_map) | set(beneficiary_score_map))
    brief_generator = BriefGenerator()
    rows: list[DiscoveryTheme] = []
    lifecycle_engine = LifecycleEngine()
    for name in names:
        theme_mentions = mention_map.get(name, [])
        theme_catalysts = catalyst_map.get(name, [])
        theme_entities = entity_map.get(name, [])
        theme_beneficiaries = beneficiary_map.get(name, [])
        theme_bottlenecks = bottleneck_map.get(name, [])
        theme_beneficiary_scores = beneficiary_score_map.get(name, [])
        emerging = compute_emerging_score(theme_mentions, now=now)
        catalyst_score = compute_catalyst_score(theme_catalysts)
        entity_strength = _entity_strength_score(theme_entities, theme_beneficiaries)
        confidence = _confidence_score(theme_mentions, theme_catalysts, theme_entities)
        lifecycle = _lifecycle_stage(emerging.score, catalyst_score, entity_strength)
        bottleneck_metrics = _bottleneck_metrics(theme_bottlenecks)
        beneficiary_metrics = _beneficiary_metrics(theme_beneficiary_scores)
        crowding = clamp_score(compute_crowding_proxy(name, theme_mentions, lifecycle) + bottleneck_metrics["crowding_add"])
        confidence = clamp_score(confidence + beneficiary_metrics["confidence_add"])
        discovery = clamp_score(emerging.score * 0.42 + catalyst_score * 0.26 + entity_strength * 0.18 + confidence * 0.14)
        final = clamp_score(
            discovery * 0.28
            + emerging.score * 0.24
            + catalyst_score * 0.18
            + entity_strength * 0.14
            + confidence * 0.12
            - crowding * 0.10
            + bottleneck_metrics["final_adjustment"]
            + beneficiary_metrics["final_adjustment"]
        )
        lifecycle_result = lifecycle_engine.classify(
            LifecycleInput(
                theme_name=name,
                discovery_score=discovery,
                emerging_score=emerging.score,
                catalyst_score=catalyst_score,
                entity_strength_score=entity_strength,
                confidence_score=confidence,
                crowding_proxy=crowding,
                final_ai_score=final,
                key_catalysts=_catalyst_payload(theme_catalysts),
                key_bottlenecks=[bottleneck_metrics["primary"]] if bottleneck_metrics["primary"] else [],
                top_beneficiaries=beneficiary_metrics["top"],
                beneficiaries=_beneficiary_payload(theme_beneficiaries),
                source_count=len({mention.source for mention in theme_mentions}),
                history=[],
            )
        )
        rows.append(
            DiscoveryTheme(
                name=name,
                discovery_score=discovery,
                emerging_score=emerging.score,
                catalyst_score=catalyst_score,
                entity_strength_score=entity_strength,
                confidence_score=confidence,
                crowding_proxy=crowding,
                final_ai_score=final,
                lifecycle_stage=lifecycle_result.lifecycle_stage,
                lifecycle_confidence=lifecycle_result.lifecycle_confidence,
                expected_next_stage=lifecycle_result.expected_next_stage,
                time_window=lifecycle_result.time_window,
                lifecycle_reason=lifecycle_result.explanation.stage_reason,
                key_catalysts=_catalyst_payload(theme_catalysts),
                primary_bottleneck=bottleneck_metrics["primary"],
                bottleneck_strength=bottleneck_metrics["strength"],
                resolution_probability=bottleneck_metrics["resolution_probability"],
                top_beneficiaries=beneficiary_metrics["top"],
                beneficiary_research_importance=beneficiary_metrics["research_importance"],
                beneficiaries=_beneficiary_payload(theme_beneficiaries),
                brief=brief_generator.build(name, emerging, theme_catalysts, theme_beneficiaries, crowding),
                updated_at=utc_now_iso(),
            )
        )
    return sorted(rows, key=lambda item: item.final_ai_score, reverse=True)


def _entity_strength_score(entities: list[ThemeEntity], beneficiaries: list[ThemeBeneficiary]) -> float:
    values = [entity.relationship_strength for entity in entities] + [item.relationship_strength for item in beneficiaries]
    if not values:
        return 0.0
    ticker_count_score = min(100.0, len({item.ticker for item in entities if item.ticker}) * 10.0)
    return clamp_score(mean(sorted(values, reverse=True)[:8]) * 0.75 + ticker_count_score * 0.25)


def _confidence_score(mentions: list[ThemeMention], catalysts: list[CatalystRecord], entities: list[ThemeEntity]) -> float:
    sources = len({mention.source for mention in mentions})
    source_score = min(100.0, sources * 22.0)
    catalyst_confidence = mean([item.confidence_score for item in catalysts]) if catalysts else 35.0
    entity_score = min(100.0, len(entities) * 8.0)
    return clamp_score(source_score * 0.42 + catalyst_confidence * 0.34 + entity_score * 0.24)


def _lifecycle_stage(emerging_score: float, catalyst_score: float, entity_strength: float) -> str:
    composite = emerging_score * 0.50 + catalyst_score * 0.30 + entity_strength * 0.20
    if composite >= 78:
        return "Early"
    if composite >= 58:
        return "Seed"
    return "Seed"


def _time_window(lifecycle: str) -> str:
    return "1-3 months" if lifecycle in {"Seed", "Early"} else "3-6 months"


def _catalyst_payload(catalysts: list[CatalystRecord]) -> list[dict]:
    return [
        {
            "name": item.catalyst_name,
            "type": item.catalyst_type,
            "source": item.source,
            "description": getattr(item, "description", ""),
            "impact_score": clamp_score(item.impact_score),
            "confidence_score": clamp_score(item.confidence_score),
            "novelty_score": clamp_score(getattr(item, "novelty_score", 0.0)),
            "duration_score": clamp_score(getattr(item, "duration_score", 0.0)),
            "stage_relevance": clamp_score(getattr(item, "stage_relevance", 0.0)),
            "catalyst_strength": clamp_score(getattr(item, "catalyst_strength", 0.0)),
            "timeline_status": getattr(item, "timeline_status", "current"),
            "polarity": getattr(item, "polarity", "positive"),
        }
        for item in sorted(
            catalysts,
            key=lambda row: getattr(row, "catalyst_strength", 0.0) or (row.impact_score + row.confidence_score) / 2.0,
            reverse=True,
        )[:5]
    ]


def _beneficiary_payload(beneficiaries: list[ThemeBeneficiary]) -> list[dict]:
    return [
        {
            "ticker": item.ticker,
            "company_name": item.company_name,
            "beneficiary_score": clamp_score(item.beneficiary_score),
            "relationship_strength": clamp_score(item.relationship_strength),
        }
        for item in sorted(beneficiaries, key=lambda row: row.beneficiary_score, reverse=True)[:8]
    ]


def _bottleneck_metrics(bottlenecks: list[Any]) -> dict[str, Any]:
    if not bottlenecks:
        return {
            "primary": None,
            "strength": 0.0,
            "resolution_probability": 0.0,
            "crowding_add": 0.0,
            "final_adjustment": 0.0,
        }
    primary = sorted(bottlenecks, key=lambda row: row.bottleneck_strength, reverse=True)[0]
    strength = clamp_score(primary.bottleneck_strength)
    resolution = clamp_score(primary.resolution_probability)
    unresolved_penalty = max(0.0, strength - 60.0) * ((100.0 - resolution) / 100.0) * 0.14
    controller_bonus = min(4.0, len(primary.controller_entities) * 0.8 + len(primary.beneficiaries) * 0.35) if strength >= 70 else 0.0
    crowding_add = min(8.0, len(primary.evidence) * 2.0 + (strength * 0.03 if strength >= 70 else 0.0))
    return {
        "primary": primary.to_api(),
        "strength": strength,
        "resolution_probability": resolution,
        "crowding_add": clamp_score(crowding_add),
        "final_adjustment": clamp_score(controller_bonus) - clamp_score(unresolved_penalty),
    }


def _beneficiary_metrics(scores: list[Any]) -> dict[str, Any]:
    if not scores:
        return {"top": [], "research_importance": 0.0, "confidence_add": 0.0, "final_adjustment": 0.0}
    ranked = sorted(scores, key=lambda row: (row.allocation_score, row.beneficiary_score), reverse=True)
    top = ranked[:5]
    research_importance = clamp_score(sum(row.beneficiary_score for row in top) / len(top))
    average_allocation = clamp_score(sum(row.allocation_score for row in top) / len(top))
    bubble_drag = clamp_score(sum(row.bubble_penalty for row in top) / len(top))
    confidence_add = min(4.0, len(top) * 0.7 + average_allocation * 0.015)
    final_adjustment = clamp_score(max(0.0, average_allocation - 65.0) * 0.05) - clamp_score(max(0.0, bubble_drag - 35.0) * 0.04)
    return {
        "top": [row.to_api() for row in top],
        "research_importance": research_importance,
        "confidence_add": clamp_score(confidence_add),
        "final_adjustment": final_adjustment,
    }
