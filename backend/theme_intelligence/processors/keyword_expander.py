from __future__ import annotations

import re

from theme_intelligence.models import THEME_ALIAS_MAP, normalize_theme_name


EXPANDED_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Glass Substrate": (
        "glass substrate",
        "glass core substrate",
        "advanced packaging substrate",
        "panel level packaging",
        "panel-level packaging",
    ),
    "HBM": (
        "hbm",
        "hbm3e",
        "high bandwidth memory",
        "memory stack",
        "stacked memory",
    ),
    "CoWoS": (
        "cowos",
        "chip on wafer on substrate",
        "chip-on-wafer-on-substrate",
        "advanced packaging capacity",
    ),
    "AI Infrastructure": (
        "ai infrastructure",
        "ai infra",
        "ai server",
        "ai datacenter",
        "ai data center",
        "accelerator cluster",
    ),
    "Advanced Packaging": (
        "advanced packaging",
        "chip packaging",
        "semiconductor packaging",
        "hybrid bonding",
        "interposer",
    ),
    "Power Grid": (
        "power grid",
        "electric grid",
        "transformer",
        "grid modernization",
        "datacenter power",
    ),
    "Robotics": (
        "robotics",
        "robot",
        "automation",
        "warehouse automation",
        "industrial robot",
    ),
    "Optical Interconnect": (
        "optical interconnect",
        "optical interconnects",
        "silicon photonics",
        "optical connectivity",
    ),
    "CPO Photonics": (
        "cpo",
        "cpo photonics",
        "co packaged optics",
        "co-packaged optics",
        "co-packaged photonics",
        "cpo optical engine",
    ),
    "Edge AI": (
        "edge ai",
        "on device ai",
        "on-device ai",
        "ai pc",
        "edge inference",
        "embedded ai",
    ),
    "Data Center Cooling": (
        "data center cooling",
        "datacenter cooling",
        "liquid cooling",
        "immersion cooling",
        "thermal management",
        "ai cooling",
    ),
    "Humanoid Robot": (
        "humanoid robot",
        "humanoid robotics",
        "humanoid robots",
    ),
    "Satellite": ("satellite", "satellites", "space network", "leo constellation"),
    "Quantum": ("quantum", "quantum computing", "quantum computer"),
    "Nuclear": ("nuclear", "nuclear energy", "small modular reactor", "uranium"),
}


class KeywordExpander:
    def __init__(self, expansions: dict[str, tuple[str, ...]] | None = None) -> None:
        self.expansions = expansions or self._merged_expansions()

    def keywords_for(self, theme_name: str) -> tuple[str, ...]:
        canonical = normalize_theme_name(theme_name) or theme_name
        return self.expansions.get(canonical, (canonical.lower(),))

    def match(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        matches: list[str] = []
        for theme, keywords in self.expansions.items():
            for keyword in keywords:
                pattern = self._normalize(keyword)
                if re.search(rf"(?<![a-z0-9]){re.escape(pattern)}(?![a-z0-9])", normalized):
                    matches.append(theme)
                    break
        return matches

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()

    @staticmethod
    def _merged_expansions() -> dict[str, tuple[str, ...]]:
        merged: dict[str, list[str]] = {theme: list(values) for theme, values in EXPANDED_KEYWORDS.items()}
        for alias, theme in THEME_ALIAS_MAP.items():
            merged.setdefault(theme, [])
            if alias not in merged[theme]:
                merged[theme].append(alias)
        return {theme: tuple(values) for theme, values in merged.items()}
