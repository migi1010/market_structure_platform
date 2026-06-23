from __future__ import annotations

from pathlib import Path

from test_opportunity_builder import build_controller_repository

from theme_intelligence.industrial_graph.opportunity_builder import OpportunityBuilder


def test_opportunity_ranking_is_deterministic(tmp_path: Path) -> None:
    repository, controller = build_controller_repository(tmp_path)
    first = OpportunityBuilder(repository).build(controller.controller_version)
    second = OpportunityBuilder(repository).build(controller.controller_version)
    assert [row.company_key for row in first.opportunities] == [
        row.company_key for row in second.opportunities
    ]
    assert [row.rank for row in first.opportunities] == list(
        range(1, len(first.opportunities) + 1)
    )
