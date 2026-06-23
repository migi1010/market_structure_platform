from pathlib import Path

from test_decision_packet_builder import packet_repository

from theme_intelligence.industrial_graph.decision_packet_builder import DecisionPacketBuilder
from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository


def test_packet_paths_preserve_opportunity_paths(tmp_path: Path) -> None:
    repository, _, _, opportunity = packet_repository(tmp_path)
    source = IndustrialGraphRepository(repository).get_opportunity_metrics(
        opportunity.opportunity_version
    )
    build = DecisionPacketBuilder(repository).build(opportunity.opportunity_version)
    packet = next(
        p for p in build.packets
        if p.packet_type == "OpportunityDecisionPacket"
        and p.subject_key == f"opportunity:{source[0].company_key[1]}"
    )
    assert {p.path for p in packet.paths} == set(source[0].reasoning_paths)
