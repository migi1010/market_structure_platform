from __future__ import annotations

from theme_intelligence.graph.graph_models import ThemeOverlap


def rank_overlaps(rows: list[ThemeOverlap], theme_id: str) -> list[ThemeOverlap]:
    matches = [row for row in rows if theme_id in {row.theme_id, row.related_theme_id}]
    return sorted(matches, key=lambda row: (-row.overlap_score, row.related_theme_id, row.theme_id))
