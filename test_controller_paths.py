from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.controller_builder import ControllerBuilder
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_reasoning_paths_are_bounded_deterministic_and_evidence_backed(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "controller.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    IndustrialGraphSnapshotService(repository).build_and_activate()
    builder = ControllerBuilder(repository)
    projection = builder.build_projection()
    first = builder.reasoning_paths(projection, ("Company", "company:KLAC"))
    second = builder.reasoning_paths(projection, ("Company", "company:KLAC"))
    assert first == second
    assert first
    assert all(path[0] == ("Company", "company:KLAC") and len(path) <= 5 for path in first)
    assert all(
        projection[path[index]][path[index + 1]]["evidence_ids"]
        for path in first
        for index in range(len(path) - 1)
    )
