from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.beneficiaries.beneficiary_engine import BeneficiaryEngine
from theme_intelligence.beneficiaries.beneficiary_scorer import BubbleRiskProvider
from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.models import ThemeBeneficiary, ThemeEntity


class StaticBubble(BubbleRiskProvider):
    def analyze(self, ticker: str) -> dict:
        return {"bubble_index": 20, "valuation_heat": 25}


def test_bottleneck_controllers_are_ranked_separately_from_beneficiaries() -> None:
    engine = BeneficiaryEngine(bubble_provider=StaticBubble())
    entities = [
        ThemeEntity("HBM", "company", "Micron Technology", "MU", 84),
        ThemeEntity("HBM", "supply_chain_role", "memory", "MU", 88),
        ThemeEntity("HBM", "company", "NVIDIA Corporation", "NVDA", 86),
        ThemeEntity("HBM", "supply_chain_role", "accelerator", "NVDA", 80),
    ]
    beneficiaries = [ThemeBeneficiary("HBM", "NVDA", "NVIDIA Corporation", 86, 84)]
    bottlenecks = [
        BottleneckRecord(
            "HBM",
            "HBM Capacity",
            "Capacity Constraint",
            88,
            84,
            45,
            90,
            86,
            controller_entities=[{"ticker": "MU", "company_name": "Micron Technology", "role": "capacity_owner", "relationship_strength": 90}],
            beneficiaries=[{"ticker": "NVDA", "company_name": "NVIDIA Corporation", "role": "beneficiary", "relationship_strength": 84}],
        )
    ]

    rows = engine.prepare(entities, beneficiaries, bottlenecks, [])
    by_ticker = {row.ticker: row for row in rows}

    assert by_ticker["MU"].beneficiary_type == "Bottleneck Controller"
    assert by_ticker["NVDA"].beneficiary_type != "Bottleneck Controller"

