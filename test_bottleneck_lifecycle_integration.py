from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.lifecycle.lifecycle_engine import LifecycleEngine, lifecycle_result_to_api
from theme_intelligence.lifecycle.lifecycle_models import LifecycleInput


def test_lifecycle_explanation_uses_bottlenecks_without_forcing_stage() -> None:
    result = LifecycleEngine().classify(
        LifecycleInput(
            theme_name="Glass Substrate",
            discovery_score=52,
            emerging_score=58,
            catalyst_score=48,
            entity_strength_score=42,
            confidence_score=55,
            crowding_proxy=22,
            final_ai_score=54,
            key_bottlenecks=[
                {
                    "name": "Yield",
                    "type": "Yield Constraint",
                    "severity_score": 88,
                    "resolution_probability": 55,
                    "bottleneck_strength": 82,
                    "what_fixes_it": ["Yield improvement"],
                }
            ],
            source_count=2,
            history=[],
        )
    )

    payload = lifecycle_result_to_api(result)

    assert result.lifecycle_stage == "Early"
    assert payload["primary_bottleneck"]["name"] == "Yield"
    assert any("Yield" in risk for risk in payload["stage_risks"])
    assert any("Yield improvement" in trigger for trigger in payload["next_stage_triggers"])

