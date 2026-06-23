from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.beneficiaries.beneficiary_engine import BeneficiaryEngine
from theme_intelligence.beneficiaries.beneficiary_scorer import BubbleRiskProvider
from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeEntity


class StaticBubble(BubbleRiskProvider):
    def analyze(self, ticker: str) -> dict:
        return {"bubble_index": 15, "valuation_heat": 20}


def test_catalysts_raise_existing_candidate_exposure_without_unsupported_tickers() -> None:
    engine = BeneficiaryEngine(bubble_provider=StaticBubble())
    entities = [
        ThemeEntity("Glass Substrate", "company", "Corning Inc.", "GLW", 82),
        ThemeEntity("Glass Substrate", "supply_chain_role", "substrate_materials", "GLW", 86),
    ]
    beneficiaries = [ThemeBeneficiary("Glass Substrate", "GLW", "Corning Inc.", 84, 82)]
    catalysts = [
        CatalystRecord("Glass Substrate", "AMAT Packaging Equipment", "CapEx Expansion", "finnhub", 88, 82, description="AMAT benefits from packaging capex.")
    ]

    rows = engine.prepare(entities, beneficiaries, [], catalysts)

    assert {row.ticker for row in rows} == {"GLW"}
    assert rows[0].exposure_score >= 60

