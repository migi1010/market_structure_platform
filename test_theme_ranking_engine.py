from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.theme_ranking.theme_ranking_engine import ThemeRankingEngine
from theme_intelligence.theme_ranking.theme_ranking_models import ThemeRankingSource


def source(**overrides: object) -> ThemeRankingSource:
    base = {
        "theme_id": "hbm",
        "theme_name": "HBM",
        "has_active_graph": True,
        "has_scout_signal": False,
        "scout_theme_score": 0.0,
        "scout_velocity_score": 0.0,
        "scout_evidence_count": 0,
        "scout_signal_count": 0,
        "research_case_count": 0,
        "approved_research_count": 0,
        "monitoring_research_count": 0,
        "controller_count": 0,
        "opportunity_count": 0,
        "graph_evidence_count": 0,
        "updated_at": "2026-06-21T00:00:00+00:00",
    }
    base.update(overrides)
    return ThemeRankingSource(**base)


def test_engine_scores_and_sorts_deterministically() -> None:
    rows = ThemeRankingEngine().rank_themes([
        source(theme_id="emerging", theme_name="Emerging", has_active_graph=False, has_scout_signal=True, scout_theme_score=85, scout_velocity_score=70, scout_evidence_count=6, scout_signal_count=3),
        source(theme_id="active", theme_name="Active", controller_count=3, opportunity_count=2, graph_evidence_count=8, research_case_count=1, approved_research_count=1),
        source(theme_id="declining", theme_name="Declining", has_active_graph=False, graph_evidence_count=1),
    ])

    assert [row.theme_id for row in rows] == ["active", "emerging", "declining"]
    assert [row.lifecycle for row in rows] == ["ACTIVE", "EMERGING", "DECLINING"]
    assert rows == ThemeRankingEngine().rank_themes(list(reversed([
        source(theme_id="emerging", theme_name="Emerging", has_active_graph=False, has_scout_signal=True, scout_theme_score=85, scout_velocity_score=70, scout_evidence_count=6, scout_signal_count=3),
        source(theme_id="active", theme_name="Active", controller_count=3, opportunity_count=2, graph_evidence_count=8, research_case_count=1, approved_research_count=1),
        source(theme_id="declining", theme_name="Declining", has_active_graph=False, graph_evidence_count=1),
    ])))


def test_engine_classifies_accelerating_and_monitoring_from_persisted_signals() -> None:
    accelerating = ThemeRankingEngine().rank_themes([
        source(
            theme_id="ai_power_grid",
            theme_name="AI Power Grid",
            has_active_graph=False,
            has_scout_signal=True,
            scout_theme_score=80,
            scout_velocity_score=80,
            scout_evidence_count=6,
            scout_signal_count=3,
            research_case_count=1,
        )
    ])[0]
    monitoring = ThemeRankingEngine().rank_themes([
        source(
            theme_id="cooling",
            theme_name="Cooling",
            has_active_graph=True,
            graph_evidence_count=6,
            research_case_count=1,
            monitoring_research_count=1,
        )
    ])[0]

    assert accelerating.lifecycle == "ACCELERATING"
    assert monitoring.lifecycle == "MONITORING"


def test_engine_merges_normalized_duplicate_theme_identities() -> None:
    rows = ThemeRankingEngine().rank_themes([
        source(
            theme_id="ai_infrastructure_constraint_watch",
            theme_name="AI Infrastructure Constraint Watch",
            has_active_graph=False,
            has_scout_signal=True,
            scout_theme_score=65,
            scout_velocity_score=20,
            scout_evidence_count=5,
            scout_signal_count=2,
        ),
        source(
            theme_id="ai-infrastructure-constraint-watch",
            theme_name="AI Infrastructure Constraint Watch",
            has_active_graph=False,
            research_case_count=1,
            monitoring_research_count=1,
        ),
    ])

    assert len(rows) == 1
    assert rows[0].theme_id == "ai_infrastructure_constraint_watch"
    assert rows[0].research_score > 0
    assert rows[0].evidence_score > 0
