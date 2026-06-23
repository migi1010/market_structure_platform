from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_isolation import (
    downstream_fingerprint,
)
from theme_intelligence.industrial_graph.theme_scout_models import ThemeScoutBuild
from theme_intelligence.industrial_graph.theme_scout_repository import ThemeScoutRepository
from theme_intelligence.storage.theme_repository import ThemeRepository


def _empty_build() -> ThemeScoutBuild:
    return ThemeScoutBuild(
        algorithm_version="test",
        provider_name="manual",
        provider_model="offline",
        prompt_version="v1",
        source_watermark="2026-06-14T00:00:00+00:00",
        evidence_bundle_checksum="a" * 64,
        proposal_checksum="b" * 64,
        candidates=(),
    )


def test_guarded_activation_preserves_downstream_fingerprint(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "isolation.sqlite3")
    scout = ThemeScoutRepository(repository)
    staged = scout.stage(_empty_build())
    before = downstream_fingerprint(repository)
    active = scout.activate_guarded(staged.scout_version)
    assert active.status == "active"
    assert downstream_fingerprint(repository) == before


def test_guarded_activation_rolls_back_on_isolation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = ThemeRepository(tmp_path / "rollback.sqlite3")
    scout = ThemeScoutRepository(repository)
    staged = scout.stage(_empty_build())

    def fail_guard(_conn, _before):
        raise ValueError("downstream isolation mismatch")

    monkeypatch.setattr(
        "theme_intelligence.industrial_graph.theme_scout_repository.verify_connection_isolation",
        fail_guard,
    )
    with pytest.raises(ValueError, match="isolation mismatch"):
        scout.activate_guarded(staged.scout_version)
    assert scout.get_active_snapshot() is None
    assert scout.get_snapshot(staged.scout_version).status == "validated"

