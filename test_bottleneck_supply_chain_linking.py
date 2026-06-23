from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.bottlenecks.bottleneck_resolver import BottleneckResolver
from theme_intelligence.models import ThemeBeneficiary, ThemeEntity


def test_bottleneck_resolver_separates_controllers_from_beneficiaries() -> None:
    resolver = BottleneckResolver()
    bottleneck = BottleneckRecord(
        theme_name="HBM",
        bottleneck_name="HBM Capacity",
        bottleneck_type="Capacity Constraint",
        severity_score=86,
        duration_score=82,
        resolution_probability=45,
        impact_score=88,
        bottleneck_strength=84,
        controller_entities=[],
        beneficiaries=[],
        timeline_status="current",
        description="HBM capacity remains tight.",
        evidence=[],
        updated_at="2026-06-05T00:00:00+00:00",
    )
    entities = [
        ThemeEntity("HBM", "company", "Micron Technology", "MU", 82),
        ThemeEntity("HBM", "supply_chain_role", "memory", "MU", 84),
        ThemeEntity("HBM", "company", "NVIDIA Corporation", "NVDA", 88),
        ThemeEntity("HBM", "supply_chain_role", "accelerator", "NVDA", 80),
    ]
    beneficiaries = [ThemeBeneficiary("HBM", "NVDA", "NVIDIA Corporation", 90, 86)]

    resolved = resolver.resolve(bottleneck, entities, beneficiaries)

    controller_tickers = {item["ticker"] for item in resolved.controller_entities}
    beneficiary_tickers = {item["ticker"] for item in resolved.beneficiaries}
    assert "MU" in controller_tickers
    assert "NVDA" not in controller_tickers
    assert "NVDA" in beneficiary_tickers
