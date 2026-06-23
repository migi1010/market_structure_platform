from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.industrial_graph.graph_models import (
    IndustrialGraphBuild, IndustrialGraphEdge, IndustrialGraphNode,
)
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator
from theme_intelligence.seeds import TARGET_SEED_THEMES, ThemeSeedLoader
from theme_intelligence.seeds.theme_seed_models import (
    SeedConstraint, SeedConstraintRelationLink, SeedProcessConstraintLink,
)
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_duplicate_and_orphan_constraint_nodes_are_rejected() -> None:
    node = IndustrialGraphNode(
        "Constraint", "constraint:hbm_capacity", "HBM Capacity Constraint",
        external_ids={"category": "Capacity Constraint"},
    )
    with pytest.raises(GraphValidationError, match="duplicate canonical node"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(node, node)))
    with pytest.raises(GraphValidationError, match="orphan constraint"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(node,)))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"constraints": (SeedConstraint("bad", "Bad", "Talent Constraint", "citation"),)},
         "unknown constraint category"),
        ({"constraints": (SeedConstraint("hbm_capacity", "HBM Capacity", "Capacity Constraint", ""),)},
         "constraint missing citation"),
        ({"constraint_relations": (
            SeedConstraintRelationLink("hbm_capacity", "hbm_capacity", "citation"),)},
         "constraint relation self-link"),
        ({"processes": (
            replace(next(t for t in TARGET_SEED_THEMES if t.theme_id == "hbm").processes[0],
                    constraint_links=(SeedProcessConstraintLink("Missing", "citation", constraint_key="missing"),)),)},
         "unknown constraint endpoint"),
    ],
)
def test_constraint_seed_validation_rejects_invalid_records(changes, message: str) -> None:
    hbm = next(theme for theme in TARGET_SEED_THEMES if theme.theme_id == "hbm")
    with pytest.raises(GraphValidationError, match=message):
        GraphValidator().validate_constraint_seeds((replace(hbm, **changes),))


def test_invalid_constraint_endpoint_and_missing_evidence_are_rejected() -> None:
    process = IndustrialGraphNode("Process", "process:tsv_etching", "TSV Etching")
    constraint = IndustrialGraphNode(
        "Constraint", "constraint:hbm_capacity", "HBM Capacity Constraint",
        external_ids={"category": "Capacity Constraint"},
    )
    edge = IndustrialGraphEdge(
        constraint.identity_key, "PROCESS_LIMITED_BY_CONSTRAINT", process.identity_key
    )
    with pytest.raises(GraphValidationError, match="invalid process constraint edge"):
        GraphValidator().validate(IndustrialGraphBuild(nodes=(process, constraint), edges=(edge,)))


def test_constraint_edge_without_evidence_is_rejected() -> None:
    theme = IndustrialGraphNode("Theme", "hbm", "HBM")
    constraint = IndustrialGraphNode(
        "Constraint", "constraint:hbm_capacity", "HBM Capacity Constraint",
        external_ids={"category": "Capacity Constraint"},
    )
    edge = IndustrialGraphEdge(
        theme.identity_key,
        "THEME_LIMITED_BY_CONSTRAINT",
        constraint.identity_key,
    )
    with pytest.raises(GraphValidationError, match="missing evidence"):
        GraphValidator().validate(
            IndustrialGraphBuild(nodes=(theme, constraint), edges=(edge,))
        )


def test_constraint_snapshot_activation_remains_transactional(tmp_path: Path, monkeypatch) -> None:
    repository = ThemeRepository(tmp_path / "graph.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    service = IndustrialGraphSnapshotService(repository)
    active = service.build_and_activate()
    staged = service.stage(IndustrialGraphBuilder(repository).build())

    def fail_activation(conn, build_version: str) -> None:
        conn.execute("UPDATE graph_snapshots SET status='superseded' WHERE status='active'")
        raise RuntimeError("constraint activation failure")

    monkeypatch.setattr(service, "_activate_in_transaction", fail_activation)
    with pytest.raises(RuntimeError, match="constraint activation failure"):
        service.activate(staged.build_version)
    current = service.repository.get_active_snapshot()
    assert current is not None and current.build_version == active.build_version
