from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.industrial_graph.graph_models import (
    IndustrialGraphBuild, IndustrialGraphEdge, IndustrialGraphEdgeEvidence,
    IndustrialGraphEvidence, IndustrialGraphNode,
)
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator
from theme_intelligence.seeds import TARGET_SEED_THEMES, ThemeSeedLoader
from theme_intelligence.seeds.theme_seed_models import (
    SeedEquipment, SeedEquipmentProducerLink, SeedEquipmentSubstitutionLink,
    SeedEquipmentConstraintLink,
    SeedProcessEquipmentLink,
)
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_duplicate_and_orphan_equipment_nodes_are_rejected() -> None:
    node = IndustrialGraphNode(
        "Equipment", "equipment:advanced_etch", "Advanced Etch",
        external_ids={"category": "Etch"},
    )
    with pytest.raises(GraphValidationError, match="duplicate canonical node"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(node, node)))
    with pytest.raises(GraphValidationError, match="orphan equipment"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(node,)))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"equipment": (SeedEquipment("bad", "Bad", "Unknown", "citation"),)},
         "unknown equipment category"),
        ({"equipment": (SeedEquipment("advanced_etch", "Advanced Etch", "Etch", ""),)},
         "equipment missing citation"),
        ({"equipment_producer_links": (
            SeedEquipmentProducerLink("advanced_etch", "", "Applied Materials", "citation"),)},
         "equipment producer missing ticker"),
        ({"equipment_producer_links": (
            SeedEquipmentProducerLink("advanced_etch", "AMAT", "Applied Materials", ""),)},
         "equipment relationship missing citation"),
        ({"process_equipment_links": (
            SeedProcessEquipmentLink("missing", "advanced_etch", "PROCESS_REQUIRES_EQUIPMENT", "citation"),)},
         "unknown process equipment endpoint"),
        ({"equipment_substitution_links": (
            SeedEquipmentSubstitutionLink("advanced_etch", "advanced_etch", "citation"),)},
         "equipment substitution self-link"),
        ({"equipment_constraint_links": (
            SeedEquipmentConstraintLink("advanced_etch", "Missing Constraint", "citation"),)},
         "unknown equipment constraint"),
    ],
)
def test_equipment_seed_validation_rejects_invalid_records(changes, message: str) -> None:
    hbm = next(theme for theme in TARGET_SEED_THEMES if theme.theme_id == "hbm")
    with pytest.raises(GraphValidationError, match=message):
        GraphValidator().validate_equipment_seeds((replace(hbm, **changes),))


def test_conflicting_global_company_identity_is_rejected() -> None:
    hbm = next(theme for theme in TARGET_SEED_THEMES if theme.theme_id == "hbm")
    conflict = replace(
        hbm,
        equipment_producer_links=(
            SeedEquipmentProducerLink("advanced_etch", "AMAT", "Different Company", "citation"),
        ),
    )
    with pytest.raises(GraphValidationError, match="conflicting company identity"):
        GraphValidator().validate_equipment_seeds((conflict,))


def test_invalid_equipment_endpoint_and_missing_evidence_are_rejected() -> None:
    theme = IndustrialGraphNode("Theme", "hbm", "HBM")
    equipment = IndustrialGraphNode(
        "Equipment", "equipment:advanced_etch", "Advanced Etch",
        external_ids={"category": "Etch"},
    )
    edge = IndustrialGraphEdge(
        theme.identity_key, "PROCESS_REQUIRES_EQUIPMENT", equipment.identity_key
    )
    with pytest.raises(GraphValidationError, match="invalid process-equipment edge"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(theme, equipment), edges=(edge,)))


def test_equipment_edge_without_evidence_is_rejected() -> None:
    process = IndustrialGraphNode("Process", "process:tsv_etching", "TSV Etching")
    equipment = IndustrialGraphNode(
        "Equipment", "equipment:advanced_etch", "Advanced Etch",
        external_ids={"category": "Etch"},
    )
    edge = IndustrialGraphEdge(
        process.identity_key, "PROCESS_REQUIRES_EQUIPMENT", equipment.identity_key
    )
    with pytest.raises(GraphValidationError, match="missing evidence"):
        GraphValidator().validate(
            IndustrialGraphBuild(nodes=(process, equipment), edges=(edge,))
        )


def test_directional_equipment_substitution_is_valid() -> None:
    source = IndustrialGraphNode(
        "Equipment", "equipment:advanced_etch", "Advanced Etch",
        external_ids={"category": "Etch"},
    )
    target = IndustrialGraphNode(
        "Equipment", "equipment:yield_inspection", "Yield Inspection",
        external_ids={"category": "Inspection"},
    )
    evidence = IndustrialGraphEvidence.from_payload(
        "seed:curated_equipment",
        "test:equipment_substitution",
        "Approved curated seed: Phase 12.6 equipment graph",
        {"source": source.canonical_key, "target": target.canonical_key},
    )
    edge = IndustrialGraphEdge(
        source.identity_key, "EQUIPMENT_SUBSTITUTES_FOR", target.identity_key
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


def test_equipment_snapshot_activation_remains_transactional(tmp_path: Path, monkeypatch) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    active = service.build_and_activate()
    staged = service.stage(IndustrialGraphBuilder(repository).build())

    def fail_activation(conn, build_version: str) -> None:
        conn.execute("UPDATE graph_snapshots SET status='superseded' WHERE status='active'")
        raise RuntimeError("equipment activation failure")

    monkeypatch.setattr(service, "_activate_in_transaction", fail_activation)
    with pytest.raises(RuntimeError, match="equipment activation failure"):
        service.activate(staged.build_version)
    current = service.repository.get_active_snapshot()
    assert current is not None and current.build_version == active.build_version
