from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.processors.keyword_expander import KeywordExpander


def test_keyword_expansion_covers_related_concepts() -> None:
    expander = KeywordExpander()

    assert "Glass Substrate" in expander.match("Panel level packaging and advanced packaging substrate capacity expands")
    assert "HBM" in expander.match("HBM3E memory stack demand rises with AI accelerators")
    assert "CoWoS" in expander.match("Chip-on-wafer-on-substrate bottlenecks remain tight")
    assert "CPO Photonics" in expander.match("CPO photonics and co-packaged optics gain customer adoption")
    assert "Optical Interconnect" in expander.match("Optical interconnect bandwidth demand rises in AI clusters")
    assert "Edge AI" in expander.match("On-device AI and AI PC product launches expand edge inference")
    assert "Data Center Cooling" in expander.match("Liquid cooling demand rises with AI rack density")


def test_keyword_expansion_preserves_canonical_aliases() -> None:
    expander = KeywordExpander()

    assert expander.keywords_for("Glass Substrate")[0] == "glass substrate"
    assert "glass core substrate" in expander.keywords_for("Glass Substrate")
