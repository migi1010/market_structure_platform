from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.lifecycle.lifecycle_engine import LifecycleEngine
from theme_intelligence.lifecycle.lifecycle_models import LifecycleInput


def test_lifecycle_confidence_bounds() -> None:
    engine = LifecycleEngine()
    result = engine.classify(
        LifecycleInput(
            theme_name="Glass Substrate",
            discovery_score=120,
            emerging_score=120,
            catalyst_score=120,
            entity_strength_score=120,
            confidence_score=120,
            crowding_proxy=-20,
            final_ai_score=120,
            key_catalysts=[],
            beneficiaries=[],
            source_count=5,
            history=[],
        )
    )

    assert 0 <= result.lifecycle_confidence <= 100


def test_lifecycle_engine_returns_explanation_fields() -> None:
    engine = LifecycleEngine()
    result = engine.classify(
        LifecycleInput(
            theme_name="Glass Substrate",
            discovery_score=86,
            emerging_score=82,
            catalyst_score=70,
            entity_strength_score=48,
            confidence_score=74,
            crowding_proxy=18,
            final_ai_score=80,
            key_catalysts=[{"confidence_score": 78}],
            beneficiaries=[{"ticker": "GLW"}],
            source_count=3,
            history=[],
        )
    )

    assert result.lifecycle_stage == "Early"
    assert result.expected_next_stage == "Growth"
    assert result.time_window == "1-6 months"
    assert result.stage_reason
    assert result.positive_signals
    assert result.next_stage_triggers
