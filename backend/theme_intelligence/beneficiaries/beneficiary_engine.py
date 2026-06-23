from __future__ import annotations

from collections import defaultdict
from typing import Any, TYPE_CHECKING

from quant_engine.data_pipeline import CACHE_SCHEMA_VERSION, get_cached_value, set_cached_value
from theme_intelligence.beneficiaries.beneficiary_exposure import BeneficiaryExposureBuilder
from theme_intelligence.beneficiaries.beneficiary_models import BeneficiaryCandidate, BeneficiaryScoreRecord
from theme_intelligence.beneficiaries.beneficiary_ranker import BeneficiaryRanker
from theme_intelligence.beneficiaries.beneficiary_scorer import BeneficiaryScorer, BubbleRiskProvider
from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeEntity, utc_now_iso

if TYPE_CHECKING:
    from theme_intelligence.storage.theme_repository import ThemeRepository


THEME_BENEFICIARY_TTL_SECONDS = 21_600


class BeneficiaryEngine:
    def __init__(
        self,
        repository: "ThemeRepository | None" = None,
        exposure_builder: BeneficiaryExposureBuilder | None = None,
        scorer: BeneficiaryScorer | None = None,
        ranker: BeneficiaryRanker | None = None,
        bubble_provider: BubbleRiskProvider | None = None,
    ) -> None:
        if repository is None:
            from theme_intelligence.storage.theme_repository import ThemeRepository

            repository = ThemeRepository()
        self.repository = repository
        self.exposure_builder = exposure_builder or BeneficiaryExposureBuilder()
        self.scorer = scorer or BeneficiaryScorer(bubble_provider=bubble_provider)
        self.ranker = ranker or BeneficiaryRanker()

    def get_beneficiaries(self, use_cache: bool = True) -> dict[str, Any]:
        cache_key = f"endpoint:{CACHE_SCHEMA_VERSION}:theme_beneficiaries:v1:all"
        if use_cache:
            cached = get_cached_value(cache_key)
            if isinstance(cached, dict):
                return cached
        persisted = self.repository.get_beneficiary_scores()
        if persisted:
            result = {
                "themes": self._to_api_rows(persisted),
                "source_status": {
                    "beneficiary_records": len(persisted),
                    "cache_ttl_seconds": THEME_BENEFICIARY_TTL_SECONDS,
                    "source": "persisted_beneficiary_scores",
                },
            }
            set_cached_value(cache_key, result, THEME_BENEFICIARY_TTL_SECONDS, "json")
            return result
        result = self.refresh()
        set_cached_value(cache_key, result, THEME_BENEFICIARY_TTL_SECONDS, "json")
        return result

    def get_detail(self, theme_id_value: str) -> dict[str, Any]:
        normalized = theme_id_value.strip().lower()
        for row in self.get_beneficiaries().get("themes", []):
            if row.get("theme_id") == normalized or str(row.get("theme", "")).strip().lower() == normalized.replace("_", " "):
                return row
        return self._empty(normalized.replace("_", " ").title())

    def refresh(self) -> dict[str, Any]:
        self.repository.initialize()
        rows = self.prepare(
            self.repository.get_entities(),
            self.repository.get_beneficiaries(),
            self.repository.get_bottlenecks(),
            self.repository.get_catalysts(),
        )
        self.repository.save_beneficiary_scores(rows)
        return {
            "themes": self._to_api_rows(rows),
            "source_status": {
                "beneficiary_records": len(rows),
                "cache_ttl_seconds": THEME_BENEFICIARY_TTL_SECONDS,
            },
        }

    def prepare(
        self,
        entities: list[ThemeEntity],
        beneficiaries: list[ThemeBeneficiary],
        bottlenecks: list[BottleneckRecord],
        catalysts: list[CatalystRecord],
    ) -> list[BeneficiaryScoreRecord]:
        themes = sorted({item.theme_name for item in entities} | {item.theme_name for item in beneficiaries} | {item.theme_name for item in bottlenecks} | {item.theme_name for item in catalysts})
        records: list[BeneficiaryScoreRecord] = []
        for theme_name in themes:
            candidates = self.exposure_builder.build(theme_name, entities, beneficiaries, bottlenecks, catalysts)
            records.extend(self.scorer.score_many([self._record_from_candidate(candidate) for candidate in candidates]))
        return records

    @staticmethod
    def _record_from_candidate(candidate: BeneficiaryCandidate) -> BeneficiaryScoreRecord:
        return BeneficiaryScoreRecord(
            theme_name=candidate.theme_name,
            ticker=candidate.ticker,
            company_name=candidate.company_name,
            beneficiary_type=candidate.beneficiary_type,
            exposure_score=candidate.exposure_score,
            leverage_score=candidate.leverage_score,
            dependency_score=candidate.dependency_score,
            valuation_penalty=0.0,
            bubble_penalty=0.0,
            beneficiary_score=0.0,
            allocation_score=0.0,
            role=candidate.role,
            updated_at=utc_now_iso(),
        )

    def _to_api_rows(self, records: list[BeneficiaryScoreRecord]) -> list[dict[str, Any]]:
        grouped: dict[str, list[BeneficiaryScoreRecord]] = defaultdict(list)
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
            "top_beneficiaries": [],
            "controllers": [],
            "resolution_enablers": [],
            "ecosystem_beneficiaries": [],
            "indirect_beneficiaries": [],
            "allocation_buckets": {"High Conviction": [], "Medium Conviction": [], "Watchlist": [], "Avoid": []},
            "over_owned_or_bubble_risk": [],
            "research_importance": 0.0,
        }


def get_theme_beneficiaries() -> dict[str, Any]:
    return BeneficiaryEngine().get_beneficiaries()


def get_theme_beneficiary_detail(theme_id_value: str) -> dict[str, Any]:
    return BeneficiaryEngine().get_detail(theme_id_value)


def _theme_id(name: str) -> str:
    return name.strip().lower().replace("/", " ").replace("&", "and").replace("-", " ").replace(" ", "_")
