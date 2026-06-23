from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_builder_adds_only_explicit_curated_equipment_edges(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    build = IndustrialGraphBuilder(repository).build()
    edges = {edge.base_identity_key for edge in build.edges}

    assert (("Process", "process:tsv_etching"), "PROCESS_REQUIRES_EQUIPMENT",
            ("Equipment", "equipment:advanced_etch")) in edges
    assert (("Equipment", "equipment:advanced_etch"), "EQUIPMENT_PRODUCED_BY",
            ("Company", "company:AMAT")) in edges
    assert (("Equipment", "equipment:yield_inspection"), "EQUIPMENT_PRODUCED_BY",
            ("Company", "company:KLAC")) in edges
    assert (("Equipment", "equipment:optical_testing_equipment"), "EQUIPMENT_PRODUCED_BY",
            ("Company", "company:TER")) in edges

    equipment_nodes = [node for node in build.nodes if node.node_type == "Equipment"]
    assert equipment_nodes
    assert all(node.canonical_key.count(":") == 1 for node in equipment_nodes)
    assert not any("equipment_supplier" in node.canonical_key for node in equipment_nodes)
    evidence = [row for row in build.evidence if row.source_type == "seed:curated_equipment"]
    assert evidence
    assert {row.citation for row in evidence} == {
        "Approved curated seed: Phase 12.6 equipment graph"
    }
