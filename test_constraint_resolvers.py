from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_resolver_and_exposure_tracing_remain_distinct(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    service.build_and_activate()

    assert service.repository.get_constraint_resolvers(
        ("Constraint", "constraint:cowos_capacity")
    ) == [("Company", "company:TSM")]
    assert service.repository.get_constraint_exposed_companies(
        ("Constraint", "constraint:hbm_capacity")
    ) == [
        ("Company", "company:000660.KS"),
        ("Company", "company:005930.KS"),
        ("Company", "company:MU"),
    ]
