from __future__ import annotations

from pathlib import Path

from test_opportunity_builder import build_controller_repository

from theme_intelligence.industrial_graph.opportunity_builder import OpportunityBuilder


def test_reasoning_paths_are_preserved_and_theme_first_when_available(
    tmp_path: Path,
) -> None:
    repository, controller = build_controller_repository(tmp_path)
    build = OpportunityBuilder(repository).build(controller.controller_version)
    tsm = next(
        row
        for row in build.opportunities
        if row.company_key == ("Company", "company:TSM")
    )
    assert tsm.reasoning_paths
    assert any(
        path[0][0] == "Theme" and path[-1] == tsm.company_key
        for path in tsm.reasoning_paths
    )
    assert len(tsm.reasoning_paths) <= 25


def test_unavailable_path_bound_market_inputs_reduce_confidence(
    tmp_path: Path,
) -> None:
    repository, controller = build_controller_repository(tmp_path)
    build = OpportunityBuilder(repository).build(controller.controller_version)
    klac = next(
        row
        for row in build.opportunities
        if row.company_key == ("Company", "company:KLAC")
    )
    assert klac.reasoning_paths
    assert klac.coverage_component == 85.0
    assert klac.coverage_confidence < 100.0
