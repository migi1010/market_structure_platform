from __future__ import annotations

from datetime import UTC, datetime

from theme_intelligence.storage.theme_repository import ThemeRepository

from .theme_ranking_engine import THEME_RANKING_ALGORITHM_VERSION, ThemeRankingEngine
from .theme_ranking_repository import ThemeRankingRepository


def export_theme_ranking(repository: ThemeRepository | None = None) -> dict:
    ranking_repository = ThemeRankingRepository(repository)
    engine = ThemeRankingEngine()
    themes = engine.rank_themes(ranking_repository.load_theme_sources())
    return {
        "available": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "algorithm_version": THEME_RANKING_ALGORITHM_VERSION,
        "weights": engine.weights.to_dict(),
        "themes": [row.to_dict() for row in themes],
    }
