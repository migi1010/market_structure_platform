from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.graph.graph_models import GraphEdge
from theme_intelligence.graph.graph_overlap import GraphOverlap


def _edge(theme: str, target_type: str, target_id: str, relationship: str) -> GraphEdge:
    return GraphEdge("theme", theme, target_type, target_id, relationship, 80, "persisted_test")


def test_overlap_uses_approved_formula_and_preserves_component_evidence() -> None:
    edges = [
        _edge("hbm", "beneficiary", "NVDA", "theme_beneficiary"),
        _edge("glass_substrate", "beneficiary", "NVDA", "theme_beneficiary"),
        _edge("hbm", "controller", "TSM", "theme_controller"),
        _edge("glass_substrate", "controller", "TSM", "theme_controller"),
        _edge("hbm", "bottleneck", "advanced_packaging", "theme_bottleneck"),
        _edge("glass_substrate", "bottleneck", "advanced_packaging", "theme_bottleneck"),
        _edge("hbm", "catalyst", "capacity_expansion", "theme_catalyst"),
        _edge("glass_substrate", "catalyst", "capacity_expansion", "theme_catalyst"),
        _edge("hbm", "portfolio", "balanced_growth", "theme_portfolio"),
        _edge("glass_substrate", "portfolio", "balanced_growth", "theme_portfolio"),
        _edge("hbm", "supply_chain_role", "packaging", "theme_supply_chain_role"),
        _edge("glass_substrate", "supply_chain_role", "packaging", "theme_supply_chain_role"),
    ]

    overlap = GraphOverlap().compare("hbm", "glass_substrate", edges)

    assert overlap.overlap_score == 100
    assert overlap.components == {
        "beneficiary_overlap": 100.0,
        "controller_overlap": 100.0,
        "bottleneck_overlap": 100.0,
        "catalyst_overlap": 100.0,
        "portfolio_overlap": 100.0,
    }
    assert overlap.shared_supply_chain_roles == ["packaging"]


def test_supply_chain_role_overlap_is_evidence_only() -> None:
    edges = [
        _edge("hbm", "supply_chain_role", "packaging", "theme_supply_chain_role"),
        _edge("glass_substrate", "supply_chain_role", "packaging", "theme_supply_chain_role"),
    ]

    overlap = GraphOverlap().compare("hbm", "glass_substrate", edges)

    assert overlap.overlap_score == 0
    assert overlap.shared_supply_chain_roles == ["packaging"]
