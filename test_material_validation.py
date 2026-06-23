from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_models import IndustrialGraphBuild, IndustrialGraphEdge, IndustrialGraphNode
from theme_intelligence.industrial_graph.graph_models import (
    IndustrialGraphEdgeEvidence,
    IndustrialGraphEvidence,
)
from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator
from theme_intelligence.seeds import TARGET_SEED_THEMES, ThemeSeedLoader
from theme_intelligence.seeds.theme_seed_models import (
    SeedMaterial,
    SeedMaterialSubstitutionLink,
    SeedMaterialSupplierLink,
    SeedProcessMaterialLink,
)
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_duplicate_and_orphan_material_nodes_are_rejected() -> None:
    material = IndustrialGraphNode(
        "Material",
        "material:photoresist",
        "Photoresist",
        external_ids={"category": "Specialty Chemical"},
    )
    with pytest.raises(GraphValidationError, match="duplicate canonical node"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(material, material)))
    with pytest.raises(GraphValidationError, match="orphan material"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(material,)))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {"materials": (SeedMaterial("bad", "Bad", "Unknown", "citation"),)},
            "unknown material category",
        ),
        (
            {"materials": (SeedMaterial("photoresist", "Photoresist", "Specialty Chemical", ""),)},
            "material missing citation",
        ),
        (
            {
                "process_material_links": (
                    SeedProcessMaterialLink(
                        "tsv_etching",
                        "photoresist",
                        "PROCESS_REQUIRES_MATERIAL",
                        "",
                    ),
                )
            },
            "material relationship missing citation",
        ),
        (
            {
                "material_supplier_links": (
                    SeedMaterialSupplierLink("photoresist", "MISSING", "citation"),
                )
            },
            "unknown material supplier ticker",
        ),
        (
            {
                "process_material_links": (
                    SeedProcessMaterialLink("missing_process", "photoresist", "PROCESS_REQUIRES_MATERIAL", "citation"),
                )
            },
            "unknown process material endpoint",
        ),
        (
            {
                "material_substitution_links": (
                    SeedMaterialSubstitutionLink("photoresist", "photoresist", "citation"),
                )
            },
            "material substitution self-link",
        ),
    ],
)
def test_material_seed_validation_rejects_invalid_records(changes, message: str) -> None:
    hbm = next(theme for theme in TARGET_SEED_THEMES if theme.theme_id == "hbm")
    invalid = replace(hbm, **changes)
    with pytest.raises(GraphValidationError, match=message):
        GraphValidator().validate_material_seeds((invalid,))


def test_invalid_material_relationship_endpoints_are_rejected() -> None:
    theme = IndustrialGraphNode("Theme", "hbm", "HBM")
    material = IndustrialGraphNode(
        "Material",
        "material:photoresist",
        "Photoresist",
        external_ids={"category": "Specialty Chemical"},
    )
    edge = IndustrialGraphEdge(
        theme.identity_key,
        "PROCESS_REQUIRES_MATERIAL",
        material.identity_key,
    )
    with pytest.raises(GraphValidationError, match="invalid process-material edge"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(theme, material), edges=(edge,)))


def test_material_edge_without_evidence_is_rejected() -> None:
    process = IndustrialGraphNode("Process", "process:packaging", "Packaging")
    material = IndustrialGraphNode(
        "Material",
        "material:underfill",
        "Underfill",
        external_ids={"category": "Encapsulation Material"},
    )
    edge = IndustrialGraphEdge(
        process.identity_key,
        "PROCESS_REQUIRES_MATERIAL",
        material.identity_key,
    )
    with pytest.raises(GraphValidationError, match="missing evidence"):
        GraphValidator().validate(
            IndustrialGraphBuild(nodes=(process, material), edges=(edge,))
        )


def test_directional_material_substitution_is_valid() -> None:
    source = IndustrialGraphNode(
        "Material",
        "material:optical_polymer",
        "Optical Polymer",
        external_ids={"category": "Optical Material"},
    )
    target = IndustrialGraphNode(
        "Material",
        "material:optical_adhesive",
        "Optical Adhesive",
        external_ids={"category": "Adhesive"},
    )
    evidence = IndustrialGraphEvidence.from_payload(
        "seed:curated_material",
        "test:substitution",
        "Approved curated seed: Phase 12.5 material graph",
        {"source": source.canonical_key, "target": target.canonical_key},
    )
    edge = IndustrialGraphEdge(
        source.identity_key,
        "MATERIAL_SUBSTITUTES_FOR",
        target.identity_key,
    )
    GraphValidator().validate(
        IndustrialGraphBuild(
            nodes=(source, target),
            edges=(edge,),
            evidence=(evidence,),
            edge_evidence=(
                IndustrialGraphEdgeEvidence(edge.base_identity_key, evidence.identity_key),
            ),
        )
    )


def test_material_snapshot_activation_remains_transactional(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(
        recompute=False,
        build_industrial_graph=False,
    )
    service = IndustrialGraphSnapshotService(repository)
    active = service.build_and_activate()
    staged = service.stage(IndustrialGraphBuilder(repository).build())

    def fail_activation(conn, build_version: str) -> None:
        conn.execute("UPDATE graph_snapshots SET status='superseded' WHERE status='active'")
        raise RuntimeError("material activation failure")

    monkeypatch.setattr(service, "_activate_in_transaction", fail_activation)
    with pytest.raises(RuntimeError, match="material activation failure"):
        service.activate(staged.build_version)

    current = service.repository.get_active_snapshot()
    assert current is not None and current.build_version == active.build_version
