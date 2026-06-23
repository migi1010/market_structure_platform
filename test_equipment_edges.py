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


def _build(*, duplicate: bool = False) -> IndustrialGraphBuild:
    process = IndustrialGraphNode("Process", "process:tsv_etching", "TSV Etching")
    equipment = IndustrialGraphNode(
        "Equipment", "equipment:advanced_etch", "Advanced Etch",
        external_ids={"category": "Etch"},
    )
    evidence = IndustrialGraphEvidence.from_payload(
        "seed:curated_equipment", "hbm:tsv_etching:advanced_etch",
        "Approved curated seed: Phase 12.6 equipment graph",
        {"process": "tsv_etching", "equipment": "advanced_etch"},
    )
    edge = IndustrialGraphEdge(
        process.identity_key, "PROCESS_REQUIRES_EQUIPMENT", equipment.identity_key
    )
    return IndustrialGraphBuild(
        nodes=(process, equipment),
        edges=(edge, edge) if duplicate else (edge,),
        evidence=(evidence,),
        edge_evidence=(IndustrialGraphEdgeEvidence(edge.base_identity_key, evidence.identity_key),),
    )


def test_equipment_relationships_are_registered() -> None:
    assert {
        "PROCESS_REQUIRES_EQUIPMENT", "EQUIPMENT_PRODUCED_BY",
        "EQUIPMENT_SUBSTITUTES_FOR", "EQUIPMENT_LIMITED_BY",
        "EQUIPMENT_RESOLVED_BY", "EQUIPMENT_ENABLES_PROCESS",
        "THEME_DEPENDS_ON_EQUIPMENT",
    } <= RELATIONSHIP_TYPES


def test_duplicate_equipment_edges_are_rejected() -> None:
    with pytest.raises(GraphValidationError, match="duplicate edge"):
        GraphValidator().validate(_build(duplicate=True))
