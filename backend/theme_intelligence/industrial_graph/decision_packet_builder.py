from __future__ import annotations

import json
from collections import defaultdict

from theme_intelligence.storage.theme_repository import ThemeRepository

from .decision_packet_models import (
    DecisionPacket, DecisionPacketBuild, DecisionPacketEvidence,
    DecisionPacketPath, DecisionPacketRisk,
)
from .graph_models import NodeKey, content_hash
from .graph_repository import IndustrialGraphRepository
from .constraint_taxonomy import constraint_key, persisted_constraint_name


class DecisionPacketBuilder:
    ALGORITHM_VERSION = "decision-packet-v1"

    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = IndustrialGraphRepository(repository or ThemeRepository())

    def build(self, opportunity_version: str | None = None) -> DecisionPacketBuild:
        opportunity_snapshot = (
            self.repository.get_opportunity_snapshot(opportunity_version)
            if opportunity_version else self.repository.get_active_opportunity_snapshot()
        )
        if opportunity_snapshot is None or opportunity_snapshot.id is None:
            raise ValueError("missing opportunity snapshot")
        controller_snapshot = self.repository.get_controller_snapshot(
            opportunity_snapshot.controller_version
        )
        graph_snapshot = self.repository.get_snapshot(
            opportunity_snapshot.graph_build_version
        )
        if controller_snapshot is None or controller_snapshot.id != opportunity_snapshot.controller_snapshot_id:
            raise ValueError("missing controller snapshot")
        if graph_snapshot is None or graph_snapshot.id != opportunity_snapshot.graph_snapshot_id:
            raise ValueError("missing graph snapshot")
        if controller_snapshot.graph_snapshot_id != graph_snapshot.id:
            raise ValueError("snapshot lineage mismatch")

        opportunities = self.repository.get_opportunity_metrics(
            opportunity_snapshot.opportunity_version
        )
        controllers = {
            row.company_key: row
            for row in self.repository.get_controller_metrics(
                controller_snapshot.controller_version
            )
        }
        graph = self.repository.export_to_networkx(graph_snapshot.build_version)
        packets: list[DecisionPacket] = []
        theme_rows: dict[NodeKey, list] = defaultdict(list)
        for opportunity in opportunities:
            for path in opportunity.reasoning_paths:
                for node in path:
                    if node[0] == "Theme":
                        theme_rows[node].append(opportunity)

        for opportunity in opportunities:
            controller = controllers[opportunity.company_key]
            paths = self._paths(opportunity.reasoning_paths, opportunity.evidence_ids)
            evidence = self._graph_evidence(opportunity.evidence_ids)
            risks = self._risks(
                subject_key=opportunity.company_key[1],
                opportunity=opportunity,
                controller=controller,
                paths=paths,
                graph=graph,
            )
            common = self._common_payload(
                graph_snapshot, controller_snapshot, opportunity_snapshot
            )
            company_payload = {
                **common,
                "company": self._controller_payload(controller),
                "opportunities": [self._opportunity_payload(opportunity)],
                "bottlenecks": self._bottlenecks(paths, graph),
                "evidence_gaps": self._evidence_gaps(opportunity, controller),
            }
            packets.append(self._packet(
                "CompanyDecisionPacket", "Company", opportunity.company_key[1],
                opportunity.coverage_confidence, company_payload, paths, evidence, risks,
            ))
            opportunity_payload = {
                **common,
                "company": self._controller_payload(controller),
                "opportunity": self._opportunity_payload(opportunity),
                "bottlenecks": self._bottlenecks(paths, graph),
                "evidence_gaps": self._evidence_gaps(opportunity, controller),
            }
            packets.append(self._packet(
                "OpportunityDecisionPacket", "Opportunity",
                f"opportunity:{opportunity.company_key[1]}",
                opportunity.coverage_confidence, opportunity_payload,
                paths, evidence, risks,
            ))

        for theme_key, related in sorted(theme_rows.items()):
            unique = {row.company_key: row for row in related}
            paths = self._theme_paths(theme_key, tuple(unique.values()))
            evidence_ids = tuple(sorted({
                evidence_id for row in unique.values()
                for evidence_id in row.evidence_ids
            }))
            evidence = list(self._graph_evidence(evidence_ids))
            theme_payload, scalar_evidence = self._theme_payload(theme_key, graph)
            evidence.extend(scalar_evidence)
            matched, matched_evidence, matched_risks = self._matched_bottlenecks(
                theme_payload["theme_name"], paths, graph
            )
            evidence.extend(matched_evidence)
            coverage = min(row.coverage_confidence for row in unique.values())
            risks: list[DecisionPacketRisk] = []
            for row in unique.values():
                risks.extend(self._risks(
                    theme_key[1], row, controllers[row.company_key], paths, graph
                ))
            risks.extend(matched_risks)
            payload = {
                **self._common_payload(
                    graph_snapshot, controller_snapshot, opportunity_snapshot
                ),
                "theme": theme_payload,
                "companies": sorted(row.company_key[1] for row in unique.values()),
                "bottlenecks": self._bottlenecks(paths, graph) + matched,
                "evidence_gaps": self._theme_gaps(theme_payload),
            }
            packets.append(self._packet(
                "ThemeDecisionPacket", "Theme", theme_key[1], coverage,
                payload, paths, tuple(evidence), tuple(risks),
            ))

        return DecisionPacketBuild(
            graph_snapshot_id=graph_snapshot.id,
            graph_build_version=graph_snapshot.build_version,
            controller_snapshot_id=controller_snapshot.id,
            controller_version=controller_snapshot.controller_version,
            opportunity_snapshot_id=opportunity_snapshot.id,
            opportunity_version=opportunity_snapshot.opportunity_version,
            algorithm_version=self.ALGORITHM_VERSION,
            packets=tuple(packets),
        )

    def _packet(self, packet_type, subject_type, subject_key, coverage,
                payload, paths, evidence, risks) -> DecisionPacket:
        classes = 2 + (3 if packet_type == "ThemeDecisionPacket" else 2)
        present = 2
        if packet_type == "ThemeDecisionPacket":
            theme = payload["theme"]
            present += sum(
                theme[name]["availability_state"] == "available"
                for name in ("lifecycle", "crowding", "research_importance")
            )
        else:
            present += 2
        unique_risks = {}
        for risk in risks:
            key = (
                risk.risk_category, risk.risk_code, risk.risk_state,
                risk.subject_key, risk.constraint_key or "",
                risk.source_table or "", json.dumps(risk.metadata, sort_keys=True),
            )
            unique_risks[key] = risk
        return DecisionPacket(
            packet_type=packet_type, subject_type=subject_type,
            subject_key=subject_key, coverage=coverage,
            evidence_coverage=round(100 * present / classes, 6),
            payload=payload, paths=tuple(paths), evidence=tuple(evidence),
            risks=tuple(sorted(unique_risks.values(), key=lambda r: (
                r.risk_category, r.risk_code, r.constraint_key or "", r.subject_key
            ))),
        )

    @staticmethod
    def _common_payload(graph, controller, opportunity):
        return {"snapshots": {
            "graph_snapshot_id": graph.id, "graph_build_version": graph.build_version,
            "graph_checksum": graph.checksum,
            "controller_snapshot_id": controller.id,
            "controller_version": controller.controller_version,
            "controller_algorithm_version": controller.algorithm_version,
            "controller_checksum": controller.checksum,
            "opportunity_snapshot_id": opportunity.id,
            "opportunity_version": opportunity.opportunity_version,
            "opportunity_algorithm_version": opportunity.algorithm_version,
            "opportunity_checksum": opportunity.checksum,
            "packet_algorithm_version": DecisionPacketBuilder.ALGORITHM_VERSION,
        }}

    @staticmethod
    def _controller_payload(row):
        return {
            "company_key": row.company_key[1], "company_name": row.company_name,
            "controller_types": list(row.controller_types),
            "dependency_score": row.dependency_score,
            "controller_score": row.controller_score, "base_score": row.base_score,
            "constraint_influence": row.constraint_influence,
            "material_control": row.material_control,
            "equipment_control": row.equipment_control,
            "process_control": row.process_control,
            "technology_control": row.technology_control,
            "resolution_influence": row.resolution_influence,
            "supply_chain_influence": row.supply_chain_influence,
            "coverage": row.coverage,
            "coverage_confidence": row.coverage_confidence,
        }

    @staticmethod
    def _opportunity_payload(row):
        return {
            "company_key": row.company_key[1],
            "opportunity_types": list(row.opportunity_types), "rank": row.rank,
            "controller_component": row.controller_component,
            "constraint_component": row.constraint_component,
            "dependency_component": row.dependency_component,
            "resolution_component": row.resolution_component,
            "criticality_component": row.criticality_component,
            "market_attention": row.market_attention.to_dict(),
            "valuation": row.valuation.to_dict(),
            "bubble_risk": row.bubble_risk.to_dict(),
            "configured_weights": dict(row.configured_weights),
            "applied_weights": dict(row.applied_weights),
            "coverage_component": row.coverage_component,
            "coverage_confidence": row.coverage_confidence,
            "base_score": row.base_score, "opportunity_score": row.opportunity_score,
        }

    @staticmethod
    def _paths(paths, evidence_ids):
        return tuple(
            DecisionPacketPath(
                path_kind="theme_to_company" if path[0][0] == "Theme" else "controller_path",
                source_opportunity_path_order=index,
                path=path, evidence_ids=evidence_ids,
            )
            for index, path in enumerate(paths, 1)
        )

    def _theme_paths(self, theme, opportunities):
        rows = []
        for opportunity in opportunities:
            for index, path in enumerate(opportunity.reasoning_paths, 1):
                if path[0] == theme:
                    rows.append(DecisionPacketPath(
                        "theme_to_company", index, path, opportunity.evidence_ids
                    ))
        return tuple(sorted(set(rows), key=lambda p: (len(p.path), p.path)))

    def _graph_evidence(self, evidence_ids):
        if not evidence_ids:
            return ()
        placeholders = ",".join("?" for _ in evidence_ids)
        with self.repository.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM graph_evidence WHERE id IN ({placeholders}) ORDER BY id",
                tuple(evidence_ids),
            ).fetchall()
        return tuple(DecisionPacketEvidence(
            evidence_kind="graph_evidence", original_graph_evidence_id=int(row["id"]),
            source_table="graph_evidence",
            source_record_key={"id": str(row["id"])},
            source_timestamp=row["observed_date"], source_value=None,
            source_type=str(row["source_type"]),
            source_record_id=str(row["source_record_id"]),
            content_hash=str(row["content_hash"]), citation=str(row["citation"]),
            review_status=str(row["review_status"]), availability_state="available",
        ) for row in rows)

    def _theme_payload(self, theme_key, graph):
        name = str(graph.nodes[theme_key].get("display_name") or theme_key[1])
        with self.repository.connect() as conn:
            discovery = conn.execute(
                "SELECT * FROM theme_discovery_scores WHERE theme_name=?", (name,)
            ).fetchone()
            final = conn.execute(
                "SELECT id, theme_name, research_importance, updated_at FROM theme_final_scores WHERE theme_name=?",
                (name,),
            ).fetchone()
        evidence = []
        def scalar(label, table, row, value_key):
            if row is None:
                return {"availability_state": "unavailable", "value": None, "reason": "missing_row"}
            value = row[value_key]
            evidence.append(DecisionPacketEvidence(
                evidence_kind="persisted_scalar", original_graph_evidence_id=None,
                source_table=table,
                source_record_key={"id": str(row["id"]), "theme_name": name},
                source_timestamp=str(row["updated_at"]), source_value=value,
                source_type=table, source_record_id=f"{row['id']}:{label}",
                content_hash=content_hash({"value": value, "updated_at": row["updated_at"]}),
                citation=None, review_status=None, availability_state="available",
            ))
            return {"availability_state": "available", "value": value,
                    "source_table": table, "source_timestamp": str(row["updated_at"])}
        payload = {
            "theme_key": theme_key[1], "theme_name": name,
            "theme_id": str(discovery["theme_id"]) if discovery else theme_key[1],
            "lifecycle": scalar("lifecycle", "theme_discovery_scores", discovery, "lifecycle_stage"),
            "lifecycle_confidence": scalar("lifecycle_confidence", "theme_discovery_scores", discovery, "lifecycle_confidence"),
            "crowding": scalar("crowding", "theme_discovery_scores", discovery, "crowding_proxy"),
            "research_importance": scalar("research_importance", "theme_final_scores", final, "research_importance"),
        }
        return payload, tuple(evidence)

    @staticmethod
    def _theme_gaps(theme):
        return sorted(
            name for name in ("lifecycle", "crowding", "research_importance")
            if theme[name]["availability_state"] != "available"
        )

    @staticmethod
    def _evidence_gaps(opportunity, controller):
        gaps = []
        if opportunity.market_attention.availability_state != "available":
            gaps.append("market_attention")
        if opportunity.valuation.availability_state != "available":
            gaps.append("valuation")
        if opportunity.bubble_risk.availability_state != "available":
            gaps.append("bubble_risk")
        if controller.coverage < 100:
            gaps.append("controller_coverage")
        return gaps

    @staticmethod
    def _bottlenecks(paths, graph):
        result = []
        for constraint in sorted({
            node for path in paths for node in path.path if node[0] == "Constraint"
        }):
            metadata = graph.nodes[constraint]
            affected = sorted({
                neighbor[0]
                for path in paths for index, node in enumerate(path.path)
                if node == constraint
                for neighbor in path.path[max(0, index - 1):index + 2]
                if neighbor[0] not in {"Theme", "Company", "Constraint"}
            })
            result.append({
                "constraint_key": constraint[1],
                "constraint_name": metadata.get("display_name", constraint[1]),
                "constraint_category": metadata.get("external_ids", {}).get("category", "Unknown"),
                "affected_layers": affected,
                "resolution_state": "unknown",
            })
        return result

    @staticmethod
    def _risks(subject_key, opportunity, controller, paths, graph):
        risks = []
        constraints = sorted({
            node for path in paths for node in path.path if node[0] == "Constraint"
        })
        for constraint in constraints:
            risks.append(DecisionPacketRisk(
                "constraint", "CANONICAL_CONSTRAINT", "known", subject_key,
                constraint_key=constraint[1],
            ))
            risks.append(DecisionPacketRisk(
                "constraint", "UNRESOLVED_CONSTRAINT_PATH", "unresolved",
                subject_key, constraint_key=constraint[1],
            ))
        for component, code in (
            (opportunity.market_attention, "MARKET_ATTENTION_UNAVAILABLE"),
            (opportunity.valuation, "VALUATION_UNAVAILABLE"),
            (opportunity.bubble_risk, "BUBBLE_UNAVAILABLE"),
        ):
            if component.availability_state != "available":
                risks.append(DecisionPacketRisk(
                    "availability", code, "unavailable", subject_key,
                    source_table="opportunity_metrics",
                    metadata={"reason": component.unavailable_reason},
                ))
        if controller.coverage < 100:
            risks.append(DecisionPacketRisk(
                "coverage", "LOW_CONTROLLER_COVERAGE", "known", subject_key,
                source_table="controller_metrics",
                source_value=controller.coverage,
            ))
        if opportunity.coverage_confidence < 100:
            risks.append(DecisionPacketRisk(
                "coverage", "LOW_OPPORTUNITY_COVERAGE", "known", subject_key,
                source_table="opportunity_metrics",
                source_value=opportunity.coverage_confidence,
            ))
        return tuple(risks)

    def _matched_bottlenecks(self, theme_name, paths, graph):
        constraints = {
            node for path in paths for node in path.path if node[0] == "Constraint"
        }
        with self.repository.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM theme_bottlenecks WHERE theme_name=? ORDER BY id",
                (theme_name,),
            ).fetchall()
        matched, evidence, risks = [], [], []
        for row in rows:
            key = ("Constraint", constraint_key(
                persisted_constraint_name(theme_name, str(row["bottleneck_name"]))
            ))
            payload = json.loads(row["evidence_json"] or "[]")
            if key not in constraints or key not in graph or not payload or not row["updated_at"]:
                continue
            source_value = {
                "theme_name": theme_name,
                "bottleneck_name": str(row["bottleneck_name"]),
                "bottleneck_type": str(row["bottleneck_type"]),
                "timeline_status": str(row["timeline_status"]),
                "severity_score": float(row["severity_score"]),
                "duration_score": float(row["duration_score"]),
                "resolution_probability": float(row["resolution_probability"]),
                "impact_score": float(row["impact_score"]),
                "bottleneck_strength": float(row["bottleneck_strength"]),
                "evidence": payload,
            }
            evidence.append(DecisionPacketEvidence(
                evidence_kind="persisted_bottleneck",
                original_graph_evidence_id=None,
                source_table="theme_bottlenecks",
                source_record_key={"id": str(row["id"]), "theme_name": theme_name},
                source_timestamp=str(row["updated_at"]),
                source_value=source_value,
                source_type="theme_bottlenecks",
                source_record_id=str(row["id"]),
                content_hash=content_hash(source_value),
                citation=None, review_status=None, availability_state="available",
            ))
            matched.append({
                "constraint_key": key[1],
                "persisted_source": {
                    "source_table": "theme_bottlenecks",
                    "source_record_id": str(row["id"]),
                    "source_timestamp": str(row["updated_at"]),
                },
            })
            risks.append(DecisionPacketRisk(
                "constraint", "MATCHED_PERSISTED_BOTTLENECK", "known",
                theme_name, constraint_key=key[1],
                source_table="theme_bottlenecks",
                source_record_key={"id": str(row["id"])},
                source_timestamp=str(row["updated_at"]),
                source_value=source_value,
            ))
        return matched, tuple(evidence), tuple(risks)
