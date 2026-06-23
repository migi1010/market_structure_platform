from pathlib import Path

from test_decision_packet_builder import packet_repository

from theme_intelligence.industrial_graph.decision_packet_builder import DecisionPacketBuilder


def test_packet_evidence_copies_graph_rows_and_scalar_provenance(tmp_path: Path) -> None:
    repository, _, _, opportunity = packet_repository(tmp_path)
    with repository._connect() as conn:
        theme_name = conn.execute(
            "SELECT display_name FROM graph_nodes WHERE node_type='Theme' ORDER BY id LIMIT 1"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO theme_final_scores (
                theme_name, ai_potential_score, research_importance,
                allocation_readiness, risk_adjusted_score, conviction_level,
                updated_at, score_components_json
            ) VALUES (?, 0, 55, 0, 0, '', '2026-06-12T00:00:00+00:00', '{}')
            """,
            (theme_name,),
        )
        conn.commit()
    build = DecisionPacketBuilder(repository).build(opportunity.opportunity_version)
    graph_evidence = [
        e for packet in build.packets for e in packet.evidence
        if e.evidence_kind == "graph_evidence"
    ]
    assert graph_evidence
    assert all(e.original_graph_evidence_id and e.citation for e in graph_evidence)
    theme_packets = [p for p in build.packets if p.packet_type == "ThemeDecisionPacket"]
    assert any(
        e.source_table == "theme_final_scores"
        and isinstance(e.source_value, (int, float))
        for packet in theme_packets for e in packet.evidence
    )


def test_unavailable_market_data_creates_structured_risk(tmp_path: Path) -> None:
    repository, _, _, opportunity = packet_repository(tmp_path)
    build = DecisionPacketBuilder(repository).build(opportunity.opportunity_version)
    codes = {risk.risk_code for packet in build.packets for risk in packet.risks}
    assert "VALUATION_UNAVAILABLE" in codes
    assert "BUBBLE_UNAVAILABLE" in codes
