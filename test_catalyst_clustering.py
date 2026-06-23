from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.catalysts.catalyst_classifier import CatalystClassifier
from theme_intelligence.catalysts.catalyst_clusterer import CatalystClusterer


def test_intel_packaging_variants_cluster_into_one_event() -> None:
    classifier = CatalystClassifier()
    clusterer = CatalystClusterer()
    raw = [
        classifier.classify("Glass Substrate", "Intel advanced packaging expansion", "finnhub", "INTC"),
        classifier.classify("Glass Substrate", "Intel substrate investment", "fmp", "INTC"),
        classifier.classify("Glass Substrate", "Intel packaging capacity increase", "sec_filings", "INTC"),
    ]

    clustered = clusterer.cluster(raw)

    assert len(clustered) == 1
    event = clustered[0]
    assert event.catalyst_name == "Intel Packaging Expansion"
    assert event.cluster_key == "glass_substrate:intel:packaging_expansion"
    assert event.source == "finnhub,fmp,sec_filings"

