from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.beneficiaries.beneficiary_models import BeneficiaryScoreRecord
from theme_intelligence.beneficiaries.beneficiary_scorer import BeneficiaryScorer, BubbleRiskProvider


class StaticBubble(BubbleRiskProvider):
    def __init__(self, bubble_index: float, valuation_heat: float) -> None:
        self.bubble_index = bubble_index
        self.valuation_heat = valuation_heat

    def analyze(self, ticker: str) -> dict:
        return {"bubble_index": self.bubble_index, "valuation_heat": self.valuation_heat}


def test_bubble_provider_uses_existing_bubble_result_as_penalty_input() -> None:
    scorer = BeneficiaryScorer(bubble_provider=StaticBubble(85, 80))
    row = BeneficiaryScoreRecord("AI Infrastructure", "NVDA", "NVIDIA Corporation", "Direct Beneficiary", 92, 88, 70, 0, 0, 0, 0, "accelerator")

    scored = scorer.score(row)

    assert scored.bubble_penalty == 27
    assert scored.valuation_penalty > 0
    assert scored.allocation_score < 80
    assert "Bubble risk" in scored.risk_factors[0]
