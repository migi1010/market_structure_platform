from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from test_opportunity_builder import build_controller_repository

from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository
from theme_intelligence.industrial_graph.opportunity_builder import OpportunityBuilder
from theme_intelligence.industrial_graph.opportunity_validator import (
    OpportunityValidationError,
    OpportunityValidator,
)


def test_validator_rejects_missing_evidence(tmp_path: Path) -> None:
    repository, controller = build_controller_repository(tmp_path)
    build = OpportunityBuilder(repository).build(controller.controller_version)
    damaged = replace(
        build,
        opportunities=(
            replace(build.opportunities[0], evidence_ids=()),
            *build.opportunities[1:],
        ),
    )
    with pytest.raises(OpportunityValidationError, match="missing evidence"):
        OpportunityValidator().validate(
            damaged, IndustrialGraphRepository(repository)
        )


def test_validator_rejects_snapshot_mismatch(tmp_path: Path) -> None:
    repository, controller = build_controller_repository(tmp_path)
    build = OpportunityBuilder(repository).build(controller.controller_version)
    with pytest.raises(OpportunityValidationError, match="snapshot reference"):
        OpportunityValidator().validate(
            replace(build, graph_snapshot_id=build.graph_snapshot_id + 999),
            IndustrialGraphRepository(repository),
        )
