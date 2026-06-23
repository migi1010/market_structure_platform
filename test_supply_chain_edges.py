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


def _supply_chain_build(*, duplicate: bool = False, evidence_links: bool = True) -> IndustrialGraphBuild:
    theme = IndustrialGraphNode("Theme", "hbm", "HBM")
    role = IndustrialGraphNode("Industry", "supply_chain:hbm:material_supplier", "Material Supplier")
    company = IndustrialGraphNode("Company", "MU", "Micron Technology")
    evidence = IndustrialGraphEvidence.from_payload(
        "seed:curated",
        "hbm:memory_suppliers:MU",
        "Curated HBM memory supplier role.",
        {"theme": "hbm", "role": "memory_suppliers", "ticker": "MU"},
    )
    first = IndustrialGraphEdge(theme.identity_key, "PART_OF_SUPPLY_CHAIN", role.identity_key)
    second = IndustrialGraphEdge(role.identity_key, "SUPPLY_CHAIN_ROLE", company.identity_key)
    edges = (first, second, second) if duplicate else (first, second)
    links = (
        IndustrialGraphEdgeEvidence(first.base_identity_key, evidence.identity_key),
        IndustrialGraphEdgeEvidence(second.base_identity_key, evidence.identity_key),
    ) if evidence_links else ()
    return IndustrialGraphBuild(
        nodes=(theme, role, company),
        edges=edges,
        evidence=(evidence,),
        edge_evidence=links,
    )


def test_supply_chain_relationships_are_registered_and_directional() -> None:
    assert {
        "USES_SUPPLIER",
        "SUPPLY_CHAIN_ROLE",
        "PART_OF_SUPPLY_CHAIN",
        "LIMITED_BY",
        "RESOLVED_BY",
    } <= RELATIONSHIP_TYPES
    edge = IndustrialGraphEdge(
        ("Company", "NVDA"),
        "USES_SUPPLIER",
        ("Company", "MU"),
    )
    assert edge.source_key == ("Company", "company:NVDA")
    assert edge.target_key == ("Company", "company:MU")


def test_duplicate_supply_chain_edges_are_rejected() -> None:
    with pytest.raises(GraphValidationError, match="duplicate edge"):
        GraphValidator().validate(_supply_chain_build(duplicate=True))


def test_supply_chain_edges_without_evidence_are_rejected() -> None:
    with pytest.raises(GraphValidationError, match="missing evidence"):
        GraphValidator().validate(_supply_chain_build(evidence_links=False))
