from __future__ import annotations

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_builder import ThemeScoutBuilder
from theme_intelligence.industrial_graph.theme_scout_models import ThemeScoutProposal
from theme_intelligence.industrial_graph.theme_scout_repository import ThemeScoutRepository
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_snapshot_activation_and_rollback_are_transactional(tmp_path) -> None:
    repository = ThemeScoutRepository(ThemeRepository(tmp_path / "scout.sqlite3"))
    build = ThemeScoutBuilder().build(
        (),
        ThemeScoutProposal("fixed", "test", "v1", ()),
        "2026-06-10T00:00:00+00:00",
    )
    first = repository.stage(build)
    repository.activate(first.scout_version)
    second = repository.stage(build)
    repository.activate(second.scout_version)
    repository.rollback(second.scout_version)
    assert repository.get_active_snapshot().scout_version == first.scout_version


def test_failed_activation_preserves_current_snapshot(tmp_path) -> None:
    repository = ThemeScoutRepository(ThemeRepository(tmp_path / "scout.sqlite3"))
    build = ThemeScoutBuilder().build(
        (),
        ThemeScoutProposal("fixed", "test", "v1", ()),
        "2026-06-10T00:00:00+00:00",
    )
    first = repository.stage(build)
    repository.activate(first.scout_version)
    with pytest.raises(KeyError):
        repository.activate("missing")
    assert repository.get_active_snapshot().scout_version == first.scout_version
