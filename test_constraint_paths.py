from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.graph_models import (
    IndustrialGraphBuild,
    IndustrialGraphEdge,
    IndustrialGraphEdgeEvidence,
    IndustrialGraphEvidence,
    IndustrialGraphNode,
)
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def _repository(tmp_path: Path):
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    service.build_and_activate()
    return service.repository


def test_layer_to_constraint_traversal_succeeds(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    assert ("Constraint", "constraint:hbm_capacity") in repository.get_theme_constraints(("Theme", "hbm"))
    assert ("Constraint", "constraint:glass_substrate_yield") in repository.get_process_constraints(("Process", "process:glass_processing"))
    assert ("Constraint", "constraint:glass_substrate_yield") in repository.get_equipment_constraints(("Equipment", "equipment:yield_inspection"))


def test_constraint_dependency_paths_are_deterministic_and_bounded(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    source = ("Theme", "glass_substrate")
    target = ("Process", "process:glass_processing")
    first = repository.get_constraint_dependency_paths(source, target, max_depth=2)
    second = repository.get_constraint_dependency_paths(source, target, max_depth=2)
    assert first == second == [(
        source,
        ("Constraint", "constraint:glass_substrate_yield"),
        target,
    )]
    assert repository.get_constraint_dependency_paths(source, target, max_depth=1) == []


def test_material_to_constraint_traversal_supports_explicit_cited_edges(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "material-constraint.sqlite3")
    material = IndustrialGraphNode(
        "Material",
        "material:photoresist",
        "Photoresist",
        external_ids={"category": "Specialty Chemical"},
    )
    constraint = IndustrialGraphNode(
        "Constraint",
        "constraint:photoresist_availability",
        "Photoresist Availability Constraint",
        external_ids={"category": "Material Constraint"},
    )
    evidence = IndustrialGraphEvidence.from_payload(
        "seed:test_constraint",
        "photoresist:availability",
        "Explicit test evidence for material constraint traversal.",
        {"material": "photoresist", "constraint": "photoresist_availability"},
    )
    edge = IndustrialGraphEdge(
        material.identity_key,
        "MATERIAL_LIMITED_BY_CONSTRAINT",
        constraint.identity_key,
    )
    service = IndustrialGraphSnapshotService(repository)
    staged = service.stage(
        IndustrialGraphBuild(
            nodes=(material, constraint),
            edges=(edge,),
            evidence=(evidence,),
            edge_evidence=(
                IndustrialGraphEdgeEvidence(edge.base_identity_key, evidence.identity_key),
            ),
        )
    )
    service.activate(staged.build_version)
    assert service.repository.get_material_constraints(material.identity_key) == [
        constraint.identity_key
    ]
