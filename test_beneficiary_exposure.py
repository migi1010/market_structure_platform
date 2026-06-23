from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.beneficiaries.beneficiary_exposure import BeneficiaryExposureBuilder
from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeEntity


def test_exposure_uses_entities_as_source_of_truth_and_catalysts_do_not_create_tickers() -> None:
    builder = BeneficiaryExposureBuilder()
    entities = [
        ThemeEntity("Glass Substrate", "company", "Corning Inc.", "GLW", 82),
        ThemeEntity("Glass Substrate", "supply_chain_role", "substrate_materials", "GLW", 86),
    ]
    beneficiaries = [ThemeBeneficiary("Glass Substrate", "GLW", "Corning Inc.", 84, 82)]
    catalysts = [
        CatalystRecord(
            "Glass Substrate",
            "AMAT Packaging Equipment CapEx",
            "CapEx Expansion",
            "finnhub",
            85,
            80,
            description="CapEx expansion helps packaging equipment suppliers.",
        )
    ]

    candidates = builder.build("Glass Substrate", entities, beneficiaries, [], catalysts)

    assert {candidate.ticker for candidate in candidates} == {"GLW"}
    assert candidates[0].exposure_score > 0
    assert candidates[0].catalyst_relevance > 0

