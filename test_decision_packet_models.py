from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.decision_packet_models import (
    DecisionPacket,
    packet_checksum,
)


def _packet(payload=None) -> DecisionPacket:
    return DecisionPacket(
        packet_type="CompanyDecisionPacket",
        subject_type="Company",
        subject_key="company:KLAC",
        coverage=80.0,
        evidence_coverage=75.0,
        payload=payload or {"company": {"company_key": "company:KLAC"}},
        paths=(),
        evidence=(),
        risks=(),
    )


def test_packet_models_reject_generated_narrative_keys() -> None:
    with pytest.raises(ValueError, match="forbidden narrative"):
        _packet({"nested": {"why_high_score": "generated"}})


def test_packet_checksum_is_deterministic() -> None:
    assert packet_checksum(_packet()) == packet_checksum(_packet())
