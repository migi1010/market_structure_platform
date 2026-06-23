from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any, TYPE_CHECKING

from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, get_cached_value, set_cached_value
from theme_intelligence.bottlenecks.bottleneck_classifier import BottleneckClassifier
from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.bottlenecks.bottleneck_ranker import BottleneckRanker
from theme_intelligence.bottlenecks.bottleneck_resolver import BottleneckResolver
from theme_intelligence.bottlenecks.bottleneck_scorer import BottleneckScorer
from theme_intelligence.bottlenecks.bottleneck_timeline import BottleneckTimeline
from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeEntity, ThemeMention, clamp_score

if TYPE_CHECKING:
    from theme_intelligence.storage.theme_repository import ThemeRepository


THEME_BOTTLENECK_TTL_SECONDS = 21_600


class BottleneckEngine:
    def __init__(
        self,
        repository: "ThemeRepository | None" = None,
        classifier: BottleneckClassifier | None = None,
        resolver: BottleneckResolver | None = None,
        scorer: BottleneckScorer | None = None,
        timeline: BottleneckTimeline | None = None,
        ranker: BottleneckRanker | None = None,
    ) -> None:
        if repository is None:
            from theme_intelligence.storage.theme_repository import ThemeRepository

            repository = ThemeRepository()
        self.repository = repository
        self.classifier = classifier or BottleneckClassifier()
        self.resolver = resolver or BottleneckResolver()
        self.scorer = scorer or BottleneckScorer()
        self.timeline = timeline or BottleneckTimeline()
        self.ranker = ranker or BottleneckRanker()

    def get_bottlenecks(self, use_cache: bool = True) -> dict[str, Any]:
        cache_key = f"endpoint:{CACHE_SCHEMA_VERSION}:theme_bottlenecks:v1:all"
        if use_cache:
            cached = get_cached_value(cache_key)
            if isinstance(cached, dict):
                return cached
        result = self.refresh()
        set_cached_value(cache_key, result, THEME_BOTTLENECK_TTL_SECONDS, "json")
        return result

    def get_detail(self, theme_id_value: str) -> dict[str, Any]:
        normalized = theme_id_value.strip().lower()
        for row in self.get_bottlenecks().get("themes", []):
            if row.get("theme_id") == normalized or str(row.get("theme", "")).strip().lower() == normalized.replace("_", " "):
                return row
        return self._empty(normalized.replace("_", " ").title())

    def refresh(self) -> dict[str, Any]:
        self.repository.initialize()
        prepared = self.prepare(
            self.repository.get_mentions(),
            self.repository.get_catalysts(),
            self.repository.get_entities(),
            self.repository.get_beneficiaries(),
        )
        self.repository.save_bottlenecks(prepared)
        rows = self._to_api_rows(prepared)
        return {
            "themes": rows,
            "source_status": {
                "bottleneck_records": len(prepared),
                "cache_ttl_seconds": THEME_BOTTLENECK_TTL_SECONDS,
            },
        }

    def prepare(
        self,
        mentions: list[ThemeMention],
        catalysts: list[CatalystRecord],
        entities: list[ThemeEntity],
        beneficiaries: list[ThemeBeneficiary],
    ) -> list[BottleneckRecord]:
        raw = self._classify(mentions, catalysts)
        merged = self._merge(raw)
        resolved = [self.resolver.resolve(row, entities, beneficiaries) for row in merged]
        scored = self.scorer.score_many(resolved)
        return self.timeline.assign(scored)

    def _classify(self, mentions: list[ThemeMention], catalysts: list[CatalystRecord]) -> list[BottleneckRecord]:
        rows = [
            self.classifier.classify(mention.theme_name, mention.headline, mention.source, mention.symbol, mention.mention_time)
            for mention in mentions
            if self._looks_like_bottleneck(mention.headline)
        ]
        rows.extend(
            self.classifier.classify(
                catalyst.theme_name,
                f"{catalyst.catalyst_name} {catalyst.description}",
                catalyst.source,
                updated_at=catalyst.updated_at,
            )
            for catalyst in catalysts
            if self._looks_like_bottleneck(f"{catalyst.catalyst_name} {catalyst.description}") or catalyst.polarity == "risk"
        )
        return rows

    @staticmethod
    def _looks_like_bottleneck(text: str) -> bool:
        lower = text.lower()
        terms = (
            "capacity",
            "yield",
            "material",
            "chemical",
            "rare earth",
            "equipment",
            "tool",
            "engineer",
            "talent",
            "power",
            "cooling",
            "single supplier",
            "geographic concentration",
            "export control",
            "restriction",
            "shortage",
            "constraint",
            "bottleneck",
        )
        return any(term in lower for term in terms)

    @staticmethod
    def _merge(records: list[BottleneckRecord]) -> list[BottleneckRecord]:
        grouped: dict[tuple[str, str, str], list[BottleneckRecord]] = defaultdict(list)
        for record in records:
            grouped[(record.theme_name, record.bottleneck_name, record.bottleneck_type)].append(record)
        merged: list[BottleneckRecord] = []
        for rows in grouped.values():
            best = sorted(rows, key=lambda row: row.severity_score, reverse=True)[0]
            evidence = [item for row in rows for item in row.evidence]
            merged.append(
                best.with_updates(
                    severity_score=clamp_score(mean(row.severity_score for row in rows) + min(10.0, (len(rows) - 1) * 3.0)),
                    evidence=evidence[-12:],
                    updated_at=max(row.updated_at for row in rows),
                )
            )
        return merged

    def _to_api_rows(self, records: list[BottleneckRecord]) -> list[dict[str, Any]]:
        grouped: dict[str, list[BottleneckRecord]] = defaultdict(list)
        for record in records:
            grouped[record.theme_name].append(record)
        rows: list[dict[str, Any]] = []
        for theme_name in sorted(grouped):
            rows.append({"theme": theme_name, "theme_id": _theme_id(theme_name), **self.ranker.rank(grouped[theme_name])})
        return rows

    @staticmethod
    def _empty(theme_name: str) -> dict[str, Any]:
        return {
            "theme": theme_name,
            "theme_id": _theme_id(theme_name),
            "primary_bottleneck": None,
            "secondary_bottlenecks": [],
            "controllers": [],
            "beneficiaries": [],
            "resolution_probability": 0.0,
            "why_it_matters": "",
            "what_fixes_it": [],
            "who_controls_it": [],
            "who_benefits": [],
            "what_to_monitor": [],
        }


def get_theme_bottlenecks() -> dict[str, Any]:
    return BottleneckEngine().get_bottlenecks()


def get_theme_bottleneck_detail(theme_id_value: str) -> dict[str, Any]:
    return BottleneckEngine().get_detail(theme_id_value)


def _theme_id(name: str) -> str:
    return name.strip().lower().replace("/", " ").replace("&", "and").replace("-", " ").replace(" ", "_")
