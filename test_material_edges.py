from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_models import (
    RELATIONSHIP_TYPES,
    IndustrialGraphBuild,
    IndustrialGraphEdge,
    IndustrialGraphEdgeEvidence,
    IndustrialGraphEvidence,
    IndustrialGraphNode,
)
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator


def _material_build(*, duplicate: bool = False) -> IndustrialGraphBuild:
    process = IndustrialGraphNode("Process", "process:packaging", "Packaging")
    material = IndustrialGraphNode(
        "Material",
        "material:underfill",
        "Underfill",
        external_ids={"category": "Encapsulation Material"},
    )
    evidence = IndustrialGraphEvidence.from_payload(
        "seed:curated_material",
        "advanced_packaging:packaging:underfill",
        "Approved curated seed: Phase 12.5 material graph",
        {"process": "packaging", "material": "underfill"},
    )
    edge = IndustrialGraphEdge(
        process.identity_key,
        "PROCESS_REQUIRES_MATERIAL",
        material.identity_key,
    )
    return IndustrialGraphBuild(
        nodes=(process, material),
        edges=(edge, edge) if duplicate else (edge,),
        evidence=(evidence,),
        edge_evidence=(
            IndustrialGraphEdgeEvidence(edge.base_identity_key, evidence.identity_key),
        ),
    )


def test_material_relationships_are_registered() -> None:
    assert {
        "PROCESS_REQUIRES_MATERIAL",
        "MATERIAL_SUPPLIED_BY",
        "MATERIAL_SUBSTITUTES_FOR",
        "MATERIAL_LIMITED_BY",
        "MATERIAL_RESOLVED_BY",
        "MATERIAL_ENABLES_PROCESS",
        "THEME_DEPENDS_ON_MATERIAL",
    } <= RELATIONSHIP_TYPES


def test_duplicate_material_edges_are_rejected() -> None:
    with pytest.raises(GraphValidationError, match="duplicate edge"):
        GraphValidator().validate(_material_build(duplicate=True))
