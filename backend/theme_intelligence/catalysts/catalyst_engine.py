from __future__ import annotations

from collections import defaultdict
from typing import Any, TYPE_CHECKING

from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, get_cached_value, set_cached_value
from theme_intelligence.catalysts.catalyst_clusterer import CatalystClusterer
from theme_intelligence.catalysts.catalyst_models import CatalystEvent
from theme_intelligence.catalysts.catalyst_ranker import CatalystRanker
from theme_intelligence.catalysts.catalyst_scorer import CatalystScorer
from theme_intelligence.catalysts.catalyst_timeline import CatalystTimeline
from theme_intelligence.models import CatalystRecord

if TYPE_CHECKING:
    from theme_intelligence.storage.theme_repository import ThemeRepository


THEME_CATALYST_TTL_SECONDS = 21_600


class CatalystEngine:
    def __init__(
        self,
        repository: "ThemeRepository | None" = None,
        clusterer: CatalystClusterer | None = None,
        scorer: CatalystScorer | None = None,
        timeline: CatalystTimeline | None = None,
        ranker: CatalystRanker | None = None,
    ) -> None:
        if repository is None:
            from theme_intelligence.storage.theme_repository import ThemeRepository

            repository = ThemeRepository()
        self.repository = repository
        self.clusterer = clusterer or CatalystClusterer()
        self.scorer = scorer or CatalystScorer()
        self.timeline = timeline or CatalystTimeline()
        self.ranker = ranker or CatalystRanker()

    def get_catalysts(self, use_cache: bool = True) -> dict[str, Any]:
        cache_key = f"endpoint:{CACHE_SCHEMA_VERSION}:theme_catalysts:v1:all"
        if use_cache:
            cached = get_cached_value(cache_key)
            if isinstance(cached, dict):
                return cached
        result = self.refresh()
        set_cached_value(cache_key, result, THEME_CATALYST_TTL_SECONDS, "json")
        return result

    def get_detail(self, theme_id_value: str) -> dict[str, Any]:
        normalized = theme_id_value.strip().lower()
        for row in self.get_catalysts().get("themes", []):
            if row.get("theme_id") == normalized or str(row.get("theme", "")).strip().lower() == normalized.replace("_", " "):
                return row
        return self._empty(normalized.replace("_", " ").title())

    def refresh(self) -> dict[str, Any]:
        self.repository.initialize()
        events = self.prepare(self.repository.get_catalysts())
        self.repository.save_catalysts(events)
        grouped: dict[str, list[CatalystEvent]] = defaultdict(list)
        for event in events:
            grouped[event.theme_name].append(event)
        rows = []
        for theme_name in sorted(grouped):
            summary = self.ranker.rank(grouped[theme_name])
            rows.append({"theme": theme_name, "theme_id": _theme_id(theme_name), **summary})
        return {
            "themes": rows,
            "source_status": {
                "catalyst_records": len(events),
                "cache_ttl_seconds": THEME_CATALYST_TTL_SECONDS,
            },
        }

    def prepare(self, catalysts: list[CatalystRecord | CatalystEvent], lifecycle_stage: str = "Early") -> list[CatalystEvent]:
        events = [self._to_event(row) for row in catalysts]
        clustered = self.clusterer.cluster(events)
        scored = self.scorer.score_many(clustered, lifecycle_stage=lifecycle_stage)
        return self.timeline.assign(scored)

    @staticmethod
    def _to_event(row: CatalystRecord | CatalystEvent) -> CatalystEvent:
        if isinstance(row, CatalystEvent):
            return row
        return CatalystEvent(
            theme_name=row.theme_name,
            catalyst_name=row.catalyst_name,
            catalyst_type=row.catalyst_type,
            source=row.source,
            description=getattr(row, "description", "") or f"{row.catalyst_name} catalyst evidence.",
            impact_score=row.impact_score,
            confidence_score=row.confidence_score,
            novelty_score=getattr(row, "novelty_score", 0.0),
            duration_score=getattr(row, "duration_score", 0.0),
            stage_relevance=getattr(row, "stage_relevance", 0.0),
            catalyst_strength=getattr(row, "catalyst_strength", 0.0),
            cluster_key=getattr(row, "cluster_key", ""),
            timeline_status=getattr(row, "timeline_status", "current"),
            polarity=getattr(row, "polarity", "positive"),
            created_at=row.created_at,
            updated_at=getattr(row, "updated_at", row.created_at),
        )

    @staticmethod
    def _empty(theme_name: str) -> dict[str, Any]:
        return {
            "theme": theme_name,
            "theme_id": _theme_id(theme_name),
            "top_catalysts": [],
            "top_positive_catalysts": [],
            "top_risks": [],
            "top_future_catalysts": [],
            "future_catalysts": [],
            "key_blockers": [],
        }


def get_theme_catalysts() -> dict[str, Any]:
    return CatalystEngine().get_catalysts()


def get_theme_catalyst_detail(theme_id_value: str) -> dict[str, Any]:
    return CatalystEngine().get_detail(theme_id_value)


def _theme_id(name: str) -> str:
    return name.strip().lower().replace("/", " ").replace("&", "and").replace("-", " ").replace(" ", "_")
