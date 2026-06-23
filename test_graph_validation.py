from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_models import (
    IndustrialGraphBuild,
    IndustrialGraphEdge,
    IndustrialGraphEdgeEvidence,
    IndustrialGraphEvidence,
    IndustrialGraphNode,
)
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator


def _valid_build() -> IndustrialGraphBuild:
    theme = IndustrialGraphNode("Theme", "hbm", "HBM")
    constraint = IndustrialGraphNode(
        "Constraint",
        "constraint:hbm_yield",
        "HBM Yield Constraint",
        external_ids={"category": "Yield Constraint"},
    )
    evidence = IndustrialGraphEvidence.from_payload(
        "phase10:bottleneck",
        "hbm:yield",
        "Persisted yield constraint.",
        {"name": "Yield"},
    )
    edge = IndustrialGraphEdge(
        theme.identity_key,
        "THEME_LIMITED_BY_CONSTRAINT",
        constraint.identity_key,
    )
    return IndustrialGraphBuild(
        nodes=(constraint, theme),
        edges=(edge,),
        evidence=(evidence,),
        edge_evidence=(IndustrialGraphEdgeEvidence(edge.base_identity_key, evidence.identity_key),),
    )


def test_validator_accepts_valid_build() -> None:
    GraphValidator().validate(_valid_build())


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda build: IndustrialGraphBuild(nodes=build.nodes, edges=build.edges, evidence=()), "missing evidence"),
        (
            lambda build: IndustrialGraphBuild(
                nodes=build.nodes[:1],
                edges=build.edges,
                evidence=build.evidence,
                edge_evidence=build.edge_evidence,
            ),
            "orphan edge",
        ),
        (
            lambda build: IndustrialGraphBuild(
                nodes=build.nodes,
                edges=build.edges,
                evidence=(
                    IndustrialGraphEvidence.from_payload(
                        "quote:provider", "NVDA", "Forbidden quote.", {"price": 1}
                    ),
                ),
                edge_evidence=(),
            ),
            "forbidden source",
        ),
    ],
)
def test_validator_rejects_invalid_builds(mutate, message: str) -> None:
    with pytest.raises(GraphValidationError, match=message):
        GraphValidator().validate(mutate(_valid_build()))


def test_models_reject_empty_identity_and_out_of_range_scores() -> None:
    with pytest.raises(ValueError):
        IndustrialGraphNode("Theme", "", "Theme")
    with pytest.raises(ValueError):
        IndustrialGraphEvidence.from_payload("seed:curated", "id", "", {})
    with pytest.raises(ValueError):
        IndustrialGraphEdge(("Theme", "hbm"), "ENABLES", ("Theme", "ai"), confidence_score=101)
