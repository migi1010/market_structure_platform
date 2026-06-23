from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.discovery.discovery_models import THEME_ZH
from theme_intelligence.seeds.seed_validator import contains_mojibake


def test_theme_chinese_labels_are_present_and_not_mojibake() -> None:
    expected = {
        "Glass Substrate": "玻璃基板",
        "HBM": "高頻寬記憶體",
        "CoWoS": "CoWoS先進封裝",
        "AI Infrastructure": "AI基礎設施",
        "Advanced Packaging": "先進封裝",
        "Power Grid": "電力電網",
        "CPO Photonics": "CPO光子互連",
        "Robotics": "機器人",
        "Edge AI": "邊緣AI",
        "Data Center Cooling": "資料中心冷卻",
    }

    for theme, label in expected.items():
        assert THEME_ZH[theme] == label
        assert not contains_mojibake(label)
