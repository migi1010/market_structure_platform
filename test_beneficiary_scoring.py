from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.beneficiaries.beneficiary_allocator import BeneficiaryAllocator
from theme_intelligence.beneficiaries.beneficiary_models import BeneficiaryScoreRecord
from theme_intelligence.beneficiaries.beneficiary_scorer import BeneficiaryScorer


def test_beneficiary_score_and_allocation_use_required_formulas() -> None:
    scorer = BeneficiaryScorer()
    record = BeneficiaryScoreRecord(
        theme_name="Glass Substrate",
        ticker="GLW",
        company_name="Corning Inc.",
        beneficiary_type="Direct Beneficiary",
        exposure_score=90,
        leverage_score=80,
        dependency_score=70,
        valuation_penalty=20,
        bubble_penalty=10,
        beneficiary_score=0,
        allocation_score=0,
        role="substrate_materials",
        updated_at="2026-06-07T00:00:00+00:00",
    )

    scored = scorer.score(record)

    expected_beneficiary = 90 * 0.35 + 80 * 0.30 + 70 * 0.20 - 20 * 0.075 - 10 * 0.075
    expected_allocation = scored.beneficiary_score * 0.55 + 90 * 0.20 + 80 * 0.15 - 10 * 0.10
    assert scored.beneficiary_score == round(expected_beneficiary, 2)
    assert scored.allocation_score == round(expected_allocation, 2)


def test_allocator_bucket_assignment_and_bubble_risk_drag() -> None:
    allocator = BeneficiaryAllocator()
    high = BeneficiaryScoreRecord("HBM", "MU", "Micron Technology", "Direct Beneficiary", 95, 92, 88, 5, 20, 92, 86, "memory")
    bubble = BeneficiaryScoreRecord("HBM", "NVDA", "NVIDIA Corporation", "Direct Beneficiary", 96, 90, 70, 10, 75, 82, 78, "accelerator")
    weak = BeneficiaryScoreRecord("HBM", "ABC", "Example", "Indirect Beneficiary", 35, 30, 20, 0, 10, 35, 38, "theme_exposure")

    assert allocator.bucket(high) == "High Conviction"
    assert allocator.bucket(bubble) == "Avoid"
    assert allocator.bucket(weak) == "Avoid"

