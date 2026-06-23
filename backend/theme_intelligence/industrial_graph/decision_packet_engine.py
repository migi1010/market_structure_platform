from __future__ import annotations

from theme_intelligence.storage.theme_repository import ThemeRepository

from .decision_packet_builder import DecisionPacketBuilder
from .decision_packet_models import (
    DecisionPacketBuild, DecisionPacketFamily, packet_build_checksum,
)
from .decision_packet_validator import DecisionPacketValidator
from .graph_models import utc_now
from .graph_repository import IndustrialGraphRepository


class DecisionPacketEngine:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        theme_repository = repository or ThemeRepository()
        self.repository = IndustrialGraphRepository(theme_repository)
        self.builder = DecisionPacketBuilder(theme_repository)
        self.validator = DecisionPacketValidator()

    def build(self, opportunity_version: str | None = None) -> DecisionPacketBuild:
        return self.builder.build(opportunity_version)

    def stage(self, build: DecisionPacketBuild) -> DecisionPacketFamily:
        self.validator.validate(build, self.repository)
        with self.repository.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                revision = self.repository.next_packet_family_revision(
                    conn, build.opportunity_snapshot_id
                )
                version = (
                    f"decision-{build.opportunity_snapshot_id}-r{revision:06d}"
                )
                family = DecisionPacketFamily(
                    packet_family_version=version,
                    packet_family_revision=revision,
                    graph_snapshot_id=build.graph_snapshot_id,
                    controller_snapshot_id=build.controller_snapshot_id,
                    opportunity_snapshot_id=build.opportunity_snapshot_id,
                    algorithm_version=build.algorithm_version,
                    status="draft",
                    family_checksum=packet_build_checksum(build),
                    packet_count=len(build.packets),
                    path_count=sum(len(p.paths) for p in build.packets),
                    evidence_count=sum(len(p.evidence) for p in build.packets),
                    risk_count=sum(len(p.risks) for p in build.packets),
                    created_at=utc_now(),
                )
                inserted = self.repository.insert_decision_packet_family(
                    conn, family, build.packets,
                    graph_build_version=build.graph_build_version,
                    controller_version=build.controller_version,
                    opportunity_version=build.opportunity_version,
                )
                if inserted != family.packet_count:
                    raise RuntimeError("staged packet counts do not match")
                conn.execute(
                    "UPDATE decision_packets SET status='validated' WHERE packet_family_version=?",
                    (version,),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        result = self.repository.get_packet_family(version)
        if result is None:
            raise RuntimeError("packet family was not persisted")
        return result

    def activate(self, packet_family_version: str) -> DecisionPacketFamily:
        family = self.repository.get_packet_family(packet_family_version)
        if family is None:
            raise KeyError(f"Unknown packet family: {packet_family_version}")
        build = self._stored_build(family)
        self.validator.validate(build, self.repository)
        if packet_build_checksum(build) != family.family_checksum:
            raise ValueError(f"packet checksum mismatch: {packet_family_version}")
        with self.repository.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._activate_in_transaction(conn, packet_family_version)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        result = self.repository.get_packet_family(packet_family_version)
        if result is None:
            raise RuntimeError("packet family disappeared")
        return result

    @staticmethod
    def _activate_in_transaction(conn, version: str) -> None:
        rows = conn.execute(
            "SELECT DISTINCT status FROM decision_packets WHERE packet_family_version=?",
            (version,),
        ).fetchall()
        if not rows:
            raise KeyError(f"Unknown packet family: {version}")
        if {str(row[0]) for row in rows} - {"validated", "active"}:
            raise ValueError(f"Packet family is not activatable: {version}")
        conn.execute(
            "UPDATE decision_packets SET status='superseded' WHERE status='active' AND packet_family_version<>?",
            (version,),
        )
        conn.execute(
            "UPDATE decision_packets SET status='active', activated_at=? WHERE packet_family_version=?",
            (utc_now(), version),
        )

    def archive(self, packet_family_version: str) -> DecisionPacketFamily:
        family = self.repository.get_packet_family(packet_family_version)
        if family is None:
            raise KeyError(f"Unknown packet family: {packet_family_version}")
        if family.status == "active":
            raise ValueError("active packet family cannot be archived")
        with self.repository.connect() as conn:
            conn.execute(
                "UPDATE decision_packets SET status='archived' WHERE packet_family_version=?",
                (packet_family_version,),
            )
            conn.commit()
        return self.repository.get_packet_family(packet_family_version)

    def build_and_activate(
        self, opportunity_version: str | None = None
    ) -> DecisionPacketFamily:
        return self.activate(self.stage(self.build(opportunity_version)).packet_family_version)

    def _stored_build(self, family: DecisionPacketFamily) -> DecisionPacketBuild:
        with self.repository.connect() as conn:
            row = conn.execute(
                "SELECT * FROM decision_packets WHERE packet_family_version=? LIMIT 1",
                (family.packet_family_version,),
            ).fetchone()
        return DecisionPacketBuild(
            graph_snapshot_id=family.graph_snapshot_id,
            graph_build_version=str(row["graph_build_version"]),
            controller_snapshot_id=family.controller_snapshot_id,
            controller_version=str(row["controller_version"]),
            opportunity_snapshot_id=family.opportunity_snapshot_id,
            opportunity_version=str(row["opportunity_version"]),
            algorithm_version=family.algorithm_version,
            packets=tuple(self.repository.get_decision_packets(family.packet_family_version)),
        )

    def get_packets(self, *, packet_type: str | None = None):
        rows = self.repository.get_decision_packets()
        return [row for row in rows if packet_type is None or row.packet_type == packet_type]

    def get_packet(self, packet_type: str, subject_key: str):
        return next((
            row for row in self.get_packets(packet_type=packet_type)
            if row.subject_key == subject_key
        ), None)
