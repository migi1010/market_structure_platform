from __future__ import annotations

from typing import Any

from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, get_cached_value, set_cached_value
from theme_intelligence.catalysts.catalyst_engine import CatalystEngine
from theme_intelligence.collectors.etf_collector import ETFCollector
from theme_intelligence.collectors.filing_collector import FilingCollector
from theme_intelligence.collectors.market_collector import MarketCollector
from theme_intelligence.collectors.news_collector import NewsCollector
from theme_intelligence.models import CollectorItem
from theme_intelligence.processors.catalyst_extractor import CatalystExtractor
from theme_intelligence.processors.entity_linker import EntityLinker
from theme_intelligence.processors.mention_deduplicator import MentionDeduplicator
from theme_intelligence.processors.mention_processor import MentionProcessor
from theme_intelligence.scoring.theme_score import score_themes
from theme_intelligence.storage.theme_repository import ThemeRepository


THEME_INTELLIGENCE_TTL_SECONDS = 21_600


class ThemeIntelligenceService:
    def __init__(
        self,
        repository: ThemeRepository | None = None,
        market_collector: MarketCollector | None = None,
        news_collector: NewsCollector | None = None,
        filing_collector: FilingCollector | None = None,
        etf_collector: ETFCollector | None = None,
        mention_processor: MentionProcessor | None = None,
        deduplicator: MentionDeduplicator | None = None,
        catalyst_extractor: CatalystExtractor | None = None,
        catalyst_engine: CatalystEngine | None = None,
        entity_linker: EntityLinker | None = None,
    ) -> None:
        self.repository = repository or ThemeRepository()
        self.market_collector = market_collector or MarketCollector()
        self.news_collector = news_collector or NewsCollector()
        self.filing_collector = filing_collector or FilingCollector()
        self.etf_collector = etf_collector or ETFCollector()
        self.mention_processor = mention_processor or MentionProcessor()
        self.deduplicator = deduplicator or MentionDeduplicator()
        self.catalyst_extractor = catalyst_extractor or CatalystExtractor()
        self.catalyst_engine = catalyst_engine or CatalystEngine(repository=self.repository)
        self.entity_linker = entity_linker or EntityLinker()

    def get_intelligence(self, limit: int | None = None, use_cache: bool = True) -> dict[str, Any]:
        cache_key = self._cache_key("top" if limit else "all", limit or "all")
        if use_cache:
            cached = get_cached_value(cache_key)
            if isinstance(cached, dict):
                return cached
        result = self.refresh(limit=limit)
        set_cached_value(cache_key, result, THEME_INTELLIGENCE_TTL_SECONDS, "json")
        return result

    def refresh(self, limit: int | None = None) -> dict[str, Any]:
        self.repository.initialize()
        etf_items = self.etf_collector.collect()
        items = [
            *self._safe_collect(self.market_collector.collect),
            *self._safe_collect(self.news_collector.collect),
            *self._safe_collect(self.filing_collector.collect),
            *etf_items,
        ]
        mentions, _legacy_catalysts = self.mention_processor.process(items)
        mentions = self.deduplicator.deduplicate(mentions)
        catalysts = self.catalyst_engine.prepare(self.catalyst_extractor.extract(mentions))
        linked = self.entity_linker.link(mentions)
        etf_entities, etf_beneficiaries = self.etf_collector.entities_and_beneficiaries()
        entities = [*linked.entities, *etf_entities]
        beneficiaries = [*linked.beneficiaries, *etf_beneficiaries]
        scores = score_themes(mentions, entities)

        self.repository.save_mentions(mentions)
        self.repository.save_catalysts(catalysts)
        self.repository.save_entities(entities)
        self.repository.save_beneficiaries(beneficiaries)
        self.repository.upsert_scores(scores)

        rows = self.repository.get_top_scores(limit) if limit else self.repository.get_scores()
        return {"themes": [self._api_theme(row) for row in rows], "source_status": self._source_status(items, mentions)}

    @staticmethod
    def _safe_collect(task: Any) -> list[CollectorItem]:
        try:
            rows = task()
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    @staticmethod
    def _api_theme(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": row["name"],
            "mention_score": row["mention_score"],
            "velocity_score": row["velocity_score"],
            "sentiment_score": row["sentiment_score"],
            "lifecycle_stage": row["lifecycle_stage"],
            "lifecycle_confidence": row["lifecycle_confidence"],
            "total_score": row["total_score"],
        }

    @staticmethod
    def _source_status(items: list[CollectorItem], mentions: list[Any]) -> dict[str, Any]:
        sources = sorted({item.source for item in items})
        return {
            "collector_items": len(items),
            "mentions_extracted": len(mentions),
            "sources": sources,
            "cache_ttl_seconds": THEME_INTELLIGENCE_TTL_SECONDS,
        }

    @staticmethod
    def _cache_key(namespace: str, *parts: Any) -> str:
        suffix = ":".join(str(part).strip().lower() for part in parts if str(part).strip())
        return f"endpoint:{CACHE_SCHEMA_VERSION}:theme_intelligence:{namespace}:{suffix}"


def get_theme_intelligence() -> dict[str, Any]:
    return ThemeIntelligenceService().get_intelligence()


def get_top_theme_intelligence(limit: int = 20) -> dict[str, Any]:
    return ThemeIntelligenceService().get_intelligence(limit=limit)
