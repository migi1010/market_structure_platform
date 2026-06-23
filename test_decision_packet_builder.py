from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.controller_engine import ControllerEngine
from theme_intelligence.industrial_graph.decision_packet_builder import DecisionPacketBuilder
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.opportunity_engine import OpportunityEngine
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


def packet_repository(tmp_path: Path):
    repository = ThemeRepository(tmp_path / "packets.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False, build_industrial_graph=False)
    graph = IndustrialGraphSnapshotService(repository).build_and_activate()
    controller = ControllerEngine(repository).build_and_activate()
    opportunity = OpportunityEngine(repository).build_and_activate(controller.controller_version)
    return repository, graph, controller, opportunity


def test_packet_build_cardinality_and_determinism(tmp_path: Path) -> None:
    repository, graph, controller, opportunity = packet_repository(tmp_path)
    builder = DecisionPacketBuilder(repository)
    first = builder.build(opportunity.opportunity_version)
    second = builder.build(opportunity.opportunity_version)
    assert first == second
    assert first.graph_snapshot_id == graph.id
    assert first.controller_snapshot_id == controller.id
    assert first.opportunity_snapshot_id == opportunity.id
    types = [packet.packet_type for packet in first.packets]
    assert types.count("OpportunityDecisionPacket") == opportunity.company_count
    assert types.count("CompanyDecisionPacket") == opportunity.company_count
    assert types.count("ThemeDecisionPacket") > 0
    assert all(packet.paths and packet.evidence for packet in first.packets)


def test_packet_payload_has_no_generated_narratives(tmp_path: Path) -> None:
    repository, _, _, opportunity = packet_repository(tmp_path)
    build = DecisionPacketBuilder(repository).build(opportunity.opportunity_version)
    text = repr([packet.payload for packet in build.packets]).lower()
    for forbidden in ("why_high_score", "why_low_score", "major_risks", "allocation_notes"):
        assert forbidden not in text
