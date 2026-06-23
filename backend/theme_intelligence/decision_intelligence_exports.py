from __future__ import annotations

from theme_intelligence.decision_intelligence_engine import DecisionIntelligenceEngine
from theme_intelligence.decision_intelligence_models import DecisionIntelligencePacket


def export_decision_intelligence_packet(packet: DecisionIntelligencePacket) -> dict:
    return packet.to_dict()


def export_decision_intelligence(engine: DecisionIntelligenceEngine) -> dict:
    packets = [export_decision_intelligence_packet(packet) for packet in engine.list_packets()]
    return {
        "available": True,
        "packets": [
            {
                "packet_id": packet["packet_id"],
                "title": packet["title"],
                "theme_id": packet["theme_id"],
                "status": packet["status"],
                "checksum": packet["checksum"],
                "lineage": packet["lineage"],
                "section_count": len(packet["sections"]),
            }
            for packet in packets
        ],
        "details": packets,
    }


def export_decision_intelligence_detail(engine: DecisionIntelligenceEngine, packet_id: str) -> dict:
    packet = engine.get_packet(packet_id)
    if packet is None:
        raise KeyError(f"Unknown decision intelligence packet: {packet_id}")
    return {"available": True, "packet": export_decision_intelligence_packet(packet)}
