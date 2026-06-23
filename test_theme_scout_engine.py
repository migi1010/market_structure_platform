from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_engine import ThemeScoutEngine
from theme_intelligence.industrial_graph.theme_scout_models import ThemeScoutProposal
from theme_intelligence.storage.theme_repository import ThemeRepository


class FixedProvider:
    provider_name = "fixed"
    provider_model = "test"
    prompt_version = "v1"

    def propose(self, evidence):
        return ThemeScoutProposal(
            self.provider_name,
            self.provider_model,
            self.prompt_version,
            (),
        )


def test_identical_input_produces_identical_content_checksum(tmp_path) -> None:
    engine = ThemeScoutEngine(
        ThemeRepository(tmp_path / "scout.sqlite3"),
        provider=FixedProvider(),
    )
    first = engine.build(source_watermark="2026-06-10T00:00:00+00:00")
    second = engine.build(source_watermark="2026-06-10T00:00:00+00:00")
    assert first.checksum == second.checksum


def test_engine_does_not_require_downstream_snapshots(tmp_path) -> None:
    engine = ThemeScoutEngine(
        ThemeRepository(tmp_path / "scout.sqlite3"),
        provider=FixedProvider(),
    )
    snapshot = engine.build_and_activate(
        source_watermark="2026-06-10T00:00:00+00:00"
    )
    assert snapshot.status == "active"
