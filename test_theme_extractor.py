from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.models import normalize_theme_name
from theme_intelligence.processors.theme_extractor import ThemeExtractor


def test_theme_alias_normalization() -> None:
    assert normalize_theme_name("AI infra") == "AI Infrastructure"
    assert normalize_theme_name("AI server") == "AI Infrastructure"
    assert normalize_theme_name("Glass Core Substrate") == "Glass Substrate"


def test_theme_extractor_detects_supported_themes() -> None:
    extractor = ThemeExtractor()
    themes = extractor.extract("NVIDIA Blackwell demand boosts HBM, CoWoS, and advanced packaging capacity.")
    assert "HBM" in themes
    assert "CoWoS" in themes
    assert "Advanced Packaging" in themes
