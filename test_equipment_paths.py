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


def test_process_and_theme_equipment_traversal_succeeds(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    assert repository.get_process_equipment(("Process", "process:tsv_etching")) == [
        ("Equipment", "equipment:advanced_etch")
    ]
    assert ("Equipment", "equipment:advanced_etch") in repository.get_theme_equipment(
        ("Theme", "hbm")
    )


def test_equipment_dependency_paths_are_deterministic_and_bounded(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source = ("Technology", "technology:tsv")
    target = ("Equipment", "equipment:advanced_etch")
    expected = [(source, ("Process", "process:tsv_etching"), target)]
    assert repository.get_equipment_dependency_paths(source, target, max_depth=2) == expected
    assert repository.get_equipment_dependency_paths(source, target, max_depth=2) == expected
    assert repository.get_equipment_dependency_paths(source, target, max_depth=1) == []
