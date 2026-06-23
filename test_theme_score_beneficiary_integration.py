from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_score.theme_score_scorer import compute_beneficiary_quality


def test_beneficiary_quality_uses_all_required_components() -> None:
    quality = compute_beneficiary_quality(
        [
            {"allocation_score": 90, "beneficiary_score": 88, "beneficiary_type": "Direct Beneficiary"},
            {"allocation_score": 82, "beneficiary_score": 84, "beneficiary_type": "Bottleneck Controller"},
            {"allocation_score": 76, "beneficiary_score": 80, "beneficiary_type": "Resolution Enabler"},
        ]
    )

    assert quality > 80

