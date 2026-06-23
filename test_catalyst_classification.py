from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.models import ThemeMention
from theme_intelligence.catalysts.catalyst_classifier import CatalystClassifier
from theme_intelligence.processors.catalyst_extractor import CatalystExtractor


def test_catalyst_extractor_classifies_required_types() -> None:
    extractor = CatalystExtractor()
    mentions = [
        ThemeMention("HBM", "finnhub", "NVDA", "NVIDIA Blackwell product launch boosts HBM3E", "2026-06-05T00:00:00+00:00", 74),
        ThemeMention("Power Grid", "fmp", "ETN", "AI datacenter capex expands transformer orders", "2026-06-05T00:00:00+00:00", 70),
        ThemeMention("Nuclear", "sec_filings", "CEG", "New policy supports nuclear power contracts", "2026-06-05T00:00:00+00:00", 67),
        ThemeMention("CoWoS", "finnhub", "TSM", "Supply shortage in advanced packaging capacity", "2026-06-05T00:00:00+00:00", 42),
        ThemeMention("Optical Interconnect", "fmp", "AVGO", "Customer adoption rises for CPO photonics", "2026-06-05T00:00:00+00:00", 71),
    ]

    catalysts = extractor.extract(mentions)
    types = {item.catalyst_type for item in catalysts}

    assert "Product Launch" in types
    assert "CapEx Expansion" in types
    assert "Policy / Regulation" in types
    assert "Supply Shortage" in types
    assert "Customer Adoption" in types


def test_catalyst_classifier_supports_phase_10_4_types() -> None:
    classifier = CatalystClassifier()
    cases = {
        "NVIDIA Blackwell product launch drives HBM demand": "Product Launch",
        "Intel packaging investment expands substrate capacity": "CapEx Expansion",
        "Management commentary raises guidance on AI server demand": "Earnings Call Signal",
        "HBM shortage creates tight supply for accelerators": "Supply Shortage",
        "Glass substrate yield improvement enables new packaging process": "Technology Breakthrough",
        "Hyperscaler deployment confirms customer adoption": "Customer Adoption",
        "Government subsidy supports AI infrastructure spending": "Policy / Regulation",
        "Datacenter demand accelerates transformer orders": "Industry Demand",
    }

    for headline, expected_type in cases.items():
        classified = classifier.classify("Glass Substrate", headline, source="finnhub", symbol="INTC")
        assert classified.catalyst_type == expected_type
        assert classified.description
