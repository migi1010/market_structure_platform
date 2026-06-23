from __future__ import annotations

from typing import Any

from theme_intelligence.beneficiaries.beneficiary_allocator import BeneficiaryAllocator
from theme_intelligence.beneficiaries.beneficiary_models import BeneficiaryScoreRecord
from theme_intelligence.models import clamp_score


class BubbleRiskProvider:
    def analyze(self, ticker: str) -> dict[str, Any]:
        from quant_engine.bubble_engine import analyze_bubble

        payload = analyze_bubble(ticker)
        data = payload.get("bubble_analysis_data") if isinstance(payload, dict) else {}
        return data if isinstance(data, dict) else {}


class BeneficiaryScorer:
    def __init__(self, bubble_provider: BubbleRiskProvider | None = None, allocator: BeneficiaryAllocator | None = None) -> None:
        self.bubble_provider = bubble_provider or BubbleRiskProvider()
        self.allocator = allocator or BeneficiaryAllocator()

    def score(self, record: BeneficiaryScoreRecord) -> BeneficiaryScoreRecord:
        bubble = self._bubble_data(record.ticker)
        bubble_risk = clamp_score(bubble.get("bubble_index"), record.bubble_risk)
        valuation_heat = clamp_score(bubble.get("valuation_heat"), 0.0)
        bubble_penalty = record.bubble_penalty or clamp_score(max(0.0, bubble_risk - 55.0) * 0.9)
        valuation_penalty = record.valuation_penalty or clamp_score(max(0.0, valuation_heat - 45.0) * 0.55)
        beneficiary_score = clamp_score(
            record.exposure_score * 0.35
            + record.leverage_score * 0.30
            + record.dependency_score * 0.20
            - valuation_penalty * 0.075
            - bubble_penalty * 0.075
        )
        allocation_score = clamp_score(
            beneficiary_score * 0.55
            + record.exposure_score * 0.20
            + record.leverage_score * 0.15
            - bubble_penalty * 0.10
        )
        risk_factors: list[str] = []
        valuation_notes: list[str] = []
        if bubble_risk >= 65:
            risk_factors.append("Bubble risk is elevated and lowers allocation attractiveness.")
        if valuation_penalty > 0:
            valuation_notes.append("Valuation heat is already visible in the existing bubble analysis.")
        if not risk_factors:
            risk_factors.append("No severe bubble-risk penalty is present in the current deterministic inputs.")
        if not valuation_notes:
            valuation_notes.append("Valuation penalty is limited based on available bubble-engine inputs.")
        why = self._why_benefits(record)
        scored = record.with_updates(
            valuation_penalty=valuation_penalty,
            bubble_penalty=bubble_penalty,
            beneficiary_score=beneficiary_score,
            allocation_score=allocation_score,
            bubble_risk=bubble_risk,
            why_benefits=why,
            risk_factors=risk_factors,
            valuation_notes=valuation_notes,
        )
        bucket = self.allocator.bucket(scored)
        return scored.with_updates(allocation_bucket=bucket, allocation_reason=self.allocator.reason(scored.with_updates(allocation_bucket=bucket)))

    def score_many(self, records: list[BeneficiaryScoreRecord]) -> list[BeneficiaryScoreRecord]:
        return [self.score(record) for record in records]

    def _bubble_data(self, ticker: str) -> dict[str, Any]:
        try:
            data = self.bubble_provider.analyze(ticker)
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _why_benefits(record: BeneficiaryScoreRecord) -> str:
        return (
            f"{record.company_name} is linked to {record.theme_name} as a {record.beneficiary_type} "
            f"through role {record.role}."
        )
