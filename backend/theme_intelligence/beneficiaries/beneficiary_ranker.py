from __future__ import annotations

from typing import Any

from theme_intelligence.beneficiaries.beneficiary_models import BeneficiaryScoreRecord


class BeneficiaryRanker:
    def rank(self, records: list[BeneficiaryScoreRecord]) -> dict[str, Any]:
        ranked = sorted(records, key=lambda row: (row.allocation_score, row.beneficiary_score), reverse=True)
        return {
            "top_beneficiaries": [row.to_api() for row in ranked[:10]],
            "controllers": [row.to_api() for row in ranked if row.beneficiary_type == "Bottleneck Controller"][:8],
            "resolution_enablers": [row.to_api() for row in ranked if row.beneficiary_type == "Resolution Enabler"][:8],
            "ecosystem_beneficiaries": [row.to_api() for row in ranked if row.beneficiary_type == "Ecosystem Beneficiary"][:8],
            "indirect_beneficiaries": [row.to_api() for row in ranked if row.beneficiary_type == "Indirect Beneficiary"][:8],
            "allocation_buckets": self._allocation_buckets(ranked),
            "over_owned_or_bubble_risk": [row.to_api() for row in ranked if row.bubble_penalty >= 35][:8],
            "research_importance": self._research_importance(ranked),
        }

    @staticmethod
    def _allocation_buckets(records: list[BeneficiaryScoreRecord]) -> dict[str, list[dict[str, Any]]]:
        buckets: dict[str, list[dict[str, Any]]] = {"High Conviction": [], "Medium Conviction": [], "Watchlist": [], "Avoid": []}
        for record in records:
            buckets.setdefault(record.allocation_bucket, []).append(record.to_api())
        return {key: value[:8] for key, value in buckets.items()}

    @staticmethod
    def _research_importance(records: list[BeneficiaryScoreRecord]) -> float:
        if not records:
            return 0.0
        top = records[:5]
        return round(sum(row.beneficiary_score for row in top) / len(top), 2)
