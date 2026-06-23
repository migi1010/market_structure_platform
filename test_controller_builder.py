from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.controller_builder import ControllerBuilder
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_controller_build_is_deterministic_and_uses_explicit_evidence(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "controller.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    IndustrialGraphSnapshotService(repository).build_and_activate()
    builder = ControllerBuilder(repository)
    first = builder.build()
    second = builder.build()
    assert first == second
    assert [row.rank for row in first.controllers] == list(range(1, len(first.controllers) + 1))
    assert all(row.evidence_ids and row.coverage >= 0 for row in first.controllers)

    klac = next(row for row in first.controllers if row.company_key == ("Company", "company:KLAC"))
    assert klac.equipment_control > 0
    assert "Equipment Controller" in klac.controller_types

    tsm = next(row for row in first.controllers if row.company_key == ("Company", "company:TSM"))
    assert tsm.constraint_influence > 0
    assert "Capacity Controller" in tsm.controller_types
    assert "Constraint Controller" in tsm.controller_types

    controller_keys = {row.company_key[1] for row in first.controllers}
    assert {"company:000660.KS", "company:005930.KS", "company:MU"}.isdisjoint(controller_keys)
    assert "company:MSFT" not in controller_keys

    applicable = (
        klac.dependency_score,
        klac.constraint_influence,
        klac.resolution_influence,
        klac.equipment_control,
        klac.material_control,
        klac.process_control,
        klac.technology_control,
    )
    assert klac.coverage == round(100 * sum(value > 0 for value in applicable) / len(applicable), 6)
