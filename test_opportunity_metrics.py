from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.opportunity_models import (
    OPPORTUNITY_WEIGHTS,
    MarketComponent,
    MarketSourceRecord,
)


def test_opportunity_weights_sum_to_one() -> None:
    assert sum(OPPORTUNITY_WEIGHTS.values()) == pytest.approx(1.0)


def test_unavailable_market_component_cannot_be_favorable() -> None:
    with pytest.raises(ValueError, match="unavailable market component"):
        MarketComponent(
            name="valuation_component",
            raw_value=0.0,
            normalized_value=100.0,
            availability_state="unavailable",
            configured_weight=0.05,
            applied_weight=0.0,
            source_records=(),
            unavailable_reason="ambiguous_zero",
        )


def test_available_market_component_requires_source_provenance() -> None:
    with pytest.raises(ValueError, match="source records"):
        MarketComponent(
            name="bubble_risk_component",
            raw_value=25.0,
            normalized_value=75.0,
            availability_state="available",
            configured_weight=0.05,
            applied_weight=0.05,
            source_records=(),
        )


def test_market_source_record_preserves_persisted_value() -> None:
    source = MarketSourceRecord(
        source_table="theme_beneficiary_scores",
        source_record_key={"id": "7", "theme_name": "HBM"},
        source_timestamp="2026-06-12T00:00:00+00:00",
        source_value=20.0,
    )
    assert source.source_value == 20.0
    assert source.source_table == "theme_beneficiary_scores"
