from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_builder_adds_only_explicit_curated_material_edges(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    build = IndustrialGraphBuilder(repository).build()
    edges = {edge.base_identity_key for edge in build.edges}

    assert (
        ("Process", "process:tsv_etching"),
        "PROCESS_REQUIRES_MATERIAL",
        ("Material", "material:photoresist"),
    ) in edges
    assert (
        ("Process", "process:packaging"),
        "PROCESS_REQUIRES_MATERIAL",
        ("Material", "material:underfill"),
    ) in edges
    assert (
        ("Process", "process:thermal_management"),
        "PROCESS_REQUIRES_MATERIAL",
        ("Material", "material:coolant"),
    ) in edges
    assert (
        ("Material", "material:ultra_thin_glass"),
        "MATERIAL_SUPPLIED_BY",
        ("Company", "company:GLW"),
    ) in edges
    assert not any(
        edge.relationship_type == "MATERIAL_SUPPLIED_BY"
        and edge.target_key == ("Company", "company:AMAT")
        for edge in build.edges
    )

    material_evidence = [
        row for row in build.evidence if row.source_type.startswith("seed:curated_material")
    ]
    assert material_evidence
    assert {row.citation for row in material_evidence} == {
        "Approved curated seed: Phase 12.5 material graph"
    }
