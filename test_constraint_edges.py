from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_models import (
    RELATIONSHIP_TYPES, IndustrialGraphBuild, IndustrialGraphEdge,
    IndustrialGraphEdgeEvidence, IndustrialGraphEvidence, IndustrialGraphNode,
)
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator


def _build(*, duplicate: bool = False) -> IndustrialGraphBuild:
    theme = IndustrialGraphNode("Theme", "hbm", "HBM")
    constraint = IndustrialGraphNode(
        "Constraint", "constraint:hbm_capacity", "HBM Capacity Constraint",
        external_ids={"category": "Capacity Constraint"},
    )
    evidence = IndustrialGraphEvidence.from_payload(
        "seed:curated_constraint", "hbm:hbm_capacity_constraint",
        "Approved curated seed: Phase 12.7 bottleneck graph",
        {"theme": "hbm", "constraint": "hbm_capacity_constraint"},
    )
    edge = IndustrialGraphEdge(
        theme.identity_key, "THEME_LIMITED_BY_CONSTRAINT", constraint.identity_key
    )
    return IndustrialGraphBuild(
        nodes=(theme, constraint),
        edges=(edge, edge) if duplicate else (edge,),
        evidence=(evidence,),
        edge_evidence=(IndustrialGraphEdgeEvidence(edge.base_identity_key, evidence.identity_key),),
    )


def test_constraint_relationships_are_registered() -> None:
    assert {
        "THEME_LIMITED_BY_CONSTRAINT", "TECHNOLOGY_LIMITED_BY_CONSTRAINT",
        "PROCESS_LIMITED_BY_CONSTRAINT", "MATERIAL_LIMITED_BY_CONSTRAINT",
        "EQUIPMENT_LIMITED_BY_CONSTRAINT", "CONSTRAINT_RESOLVED_BY_COMPANY",
        "COMPANY_EXPOSED_TO_CONSTRAINT", "CONSTRAINT_DEPENDS_ON_MATERIAL",
        "CONSTRAINT_DEPENDS_ON_EQUIPMENT", "CONSTRAINT_DEPENDS_ON_PROCESS",
        "CONSTRAINT_RELATED_TO_CONSTRAINT",
    } <= RELATIONSHIP_TYPES


def test_duplicate_constraint_edges_are_rejected() -> None:
    with pytest.raises(GraphValidationError, match="duplicate edge"):
        GraphValidator().validate(_build(duplicate=True))
