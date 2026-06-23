from pathlib import Path

import pytest

from test_decision_packet_builder import packet_repository

from theme_intelligence.industrial_graph.decision_packet_engine import DecisionPacketEngine


def test_packet_family_revisions_and_activation_are_deterministic(tmp_path: Path) -> None:
    repository, _, _, opportunity = packet_repository(tmp_path)
    engine = DecisionPacketEngine(repository)
    first = engine.build_and_activate(opportunity.opportunity_version)
    second = engine.build_and_activate(opportunity.opportunity_version)
    assert first.packet_family_revision == 1
    assert second.packet_family_revision == 2
    assert first.family_checksum == second.family_checksum
    assert engine.repository.get_active_packet_family().packet_family_version == second.packet_family_version


def test_packet_activation_rolls_back(tmp_path: Path, monkeypatch) -> None:
    repository, _, _, opportunity = packet_repository(tmp_path)
    engine = DecisionPacketEngine(repository)
    first = engine.build_and_activate(opportunity.opportunity_version)
    staged = engine.stage(engine.build(opportunity.opportunity_version))

    def fail(conn, version):
        conn.execute("UPDATE decision_packets SET status='superseded' WHERE status='active'")
        raise RuntimeError("forced packet activation failure")

    monkeypatch.setattr(engine, "_activate_in_transaction", fail)
    with pytest.raises(RuntimeError, match="forced packet"):
        engine.activate(staged.packet_family_version)
    assert engine.repository.get_active_packet_family().packet_family_version == first.packet_family_version
