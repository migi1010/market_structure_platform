from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.lifecycle.lifecycle_history import append_lifecycle_snapshot


def test_lifecycle_history_append_limits_and_preserves_latest() -> None:
    history = "[]"
    for index in range(125):
        history = append_lifecycle_snapshot(
            history,
            {
                "timestamp": f"2026-06-05T00:{index:02d}:00+00:00",
                "lifecycle_stage": "Seed",
                "lifecycle_confidence": index,
                "expected_next_stage": "Early",
                "final_ai_score": index,
                "emerging_score": index,
                "catalyst_score": index,
                "entity_strength_score": index,
                "crowding_proxy": index,
            },
        )

    parsed = json.loads(history)
    assert len(parsed) == 120
    assert parsed[-1]["final_ai_score"] == 124
    assert parsed[0]["final_ai_score"] == 5
