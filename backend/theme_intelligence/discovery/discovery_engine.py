from __future__ import annotations

from typing import Any

from theme_intelligence.bottlenecks.bottleneck_engine import BottleneckEngine
from theme_intelligence.beneficiaries.beneficiary_engine import BeneficiaryEngine
from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, get_cached_value, set_cached_value
from theme_intelligence.catalysts.catalyst_engine import CatalystEngine
from theme_intelligence.collectors.etf_collector import ETFCollector
from theme_intelligence.collectors.filing_collector import FilingCollector
from theme_intelligence.collectors.market_collector import MarketCollector
from theme_intelligence.collectors.news_collector import NewsCollector
from theme_intelligence.discovery.discovery_ranking import rank_discovery_themes
from theme_intelligence.models import CollectorItem
from theme_intelligence.processors.catalyst_extractor import CatalystExtractor
from theme_intelligence.processors.entity_linker import EntityLinker
from theme_intelligence.processors.mention_deduplicator import MentionDeduplicator
from theme_intelligence.processors.mention_processor import MentionProcessor
from theme_intelligence.storage.theme_repository import ThemeRepository


THEME_DISCOVERY_TTL_SECONDS = 21_600


class DiscoveryEngine:
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
        bottleneck_engine: BottleneckEngine | None = None,
        beneficiary_engine: BeneficiaryEngine | None = None,
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
        self.bottleneck_engine = bottleneck_engine or BottleneckEngine(repository=self.repository)
        self.beneficiary_engine = beneficiary_engine or BeneficiaryEngine(repository=self.repository)
        self.entity_linker = entity_linker or EntityLinker()

    def get_discovery(self, limit: int = 20, use_cache: bool = True, refresh_data: bool = False) -> dict[str, Any]:
        cache_key = self._cache_key(limit)
        if refresh_data or not use_cache:
            result = self.refresh(limit=limit)
            set_cached_value(cache_key, result, THEME_DISCOVERY_TTL_SECONDS, "json")
            return result
        if use_cache:
            cached = get_cached_value(cache_key)
            if isinstance(cached, dict):
                return cached
        self.repository.initialize()
        rows = self.repository.get_discovery_scores(limit=limit)
        return {
            "themes": rows,
            "source_status": {
                "theme_count": len(rows),
                "source": "persisted",
                "cache_ttl_seconds": THEME_DISCOVERY_TTL_SECONDS,
            },
        }

    def refresh(self, limit: int = 20) -> dict[str, Any]:
        self.repository.initialize()
        items = self._collect_items()
        mentions, _legacy_catalysts = self.mention_processor.process(items)
        mentions = self.deduplicator.deduplicate(mentions)
        catalysts = self.catalyst_engine.prepare(self.catalyst_extractor.extract(mentions))
        linked = self.entity_linker.link(mentions)
        etf_entities, etf_beneficiaries = self.etf_collector.entities_and_beneficiaries()
        entities = [*linked.entities, *etf_entities]
        beneficiaries = [*linked.beneficiaries, *etf_beneficiaries]

        self.repository.save_mentions(mentions)
        self.repository.save_catalysts(catalysts)
        self.repository.save_entities(entities)
        self.repository.save_beneficiaries(beneficiaries)

        persisted_mentions = self.repository.get_mentions()
        persisted_catalysts = self.catalyst_engine.prepare(self.repository.get_catalysts())
        persisted_entities = self.repository.get_entities()
        persisted_beneficiaries = self.repository.get_beneficiaries()
        persisted_bottlenecks = self.bottleneck_engine.prepare(
            persisted_mentions or mentions,
            persisted_catalysts or catalysts,
            persisted_entities or entities,
            persisted_beneficiaries or beneficiaries,
        )
        self.repository.save_bottlenecks(persisted_bottlenecks)
        persisted_beneficiary_scores = self.beneficiary_engine.prepare(
            persisted_entities or entities,
            persisted_beneficiaries or beneficiaries,
            persisted_bottlenecks,
            persisted_catalysts or catalysts,
        )
        self.repository.save_beneficiary_scores(persisted_beneficiary_scores)
        ranked = rank_discovery_themes(
            persisted_mentions or mentions,
            persisted_catalysts or catalysts,
            persisted_entities or entities,
            persisted_beneficiaries or beneficiaries,
            bottlenecks=persisted_bottlenecks,
            beneficiary_scores=persisted_beneficiary_scores,
        )[:limit]
        api_rows = [row.to_api() for row in ranked]
        self.repository.upsert_discovery_scores(api_rows)
        for row in api_rows:
            self.repository.update_lifecycle(row["name"], row)
            self.repository.append_score_history(
                row["name"],
                {
                    "timestamp": row["updated_at"],
                    "lifecycle_stage": row["lifecycle_stage"],
                    "lifecycle_confidence": row["lifecycle_confidence"],
                    "expected_next_stage": row["expected_next_stage"],
                    "final_ai_score": row["ai_score"],
                    "emerging_score": row["emerging_score"],
                    "catalyst_score": row["catalyst_score"],
                    "entity_strength_score": row["entity_strength_score"],
                    "crowding_proxy": row["crowding_proxy"],
                },
            )
        return {
            "themes": api_rows,
            "source_status": {
                "collector_items": len(items),
                "deduped_mentions": len(mentions),
                "cache_ttl_seconds": THEME_DISCOVERY_TTL_SECONDS,
            },
        }

    def _collect_items(self) -> list[CollectorItem]:
        return [
            *self._safe_collect(self.market_collector.collect),
            *self._safe_collect(self.news_collector.collect),
            *self._safe_collect(self.filing_collector.collect),
            *self._safe_collect(self.etf_collector.collect),
        ]

    @staticmethod
    def _safe_collect(task: Any) -> list[CollectorItem]:
        try:
            rows = task()
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    @staticmethod
    def _cache_key(limit: int) -> str:
        return f"endpoint:{CACHE_SCHEMA_VERSION}:theme_discovery:v1:{max(1, int(limit))}"


def get_theme_discovery(limit: int = 20, refresh: bool = False) -> dict[str, Any]:
    return DiscoveryEngine().get_discovery(limit=limit, refresh_data=refresh)
