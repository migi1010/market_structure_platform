from __future__ import annotations

from collections.abc import Iterable

from .decision_packet_models import (
    DecisionPacketBuild, packet_build_checksum, reject_forbidden_narrative,
)
from .graph_repository import IndustrialGraphRepository


class DecisionPacketValidationError(ValueError):
    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = tuple(sorted(set(errors)))
        super().__init__("; ".join(self.errors))


class DecisionPacketValidator:
    def validate(
        self, build: DecisionPacketBuild, repository: IndustrialGraphRepository
    ) -> None:
        errors: list[str] = []
        opportunity = repository.get_opportunity_snapshot(build.opportunity_version)
        controller = repository.get_controller_snapshot(build.controller_version)
        graph = repository.get_snapshot(build.graph_build_version)
        if opportunity is None or opportunity.id != build.opportunity_snapshot_id:
            errors.append("missing opportunity snapshot")
        if controller is None or controller.id != build.controller_snapshot_id:
            errors.append("missing controller snapshot")
        if graph is None or graph.id != build.graph_snapshot_id:
            errors.append("missing graph snapshot")
        if opportunity and (
            opportunity.controller_snapshot_id != build.controller_snapshot_id
            or opportunity.graph_snapshot_id != build.graph_snapshot_id
        ):
            errors.append("snapshot lineage mismatch")
        identities = [(p.packet_type, p.subject_key) for p in build.packets]
        if len(identities) != len(set(identities)):
            errors.append("duplicate packet identity")
        source_opportunities = (
            repository.get_opportunity_metrics(build.opportunity_version)
            if opportunity else []
        )
        source_paths = {
            path for row in source_opportunities for path in row.reasoning_paths
        }
        valid_evidence = (
            repository.get_evidence_ids_for_build(build.graph_build_version)
            if graph else set()
        )
        for packet in build.packets:
            try:
                reject_forbidden_narrative(packet.payload)
            except ValueError as exc:
                errors.append(str(exc))
            if not packet.paths:
                errors.append(f"missing reasoning paths: {packet.subject_key}")
            for path in packet.paths:
                if path.path not in source_paths:
                    errors.append(f"invalid reasoning path: {packet.subject_key}")
            graph_copies = [
                row for row in packet.evidence
                if row.evidence_kind == "graph_evidence"
            ]
            if not graph_copies:
                errors.append(f"missing evidence references: {packet.subject_key}")
            for row in graph_copies:
                if row.original_graph_evidence_id not in valid_evidence:
                    errors.append(f"orphan evidence reference: {packet.subject_key}")
                else:
                    with repository.connect() as conn:
                        source = conn.execute(
                            "SELECT * FROM graph_evidence WHERE id=?",
                            (row.original_graph_evidence_id,),
                        ).fetchone()
                    if (
                        source is None
                        or str(source["content_hash"]) != row.content_hash
                        or str(source["citation"]) != row.citation
                    ):
                        errors.append(f"altered evidence copy: {packet.subject_key}")
        if packet_build_checksum(build) != packet_build_checksum(build):
            errors.append("non-deterministic outputs")
        if errors:
            raise DecisionPacketValidationError(errors)
