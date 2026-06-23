from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.decision_intelligence_models import (
    DecisionIntelligenceLineage,
    DecisionIntelligencePacket,
    DecisionIntelligenceSection,
    DecisionIntelligenceValidationError,
    validate_no_forbidden_fields,
)


def test_packet_requires_institutional_sections_and_deterministic_checksum() -> None:
    lineage = DecisionIntelligenceLineage(
        scout_candidate_id="candidate:ai",
        research_case_id="case-1",
        theme_id="ai_infrastructure",
        graph_snapshot_id=1,
        controller_snapshot_id=2,
        opportunity_snapshot_id=3,
        decision_packet_family_version="packet-v1",
        decision_packet_family_revision=1,
        evidence_ids=("graph_evidence:148",),
    )
    sections = (
        DecisionIntelligenceSection("summary", ({"label": "Known", "value": "AI Infrastructure"},)),
        DecisionIntelligenceSection("bull_case", ({"label": "Controller path", "evidence_ids": ["graph_evidence:148"]},)),
        DecisionIntelligenceSection("bear_case", ({"label": "Coverage gap", "state": "unresolved"},)),
        DecisionIntelligenceSection("evidence_strength", ({"label": "Evidence count", "value": 1},)),
        DecisionIntelligenceSection("research_gaps", ({"label": "Missing opportunity evidence"},)),
        DecisionIntelligenceSection("monitoring_triggers", ({"label": "Coverage below threshold"},)),
        DecisionIntelligenceSection("scenario_matrix", ({"scenario": "BASE", "condition": "Evidence unchanged"},)),
        DecisionIntelligenceSection("open_questions", ({"question": "Which resolver is evidenced?"},)),
        DecisionIntelligenceSection("lineage", ({"research_case_id": "case-1"},)),
    )

    packet = DecisionIntelligencePacket(
        packet_id="decision-intelligence:case-1",
        title="AI Infrastructure Constraint Watch",
        theme_id="ai_infrastructure",
        status="DISCOVERED",
        sections=sections,
        lineage=lineage,
    )

    assert packet.checksum == DecisionIntelligencePacket(
        packet_id="decision-intelligence:case-1",
        title="AI Infrastructure Constraint Watch",
        theme_id="ai_infrastructure",
        status="DISCOVERED",
        sections=sections,
        lineage=lineage,
    ).checksum
    assert set(packet.to_dict()["sections"]) == {
        "summary",
        "bull_case",
        "bear_case",
        "evidence_strength",
        "research_gaps",
        "monitoring_triggers",
        "scenario_matrix",
        "open_questions",
        "lineage",
    }


def test_forbidden_trading_fields_are_rejected_recursively() -> None:
    with pytest.raises(DecisionIntelligenceValidationError):
        validate_no_forbidden_fields({
            "summary": {
                "nested": [
                    {"target_price": 120},
                ],
            },
        })

    with pytest.raises(DecisionIntelligenceValidationError):
        validate_no_forbidden_fields({"recommendation": "buy"})
