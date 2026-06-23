from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.lifecycle.lifecycle_engine import LifecycleEngine, lifecycle_result_to_api
from theme_intelligence.lifecycle.lifecycle_models import LifecycleInput


def test_lifecycle_payload_includes_catalyst_explanation_fields() -> None:
    result = LifecycleEngine().classify(
        LifecycleInput(
            theme_name="Glass Substrate",
            discovery_score=72,
            emerging_score=66,
            catalyst_score=85,
            entity_strength_score=58,
            confidence_score=70,
            crowding_proxy=25,
            final_ai_score=74,
            key_catalysts=[
                {
                    "name": "Intel Packaging Expansion",
                    "type": "CapEx Expansion",
                    "catalyst_strength": 88,
                    "confidence_score": 87,
                    "timeline_status": "current",
                    "polarity": "positive",
                },
                {
                    "name": "HBM4 Adoption",
                    "type": "Product Launch",
                    "catalyst_strength": 76,
                    "confidence_score": 70,
                    "timeline_status": "future",
                    "polarity": "positive",
                },
                {
                    "name": "Yield Risk",
                    "type": "Technology Breakthrough",
                    "catalyst_strength": 64,
                    "confidence_score": 69,
                    "timeline_status": "current",
                    "polarity": "risk",
                },
            ],
            source_count=3,
            history=[],
        )
    )

    payload = lifecycle_result_to_api(result)

    assert payload["top_catalysts"][0]["name"] == "Intel Packaging Expansion"
    assert payload["future_catalysts"][0]["name"] == "HBM4 Adoption"
    assert payload["key_blockers"][0]["name"] == "Yield Risk"
    assert result.lifecycle_confidence >= 70
