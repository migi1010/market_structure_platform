"""Master theme score engine exports."""

from .theme_score_models import ThemeFinalScore, ThemeScoreInput


def get_theme_scores():
    from .theme_score_engine import ThemeScoreEngine

    return ThemeScoreEngine().get_scores()


def get_theme_score_detail(theme_id: str):
    from .theme_score_engine import ThemeScoreEngine

    return ThemeScoreEngine().get_score_detail(theme_id)


__all__ = [
    "ThemeFinalScore",
    "ThemeScoreInput",
    "get_theme_scores",
    "get_theme_score_detail",
]
