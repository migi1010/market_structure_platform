from __future__ import annotations

import re

from theme_intelligence.models import CANONICAL_THEMES, THEME_ALIAS_MAP, normalize_theme_name


class ThemeExtractor:
    def __init__(self, alias_map: dict[str, str] | None = None) -> None:
        self.alias_map = alias_map or THEME_ALIAS_MAP
        aliases = sorted(self.alias_map.keys(), key=len, reverse=True)
        self._patterns = [
            (alias, re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", re.IGNORECASE))
            for alias in aliases
        ]

    def extract(self, text: str) -> list[str]:
        found: list[str] = []
        for alias, pattern in self._patterns:
            if pattern.search(text):
                theme = self.alias_map[alias]
                if theme not in found:
                    found.append(theme)
        for theme in CANONICAL_THEMES:
            if theme not in found and normalize_theme_name(theme) == theme and re.search(rf"(?<![a-z0-9]){re.escape(theme)}(?![a-z0-9])", text, re.IGNORECASE):
                found.append(theme)
        return found
