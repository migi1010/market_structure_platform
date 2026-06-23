from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def _repository(tmp_path: Path):
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    service.build_and_activate()
    return service.repository


def test_theme_and_technology_traversal_succeeds(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    assert ("Technology", "technology:tsv") in repository.get_theme_technologies(
        ("Theme", "hbm")
    )
    assert repository.get_technology_processes(
        ("Technology", "technology:tsv")
    ) == [
        ("Process", "process:tsv_etching"),
        ("Process", "process:wafer_bonding"),
    ]


def test_process_dependency_paths_are_deterministic_and_bounded(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source = ("Process", "process:wafer_bonding")
    target = ("Process", "process:qualification")

    first = repository.get_process_paths(source, target, max_depth=2)
    second = repository.get_process_paths(source, target, max_depth=2)

    assert first == second == [(
        ("Process", "process:wafer_bonding"),
        ("Process", "process:yield_inspection"),
        ("Process", "process:qualification"),
    )]
    assert repository.get_process_paths(source, target, max_depth=1) == []
    assert repository.get_process_dependencies(source, max_depth=1) == [
        ("Process", "process:yield_inspection")
    ]
