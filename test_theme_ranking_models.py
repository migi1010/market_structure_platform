from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_ranking.theme_ranking_models import (
    THEME_RANKING_LIFECYCLES,
    ThemeRank,
    ThemeRankingWeights,
)


def test_theme_rank_validates_lifecycle_and_score_bounds() -> None:
    rank = ThemeRank(
        theme_id="hbm",
        theme_name="HBM",
        lifecycle="ACTIVE",
        rank_score=82.5,
        momentum_score=40,
        evidence_score=90,
        research_score=70,
        controller_score=80,
        opportunity_score=75,
        updated_at="2026-06-21T00:00:00+00:00",
    )

    assert THEME_RANKING_LIFECYCLES == (
        "EMERGING",
        "ACCELERATING",
        "ACTIVE",
        "MONITORING",
        "DECLINING",
    )
    assert rank.to_dict()["theme_id"] == "hbm"
    assert rank.to_dict()["lifecycle"] == "ACTIVE"

    with pytest.raises(ValueError, match="unsupported lifecycle"):
        ThemeRank(
            theme_id="bad",
            theme_name="Bad",
            lifecycle="APPROVED",
            rank_score=50,
            momentum_score=50,
            evidence_score=50,
            research_score=50,
            controller_score=50,
            opportunity_score=50,
            updated_at="2026-06-21T00:00:00+00:00",
        )

    with pytest.raises(ValueError, match="rank_score"):
        ThemeRank(
            theme_id="bad",
            theme_name="Bad",
            lifecycle="ACTIVE",
            rank_score=-1,
            momentum_score=50,
            evidence_score=50,
            research_score=50,
            controller_score=50,
            opportunity_score=50,
            updated_at="2026-06-21T00:00:00+00:00",
        )


def test_theme_ranking_weights_are_backend_configurable_and_normalized() -> None:
    weights = ThemeRankingWeights()

    assert weights.to_dict() == {
        "evidence": 0.30,
        "research": 0.20,
        "controller": 0.20,
        "opportunity": 0.20,
        "momentum": 0.10,
    }

    with pytest.raises(ValueError, match="sum to 1.0"):
        ThemeRankingWeights(evidence=1, research=1, controller=0, opportunity=0, momentum=0)
