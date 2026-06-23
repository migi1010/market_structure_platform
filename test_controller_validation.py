from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.controller_builder import ControllerBuilder
from theme_intelligence.industrial_graph.controller_models import ControllerBuild
from theme_intelligence.industrial_graph.controller_validator import (
    ControllerValidationError,
    ControllerValidator,
)
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def _build(tmp_path: Path):
    repository = ThemeRepository(tmp_path / "controller.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    service.build_and_activate()
    return service.repository, ControllerBuilder(repository).build()


def test_controller_validator_accepts_reproducible_build(tmp_path: Path) -> None:
    repository, build = _build(tmp_path)
    ControllerValidator().validate(build, repository)


def test_controller_validator_rejects_missing_snapshot_and_duplicate_company(tmp_path: Path) -> None:
    repository, build = _build(tmp_path)
    bad = ControllerBuild(
        graph_snapshot_id=0,
        graph_build_version=build.graph_build_version,
        algorithm_version=build.algorithm_version,
        metrics=build.metrics,
        controllers=build.controllers + (build.controllers[0],),
    )
    with pytest.raises(ControllerValidationError, match="snapshot|duplicate"):
        ControllerValidator().validate(bad, repository)


def test_controller_models_reject_negative_scores(tmp_path: Path) -> None:
    _, build = _build(tmp_path)
    with pytest.raises(ValueError, match="between 0 and 100"):
        replace(build.controllers[0], controller_score=-1)
