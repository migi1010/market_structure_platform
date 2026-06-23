from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.bottlenecks.bottleneck_classifier import BottleneckClassifier


def test_bottleneck_classifier_supports_required_types() -> None:
    classifier = BottleneckClassifier()
    cases = {
        "HBM capacity remains tight for AI accelerators": "Capacity Constraint",
        "Glass substrate yield limits panel level packaging": "Yield Constraint",
        "Specialty chemicals and glass materials are constrained": "Material Constraint",
        "Packaging equipment and inspection tools are a bottleneck": "Equipment Constraint",
        "AI engineers and semiconductor engineers remain scarce": "Talent Constraint",
        "Power grid and cooling limit datacenter availability": "Infrastructure Constraint",
        "Single supplier dependency creates geographic concentration risk": "Supply Chain Constraint",
        "Export controls and policy restrictions limit shipments": "Regulatory Constraint",
    }

    for text, expected_type in cases.items():
        result = classifier.classify("AI Infrastructure", text, source="finnhub")
        assert result.bottleneck_type == expected_type
        assert result.bottleneck_name
        assert result.description

