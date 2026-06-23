from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Iterator

import networkx as nx

from theme_intelligence.industrial_graph.graph_models import (
    BaseEdgeKey,
    EvidenceKey,
    IndustrialGraphEdge,
    IndustrialGraphEdgeEvidence,
    IndustrialGraphEvidence,
    IndustrialGraphNode,
    IndustrialGraphSnapshot,
    NodeKey,
    normalize_canonical_key,
    utc_now,
)
from theme_intelligence.industrial_graph.controller_models import (
    ControllerIntelligence,
    ControllerMetric,
    ControllerSnapshot,
)
from theme_intelligence.industrial_graph.opportunity_models import (
    MarketComponent,
    MarketSourceRecord,
    OpportunityIntelligence,
    OpportunitySnapshot,
)
from theme_intelligence.industrial_graph.decision_packet_models import (
    DecisionPacket, DecisionPacketEvidence, DecisionPacketFamily,
    DecisionPacketPath, DecisionPacketRisk, packet_checksum,
)
from theme_intelligence.storage.theme_repository import ThemeRepository


SUPPLY_CHAIN_TRAVERSAL_RELATIONSHIPS = frozenset({
    "SUPPLIES",
    "CUSTOMER_OF",
    "DEPENDS_ON",
    "USES_SUPPLIER",
    "SUPPLY_CHAIN_ROLE",
    "PART_OF_SUPPLY_CHAIN",
    "LIMITED_BY",
    "RESOLVED_BY",
})

TECHNOLOGY_TRAVERSAL_RELATIONSHIPS = frozenset({
    "USES_TECHNOLOGY",
    "REQUIRES_PROCESS",
    "TECHNOLOGY_ENABLES_PROCESS",
})

PROCESS_TRAVERSAL_RELATIONSHIPS = frozenset({
    "PROCESS_PRECEDES_PROCESS",
    "PROCESS_DEPENDS_ON_PROCESS",
    "PROCESS_LIMITED_BY_CONSTRAINT",
    "PROCESS_RESOLVED_BY_COMPANY",
})

PROCESS_DEPENDENCY_RELATIONSHIPS = frozenset({
    "PROCESS_PRECEDES_PROCESS",
    "PROCESS_DEPENDS_ON_PROCESS",
})

MATERIAL_TRAVERSAL_RELATIONSHIPS = frozenset({
    "PROCESS_REQUIRES_MATERIAL",
    "MATERIAL_SUPPLIED_BY",
    "MATERIAL_SUBSTITUTES_FOR",
    "MATERIAL_LIMITED_BY",
    "MATERIAL_RESOLVED_BY",
    "MATERIAL_ENABLES_PROCESS",
    "THEME_DEPENDS_ON_MATERIAL",
})

MATERIAL_DEPENDENCY_RELATIONSHIPS = frozenset({
    "USES_TECHNOLOGY",
    "REQUIRES_PROCESS",
    "TECHNOLOGY_ENABLES_PROCESS",
    "PROCESS_PRECEDES_PROCESS",
    "PROCESS_DEPENDS_ON_PROCESS",
    "PROCESS_REQUIRES_MATERIAL",
    "MATERIAL_ENABLES_PROCESS",
    "MATERIAL_SUBSTITUTES_FOR",
    "THEME_DEPENDS_ON_MATERIAL",
})

EQUIPMENT_TRAVERSAL_RELATIONSHIPS = frozenset({
    "PROCESS_REQUIRES_EQUIPMENT",
    "EQUIPMENT_PRODUCED_BY",
    "EQUIPMENT_SUBSTITUTES_FOR",
    "EQUIPMENT_LIMITED_BY",
    "EQUIPMENT_RESOLVED_BY",
    "EQUIPMENT_ENABLES_PROCESS",
    "THEME_DEPENDS_ON_EQUIPMENT",
})

EQUIPMENT_DEPENDENCY_RELATIONSHIPS = frozenset({
    "USES_TECHNOLOGY",
    "REQUIRES_PROCESS",
    "TECHNOLOGY_ENABLES_PROCESS",
    "PROCESS_PRECEDES_PROCESS",
    "PROCESS_DEPENDS_ON_PROCESS",
    "PROCESS_REQUIRES_EQUIPMENT",
    "EQUIPMENT_ENABLES_PROCESS",
    "EQUIPMENT_SUBSTITUTES_FOR",
    "THEME_DEPENDS_ON_EQUIPMENT",
})

CONSTRAINT_TRAVERSAL_RELATIONSHIPS = frozenset({
    "THEME_LIMITED_BY_CONSTRAINT",
    "TECHNOLOGY_LIMITED_BY_CONSTRAINT",
    "PROCESS_LIMITED_BY_CONSTRAINT",
    "MATERIAL_LIMITED_BY_CONSTRAINT",
    "EQUIPMENT_LIMITED_BY_CONSTRAINT",
    "CONSTRAINT_RESOLVED_BY_COMPANY",
    "COMPANY_EXPOSED_TO_CONSTRAINT",
    "CONSTRAINT_DEPENDS_ON_MATERIAL",
    "CONSTRAINT_DEPENDS_ON_EQUIPMENT",
    "CONSTRAINT_DEPENDS_ON_PROCESS",
    "CONSTRAINT_RELATED_TO_CONSTRAINT",
})


class IndustrialGraphRepository:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()

    def initialize(self) -> None:
        self.repository.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.initialize()
        conn = self.repository._connect()
        try:
            yield conn
        finally:
            conn.close()

    def resolve_nodes(
        self,
        conn: sqlite3.Connection,
        nodes: Iterable[IndustrialGraphNode],
    ) -> dict[NodeKey, int]:
        now = utc_now()
        result: dict[NodeKey, int] = {}
        for node in nodes:
            conn.execute(
                """
                INSERT INTO graph_nodes (
                    node_type, canonical_key, display_name, aliases_json, external_ids_json,
                    status, valid_from, valid_to, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_type, canonical_key) DO UPDATE SET
                    display_name=excluded.display_name,
                    aliases_json=excluded.aliases_json,
                    external_ids_json=excluded.external_ids_json,
                    status=excluded.status,
                    valid_to=excluded.valid_to,
                    updated_at=excluded.updated_at
                """,
                (
                    node.node_type,
                    node.canonical_key,
                    node.display_name,
                    json.dumps(node.aliases, ensure_ascii=False, allow_nan=False),
                    json.dumps(dict(node.external_ids), ensure_ascii=False, sort_keys=True, allow_nan=False),
                    node.status,
                    node.valid_from or now,
                    node.valid_to,
                    node.created_at or now,
                    node.updated_at or now,
                ),
            )
            row = conn.execute(
                "SELECT id FROM graph_nodes WHERE node_type=? AND canonical_key=?",
                node.identity_key,
            ).fetchone()
            result[node.identity_key] = int(row["id"])
        return result

    def resolve_evidence(
        self,
        conn: sqlite3.Connection,
        evidence: Iterable[IndustrialGraphEvidence],
    ) -> dict[EvidenceKey, int]:
        now = utc_now()
        result: dict[EvidenceKey, int] = {}
        for row in evidence:
            conn.execute(
                """
                INSERT INTO graph_evidence (
                    source_type, source_record_id, content_hash, citation,
                    observed_date, review_status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_type, source_record_id, content_hash) DO UPDATE SET
                    citation=excluded.citation,
                    observed_date=excluded.observed_date,
                    review_status=excluded.review_status
                """,
                (
                    row.source_type,
                    row.source_record_id,
                    row.content_hash,
                    row.citation,
                    row.observed_date,
                    row.review_status,
                    row.created_at or now,
                ),
            )
            stored = conn.execute(
                """
                SELECT id FROM graph_evidence
                WHERE source_type=? AND source_record_id=? AND content_hash=?
                """,
                row.identity_key,
            ).fetchone()
            result[row.identity_key] = int(stored["id"])
        return result

    def insert_edges(
        self,
        conn: sqlite3.Connection,
        edges: Iterable[IndustrialGraphEdge],
        node_ids: dict[NodeKey, int],
    ) -> dict[BaseEdgeKey, int]:
        now = utc_now()
        result: dict[BaseEdgeKey, int] = {}
        for edge in edges:
            source_id = node_ids[edge.source_key]
            target_id = node_ids[edge.target_key]
            conn.execute(
                """
                INSERT INTO graph_edges (
                    source_node_id, relationship_type, target_node_id, confidence_score,
                    dependency_strength, status, valid_from, valid_to, build_version,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    edge.relationship_type,
                    target_id,
                    edge.confidence_score,
                    edge.dependency_strength,
                    edge.status,
                    edge.valid_from or now,
                    edge.valid_to,
                    edge.build_version,
                    edge.created_at or now,
                    edge.updated_at or now,
                ),
            )
            result[edge.base_identity_key] = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        return result

    @staticmethod
    def attach_evidence(
        conn: sqlite3.Connection,
        links: Iterable[IndustrialGraphEdgeEvidence],
        edge_ids: dict[BaseEdgeKey, int],
        evidence_ids: dict[EvidenceKey, int],
    ) -> int:
        rows = sorted({(edge_ids[link.edge_key], evidence_ids[link.evidence_key]) for link in links})
        conn.executemany(
            "INSERT INTO graph_edge_evidence (edge_id, evidence_id) VALUES (?, ?)",
            rows,
        )
        return len(rows)

    def get_nodes(self, node_ids: set[int] | None = None) -> list[IndustrialGraphNode]:
        self.initialize()
        where = ""
        values: tuple[object, ...] = ()
        if node_ids is not None:
            if not node_ids:
                return []
            placeholders = ",".join("?" for _ in node_ids)
            where = f"WHERE id IN ({placeholders})"
            values = tuple(sorted(node_ids))
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM graph_nodes {where} ORDER BY node_type, canonical_key",
                values,
            ).fetchall()
        return [
            IndustrialGraphNode(
                id=int(row["id"]),
                node_type=str(row["node_type"]),
                canonical_key=str(row["canonical_key"]),
                display_name=str(row["display_name"]),
                aliases=tuple(json.loads(row["aliases_json"])),
                external_ids=json.loads(row["external_ids_json"]),
                status=str(row["status"]),
                valid_from=str(row["valid_from"]),
                valid_to=row["valid_to"],
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def get_edges(
        self,
        build_version: str | None = None,
        status: str | None = "active",
    ) -> list[IndustrialGraphEdge]:
        self.initialize()
        clauses: list[str] = []
        values: list[str] = []
        if build_version:
            clauses.append("e.build_version=?")
            values.append(build_version)
        if status:
            clauses.append("e.status=?")
            values.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT e.*, sn.node_type AS source_type, sn.canonical_key AS source_key,
                       tn.node_type AS target_type, tn.canonical_key AS target_key
                FROM graph_edges e
                JOIN graph_nodes sn ON sn.id=e.source_node_id
                JOIN graph_nodes tn ON tn.id=e.target_node_id
                {where}
                ORDER BY sn.node_type, sn.canonical_key, e.relationship_type,
                         tn.node_type, tn.canonical_key
                """,
                values,
            ).fetchall()
        return [
            IndustrialGraphEdge(
                id=int(row["id"]),
                source_node_id=int(row["source_node_id"]),
                target_node_id=int(row["target_node_id"]),
                source_key=(str(row["source_type"]), str(row["source_key"])),
                relationship_type=str(row["relationship_type"]),
                target_key=(str(row["target_type"]), str(row["target_key"])),
                confidence_score=float(row["confidence_score"]),
                dependency_strength=float(row["dependency_strength"]),
                status=str(row["status"]),
                valid_from=str(row["valid_from"]),
                valid_to=row["valid_to"],
                build_version=str(row["build_version"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def get_evidence_for_edge(self, edge_id: int) -> list[IndustrialGraphEvidence]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT ge.* FROM graph_evidence ge
                JOIN graph_edge_evidence gee ON gee.evidence_id=ge.id
                WHERE gee.edge_id=?
                ORDER BY ge.source_type, ge.source_record_id, ge.content_hash
                """,
                (edge_id,),
            ).fetchall()
        return [
            IndustrialGraphEvidence(
                id=int(row["id"]),
                source_type=str(row["source_type"]),
                source_record_id=str(row["source_record_id"]),
                content_hash=str(row["content_hash"]),
                citation=str(row["citation"]),
                observed_date=row["observed_date"],
                review_status=str(row["review_status"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    def get_active_snapshot(self) -> IndustrialGraphSnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM graph_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return IndustrialGraphSnapshot(
            id=int(row["id"]),
            build_version=str(row["build_version"]),
            status=str(row["status"]),
            source_watermark=str(row["source_watermark"]),
            node_count=int(row["node_count"]),
            edge_count=int(row["edge_count"]),
            checksum=str(row["checksum"]),
            activated_at=row["activated_at"],
            created_at=str(row["created_at"]),
        )

    def get_snapshot(self, build_version: str) -> IndustrialGraphSnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM graph_snapshots WHERE build_version=?",
                (build_version,),
            ).fetchone()
        if row is None:
            return None
        return IndustrialGraphSnapshot(
            id=int(row["id"]), build_version=str(row["build_version"]),
            status=str(row["status"]), source_watermark=str(row["source_watermark"]),
            node_count=int(row["node_count"]), edge_count=int(row["edge_count"]),
            checksum=str(row["checksum"]), activated_at=row["activated_at"],
            created_at=str(row["created_at"]),
        )

    def export_controller_source_graph(
        self,
        build_version: str | None = None,
    ) -> nx.MultiDiGraph:
        snapshot = self.get_snapshot(build_version) if build_version else self.get_active_snapshot()
        if snapshot is None:
            raise ValueError("controller analysis requires a graph snapshot")
        graph = self.export_to_networkx(snapshot.build_version)
        graph.graph.update(
            graph_snapshot_id=snapshot.id,
            graph_build_version=snapshot.build_version,
            graph_checksum=snapshot.checksum,
        )
        return graph

    def export_to_networkx(
        self,
        build_version: str | None = None,
        relationship_types: set[str] | frozenset[str] | None = None,
    ) -> nx.MultiDiGraph:
        graph = nx.MultiDiGraph()
        if build_version is None:
            snapshot = self.get_active_snapshot()
            if snapshot is None:
                return graph
            build_version = snapshot.build_version
            status = "active"
        else:
            status = None
        edges = self.get_edges(build_version=build_version, status=status)
        if relationship_types is not None:
            edges = [
                edge
                for edge in edges
                if edge.relationship_type in relationship_types
            ]
        node_ids = {
            node_id
            for edge in edges
            for node_id in (edge.source_node_id, edge.target_node_id)
            if node_id is not None
        }
        for node in self.get_nodes(node_ids):
            graph.add_node(
                node.identity_key,
                id=node.id,
                node_type=node.node_type,
                canonical_key=node.canonical_key,
                display_name=node.display_name,
                aliases=node.aliases,
                external_ids=dict(node.external_ids),
                status=node.status,
            )
        edge_ids = sorted({int(edge.id or 0) for edge in edges if edge.id})
        evidence_by_edge: dict[int, list[int]] = {edge_id: [] for edge_id in edge_ids}
        if edge_ids:
            placeholders = ",".join("?" for _ in edge_ids)
            with self.connect() as conn:
                rows = conn.execute(
                    f"""
                    SELECT edge_id, evidence_id
                    FROM graph_edge_evidence
                    WHERE edge_id IN ({placeholders})
                    ORDER BY edge_id, evidence_id
                    """,
                    tuple(edge_ids),
                ).fetchall()
            for row in rows:
                evidence_by_edge.setdefault(int(row["edge_id"]), []).append(int(row["evidence_id"]))
        for edge in edges:
            evidence_ids = evidence_by_edge.get(int(edge.id or 0), [])
            graph.add_edge(
                edge.source_key,
                edge.target_key,
                key=edge.id,
                relationship_type=edge.relationship_type,
                confidence_score=edge.confidence_score,
                dependency_strength=edge.dependency_strength,
                build_version=edge.build_version,
                evidence_ids=evidence_ids,
            )
        return graph

    def get_supply_chain_neighbors(
        self,
        endpoint: NodeKey,
        *,
        relationship_types: set[str] | frozenset[str] | None = None,
        direction: str = "both",
        max_depth: int = 1,
    ) -> list[NodeKey]:
        start = self._normalize_endpoint(endpoint)
        if direction not in {"in", "out", "both"}:
            raise ValueError(f"invalid traversal direction: {direction}")
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        allowed = relationship_types or SUPPLY_CHAIN_TRAVERSAL_RELATIONSHIPS
        graph = self.export_to_networkx(relationship_types=allowed)
        self._validate_endpoint(graph, start)
        visited: set[NodeKey] = {start}
        frontier: list[NodeKey] = [start]
        for _ in range(max_depth):
            next_frontier: set[NodeKey] = set()
            for node in frontier:
                candidates: set[NodeKey] = set()
                if direction in {"out", "both"}:
                    candidates.update(graph.successors(node))
                if direction in {"in", "both"}:
                    candidates.update(graph.predecessors(node))
                next_frontier.update(candidates - visited)
            if not next_frontier:
                break
            visited.update(next_frontier)
            frontier = sorted(next_frontier)
        return sorted(visited - {start})

    def get_upstream_companies(
        self,
        endpoint: NodeKey,
        *,
        max_depth: int = 4,
        relationship_types: set[str] | frozenset[str] | None = None,
    ) -> list[NodeKey]:
        return [
            node
            for node in self.get_supply_chain_neighbors(
                endpoint,
                relationship_types=relationship_types,
                direction="in",
                max_depth=max_depth,
            )
            if node[0] == "Company"
        ]

    def get_downstream_companies(
        self,
        endpoint: NodeKey,
        *,
        max_depth: int = 4,
        relationship_types: set[str] | frozenset[str] | None = None,
    ) -> list[NodeKey]:
        return [
            node
            for node in self.get_supply_chain_neighbors(
                endpoint,
                relationship_types=relationship_types,
                direction="out",
                max_depth=max_depth,
            )
            if node[0] == "Company"
        ]

    def get_dependency_paths(
        self,
        source: NodeKey,
        target: NodeKey,
        *,
        max_depth: int = 4,
        relationship_types: set[str] | frozenset[str] | None = None,
    ) -> list[tuple[NodeKey, ...]]:
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        source_key = self._normalize_endpoint(source)
        target_key = self._normalize_endpoint(target)
        allowed = relationship_types or SUPPLY_CHAIN_TRAVERSAL_RELATIONSHIPS
        graph = self.export_to_networkx(relationship_types=allowed)
        self._validate_endpoint(graph, source_key)
        self._validate_endpoint(graph, target_key)
        paths = nx.all_simple_paths(
            graph,
            source=source_key,
            target=target_key,
            cutoff=max_depth,
        )
        return sorted({tuple(path) for path in paths})

    def get_technology_neighbors(
        self,
        endpoint: NodeKey,
        *,
        relationship_types: set[str] | frozenset[str] | None = None,
        direction: str = "both",
        max_depth: int = 1,
    ) -> list[NodeKey]:
        return self.get_supply_chain_neighbors(
            endpoint,
            relationship_types=relationship_types or TECHNOLOGY_TRAVERSAL_RELATIONSHIPS,
            direction=direction,
            max_depth=max_depth,
        )

    def get_process_neighbors(
        self,
        endpoint: NodeKey,
        *,
        relationship_types: set[str] | frozenset[str] | None = None,
        direction: str = "both",
        max_depth: int = 1,
    ) -> list[NodeKey]:
        return self.get_supply_chain_neighbors(
            endpoint,
            relationship_types=relationship_types or PROCESS_TRAVERSAL_RELATIONSHIPS,
            direction=direction,
            max_depth=max_depth,
        )

    def get_theme_technologies(self, theme: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_technology_neighbors(
                theme,
                relationship_types={"USES_TECHNOLOGY"},
                direction="out",
                max_depth=1,
            )
            if node[0] == "Technology"
        ]

    def get_technology_processes(self, technology: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_technology_neighbors(
                technology,
                relationship_types={"REQUIRES_PROCESS", "TECHNOLOGY_ENABLES_PROCESS"},
                direction="out",
                max_depth=1,
            )
            if node[0] == "Process"
        ]

    def get_process_dependencies(
        self,
        process: NodeKey,
        *,
        max_depth: int = 1,
    ) -> list[NodeKey]:
        return [
            node
            for node in self.get_process_neighbors(
                process,
                relationship_types=PROCESS_DEPENDENCY_RELATIONSHIPS,
                direction="out",
                max_depth=max_depth,
            )
            if node[0] == "Process"
        ]

    def get_process_paths(
        self,
        source: NodeKey,
        target: NodeKey,
        *,
        max_depth: int = 4,
        relationship_types: set[str] | frozenset[str] | None = None,
    ) -> list[tuple[NodeKey, ...]]:
        return self.get_dependency_paths(
            source,
            target,
            max_depth=max_depth,
            relationship_types=relationship_types or PROCESS_DEPENDENCY_RELATIONSHIPS,
        )

    def get_material_neighbors(
        self,
        endpoint: NodeKey,
        *,
        relationship_types: set[str] | frozenset[str] | None = None,
        direction: str = "both",
        max_depth: int = 1,
    ) -> list[NodeKey]:
        return self.get_supply_chain_neighbors(
            endpoint,
            relationship_types=relationship_types or MATERIAL_TRAVERSAL_RELATIONSHIPS,
            direction=direction,
            max_depth=max_depth,
        )

    def get_material_suppliers(self, material: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_material_neighbors(
                material,
                relationship_types={"MATERIAL_SUPPLIED_BY"},
                direction="out",
                max_depth=1,
            )
            if node[0] in {"Company", "Supplier"}
        ]

    def get_process_materials(self, process: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_material_neighbors(
                process,
                relationship_types={
                    "PROCESS_REQUIRES_MATERIAL",
                    "MATERIAL_ENABLES_PROCESS",
                },
                direction="both",
                max_depth=1,
            )
            if node[0] == "Material"
        ]

    def get_theme_materials(
        self,
        theme: NodeKey,
        *,
        max_depth: int = 3,
    ) -> list[NodeKey]:
        return [
            node
            for node in self.get_supply_chain_neighbors(
                theme,
                relationship_types=MATERIAL_DEPENDENCY_RELATIONSHIPS,
                direction="out",
                max_depth=max_depth,
            )
            if node[0] == "Material"
        ]

    def get_material_dependency_paths(
        self,
        source: NodeKey,
        target: NodeKey,
        *,
        max_depth: int = 4,
        relationship_types: set[str] | frozenset[str] | None = None,
    ) -> list[tuple[NodeKey, ...]]:
        return self.get_dependency_paths(
            source,
            target,
            max_depth=max_depth,
            relationship_types=relationship_types or MATERIAL_DEPENDENCY_RELATIONSHIPS,
        )

    def get_equipment_neighbors(
        self,
        endpoint: NodeKey,
        *,
        relationship_types: set[str] | frozenset[str] | None = None,
        direction: str = "both",
        max_depth: int = 1,
    ) -> list[NodeKey]:
        return self.get_supply_chain_neighbors(
            endpoint,
            relationship_types=relationship_types or EQUIPMENT_TRAVERSAL_RELATIONSHIPS,
            direction=direction,
            max_depth=max_depth,
        )

    def get_equipment_suppliers(self, equipment: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_equipment_neighbors(
                equipment,
                relationship_types={"EQUIPMENT_PRODUCED_BY"},
                direction="out",
                max_depth=1,
            )
            if node[0] == "Company"
        ]

    def get_process_equipment(self, process: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_equipment_neighbors(
                process,
                relationship_types={
                    "PROCESS_REQUIRES_EQUIPMENT",
                    "EQUIPMENT_ENABLES_PROCESS",
                },
                direction="both",
                max_depth=1,
            )
            if node[0] == "Equipment"
        ]

    def get_theme_equipment(
        self,
        theme: NodeKey,
        *,
        max_depth: int = 3,
    ) -> list[NodeKey]:
        return [
            node
            for node in self.get_supply_chain_neighbors(
                theme,
                relationship_types=EQUIPMENT_DEPENDENCY_RELATIONSHIPS,
                direction="out",
                max_depth=max_depth,
            )
            if node[0] == "Equipment"
        ]

    def get_equipment_dependency_paths(
        self,
        source: NodeKey,
        target: NodeKey,
        *,
        max_depth: int = 4,
        relationship_types: set[str] | frozenset[str] | None = None,
    ) -> list[tuple[NodeKey, ...]]:
        return self.get_dependency_paths(
            source,
            target,
            max_depth=max_depth,
            relationship_types=relationship_types or EQUIPMENT_DEPENDENCY_RELATIONSHIPS,
        )

    def get_constraint_neighbors(
        self,
        endpoint: NodeKey,
        *,
        relationship_types: set[str] | frozenset[str] | None = None,
        direction: str = "both",
        max_depth: int = 1,
    ) -> list[NodeKey]:
        return self.get_supply_chain_neighbors(
            endpoint,
            relationship_types=relationship_types or CONSTRAINT_TRAVERSAL_RELATIONSHIPS,
            direction=direction,
            max_depth=max_depth,
        )

    def get_theme_constraints(self, theme: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_constraint_neighbors(
                theme,
                relationship_types={"THEME_LIMITED_BY_CONSTRAINT"},
                direction="out",
                max_depth=1,
            )
            if node[0] == "Constraint"
        ]

    def get_process_constraints(self, process: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_constraint_neighbors(
                process,
                relationship_types={"PROCESS_LIMITED_BY_CONSTRAINT"},
                direction="out",
                max_depth=1,
            )
            if node[0] == "Constraint"
        ]

    def get_material_constraints(self, material: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_constraint_neighbors(
                material,
                relationship_types={"MATERIAL_LIMITED_BY_CONSTRAINT"},
                direction="out",
                max_depth=1,
            )
            if node[0] == "Constraint"
        ]

    def get_equipment_constraints(self, equipment: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_constraint_neighbors(
                equipment,
                relationship_types={"EQUIPMENT_LIMITED_BY_CONSTRAINT"},
                direction="out",
                max_depth=1,
            )
            if node[0] == "Constraint"
        ]

    def get_constraint_resolvers(self, constraint: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_constraint_neighbors(
                constraint,
                relationship_types={"CONSTRAINT_RESOLVED_BY_COMPANY"},
                direction="out",
                max_depth=1,
            )
            if node[0] == "Company"
        ]

    def get_constraint_exposed_companies(self, constraint: NodeKey) -> list[NodeKey]:
        return [
            node
            for node in self.get_constraint_neighbors(
                constraint,
                relationship_types={"COMPANY_EXPOSED_TO_CONSTRAINT"},
                direction="in",
                max_depth=1,
            )
            if node[0] == "Company"
        ]

    def get_constraint_dependency_paths(
        self,
        source: NodeKey,
        target: NodeKey,
        *,
        max_depth: int = 4,
        relationship_types: set[str] | frozenset[str] | None = None,
    ) -> list[tuple[NodeKey, ...]]:
        return self.get_dependency_paths(
            source,
            target,
            max_depth=max_depth,
            relationship_types=relationship_types or CONSTRAINT_TRAVERSAL_RELATIONSHIPS,
        )

    @staticmethod
    def _normalize_endpoint(endpoint: NodeKey) -> NodeKey:
        node_type, canonical_key = endpoint
        return (
            node_type,
            normalize_canonical_key(canonical_key, node_type=node_type),
        )

    @staticmethod
    def _validate_endpoint(graph: nx.MultiDiGraph, endpoint: NodeKey) -> None:
        if endpoint not in graph:
            raise ValueError(f"invalid traversal endpoint: {endpoint}")

    def get_evidence_ids_for_build(self, build_version: str) -> set[int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT gee.evidence_id
                FROM graph_edge_evidence gee
                JOIN graph_edges e ON e.id=gee.edge_id
                WHERE e.build_version=?
                """,
                (build_version,),
            ).fetchall()
        return {int(row[0]) for row in rows}

    def insert_controller_snapshot(
        self, conn: sqlite3.Connection, snapshot: ControllerSnapshot
    ) -> int:
        conn.execute(
            """
            INSERT INTO controller_snapshots (
                controller_version, graph_snapshot_id, graph_build_version,
                algorithm_version, status, checksum, company_count, metric_count,
                activated_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.controller_version, snapshot.graph_snapshot_id,
                snapshot.graph_build_version, snapshot.algorithm_version,
                snapshot.status, snapshot.checksum, snapshot.company_count,
                snapshot.metric_count, snapshot.activated_at, snapshot.created_at,
            ),
        )
        return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

    def node_ids_for_keys(
        self, conn: sqlite3.Connection, keys: set[NodeKey]
    ) -> dict[NodeKey, int]:
        result: dict[NodeKey, int] = {}
        for node_type, canonical_key in sorted(keys):
            row = conn.execute(
                "SELECT id FROM graph_nodes WHERE node_type=? AND canonical_key=?",
                (node_type, canonical_key),
            ).fetchone()
            if row is not None:
                result[(node_type, canonical_key)] = int(row[0])
        return result

    def insert_graph_metrics(
        self, conn: sqlite3.Connection, controller_snapshot_id: int,
        controller_version: str, graph_snapshot_id: int, algorithm_version: str,
        metrics: Iterable[ControllerMetric], node_ids: dict[NodeKey, int],
    ) -> int:
        now = utc_now()
        rows = [
            (
                controller_snapshot_id, controller_version, graph_snapshot_id,
                node_ids[row.company_key], row.metric_name, row.raw_value,
                row.normalized_value, row.coverage,
                json.dumps(dict(row.metadata), sort_keys=True, allow_nan=False),
                algorithm_version, now,
            )
            for row in metrics
        ]
        conn.executemany(
            """
            INSERT INTO graph_metrics (
                controller_snapshot_id, controller_version, graph_snapshot_id,
                node_id, metric_name, raw_value, normalized_value, coverage,
                metadata_json, algorithm_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)

    def insert_controller_metrics(
        self, conn: sqlite3.Connection, controller_snapshot_id: int,
        controller_version: str, graph_snapshot_id: int, algorithm_version: str,
        controllers: Iterable[ControllerIntelligence], node_ids: dict[NodeKey, int],
    ) -> int:
        now = utc_now()
        rows = []
        for row in controllers:
            rows.append((
                controller_snapshot_id, controller_version, graph_snapshot_id,
                node_ids[row.company_key], row.dependency_score,
                row.controller_score, row.base_score, row.constraint_influence,
                row.material_control, row.equipment_control, row.process_control,
                row.technology_control, row.resolution_influence,
                row.supply_chain_influence, row.coverage,
                row.coverage_confidence, row.rank, row.company_name,
                json.dumps(row.controller_types, allow_nan=False),
                json.dumps(row.evidence_ids, allow_nan=False),
                json.dumps(row.reasoning_paths, allow_nan=False),
                algorithm_version, now,
            ))
        conn.executemany(
            """
            INSERT INTO controller_metrics (
                controller_snapshot_id, controller_version, graph_snapshot_id,
                company_node_id, dependency_score, controller_score, base_score,
                constraint_influence, material_control, equipment_control,
                process_control, technology_control, resolution_influence,
                supply_chain_influence, coverage, coverage_confidence, rank,
                company_name, controller_types_json, evidence_ids_json,
                reasoning_paths_json, algorithm_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)

    def get_controller_snapshot(self, controller_version: str) -> ControllerSnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM controller_snapshots WHERE controller_version=?",
                (controller_version,),
            ).fetchone()
        return self._controller_snapshot_from_row(row)

    def get_active_controller_snapshot(self) -> ControllerSnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM controller_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return self._controller_snapshot_from_row(row)

    @staticmethod
    def _controller_snapshot_from_row(row: sqlite3.Row | None) -> ControllerSnapshot | None:
        if row is None:
            return None
        return ControllerSnapshot(
            id=int(row["id"]), controller_version=str(row["controller_version"]),
            graph_snapshot_id=int(row["graph_snapshot_id"]),
            graph_build_version=str(row["graph_build_version"]),
            algorithm_version=str(row["algorithm_version"]), status=str(row["status"]),
            checksum=str(row["checksum"]), company_count=int(row["company_count"]),
            metric_count=int(row["metric_count"]), activated_at=row["activated_at"],
            created_at=str(row["created_at"]),
        )

    def get_controller_metrics(
        self, controller_version: str | None = None
    ) -> list[ControllerIntelligence]:
        snapshot = (
            self.get_controller_snapshot(controller_version)
            if controller_version else self.get_active_controller_snapshot()
        )
        if snapshot is None:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT cm.*, gn.canonical_key AS company_key
                FROM controller_metrics cm
                JOIN graph_nodes gn ON gn.id=cm.company_node_id
                WHERE cm.controller_snapshot_id=?
                ORDER BY cm.rank, gn.canonical_key
                """,
                (snapshot.id,),
            ).fetchall()
        return [
            ControllerIntelligence(
                company_key=("Company", str(row["company_key"])),
                company_name=str(row["company_name"]),
                controller_types=tuple(json.loads(row["controller_types_json"])),
                dependency_score=float(row["dependency_score"]),
                controller_score=float(row["controller_score"]),
                base_score=float(row["base_score"]),
                constraint_influence=float(row["constraint_influence"]),
                material_control=float(row["material_control"]),
                equipment_control=float(row["equipment_control"]),
                process_control=float(row["process_control"]),
                technology_control=float(row["technology_control"]),
                resolution_influence=float(row["resolution_influence"]),
                supply_chain_influence=float(row["supply_chain_influence"]),
                coverage=float(row["coverage"]),
                coverage_confidence=float(row["coverage_confidence"]),
                evidence_ids=tuple(json.loads(row["evidence_ids_json"])),
                reasoning_paths=tuple(
                    tuple((str(node[0]), str(node[1])) for node in path)
                    for path in json.loads(row["reasoning_paths_json"])
                ),
                rank=int(row["rank"]),
            )
            for row in rows
        ]

    def get_graph_metrics(
        self, controller_version: str
    ) -> list[ControllerMetric]:
        snapshot = self.get_controller_snapshot(controller_version)
        if snapshot is None:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT gm.*, gn.canonical_key AS company_key
                FROM graph_metrics gm
                JOIN graph_nodes gn ON gn.id=gm.node_id
                WHERE gm.controller_snapshot_id=?
                ORDER BY gn.canonical_key, gm.metric_name
                """,
                (snapshot.id,),
            ).fetchall()
        return [
            ControllerMetric(
                company_key=("Company", str(row["company_key"])),
                metric_name=str(row["metric_name"]),
                raw_value=float(row["raw_value"]),
                normalized_value=float(row["normalized_value"]),
                coverage=float(row["coverage"]),
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        ]

    def insert_opportunity_snapshot(
        self, conn: sqlite3.Connection, snapshot: OpportunitySnapshot
    ) -> int:
        conn.execute(
            """
            INSERT INTO opportunity_snapshots (
                opportunity_version, controller_snapshot_id, controller_version,
                graph_snapshot_id, graph_build_version, algorithm_version,
                status, checksum, company_count, path_count, activated_at,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.opportunity_version,
                snapshot.controller_snapshot_id,
                snapshot.controller_version,
                snapshot.graph_snapshot_id,
                snapshot.graph_build_version,
                snapshot.algorithm_version,
                snapshot.status,
                snapshot.checksum,
                snapshot.company_count,
                snapshot.path_count,
                snapshot.activated_at,
                snapshot.created_at,
            ),
        )
        return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

    def insert_opportunity_metrics(
        self,
        conn: sqlite3.Connection,
        opportunity_snapshot_id: int,
        snapshot: OpportunitySnapshot,
        opportunities: Iterable[OpportunityIntelligence],
        node_ids: dict[NodeKey, int],
    ) -> int:
        now = utc_now()
        rows = []
        for row in opportunities:
            market = {
                "market_attention_component": row.market_attention.to_dict(),
                "valuation_component": row.valuation.to_dict(),
                "bubble_risk_component": row.bubble_risk.to_dict(),
            }
            rows.append((
                opportunity_snapshot_id,
                snapshot.opportunity_version,
                snapshot.controller_snapshot_id,
                snapshot.graph_snapshot_id,
                node_ids[row.company_key],
                row.company_name,
                row.controller_component,
                row.controller_component,
                row.constraint_component,
                row.constraint_component,
                row.dependency_component,
                row.dependency_component,
                row.resolution_component,
                row.resolution_component,
                row.criticality_component,
                row.criticality_component,
                row.market_attention.raw_value,
                row.market_attention.normalized_value,
                row.valuation.raw_value,
                row.valuation.normalized_value,
                row.bubble_risk.raw_value,
                row.bubble_risk.normalized_value,
                row.coverage_component,
                row.coverage_confidence,
                row.base_score,
                row.opportunity_score,
                row.rank,
                json.dumps(row.opportunity_types, sort_keys=True, allow_nan=False),
                json.dumps(dict(row.configured_weights), sort_keys=True, allow_nan=False),
                json.dumps(dict(row.applied_weights), sort_keys=True, allow_nan=False),
                json.dumps(row.availability_states, sort_keys=True, allow_nan=False),
                json.dumps(market, sort_keys=True, allow_nan=False),
                json.dumps(row.evidence_ids, sort_keys=True, allow_nan=False),
                snapshot.algorithm_version,
                now,
            ))
        conn.executemany(
            """
            INSERT INTO opportunity_metrics (
                opportunity_snapshot_id, opportunity_version,
                controller_snapshot_id, graph_snapshot_id, company_node_id,
                company_name, controller_component_raw, controller_component,
                constraint_component_raw, constraint_component,
                dependency_component_raw, dependency_component,
                resolution_component_raw, resolution_component,
                criticality_component_raw, criticality_component,
                market_attention_raw, market_attention_component,
                valuation_penalty_raw, valuation_component,
                bubble_penalty_raw, bubble_risk_component, coverage_component,
                coverage_confidence, base_score, opportunity_score, rank,
                opportunity_types_json, configured_weights_json,
                applied_weights_json, availability_states_json,
                source_records_json, evidence_ids_json, algorithm_version,
                created_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            rows,
        )
        return len(rows)

    def insert_opportunity_reasoning_paths(
        self,
        conn: sqlite3.Connection,
        opportunity_snapshot_id: int,
        snapshot: OpportunitySnapshot,
        opportunities: Iterable[OpportunityIntelligence],
        node_ids: dict[NodeKey, int],
    ) -> int:
        now = utc_now()
        rows = []
        for opportunity in opportunities:
            for index, path in enumerate(opportunity.reasoning_paths, 1):
                rows.append((
                    opportunity_snapshot_id,
                    snapshot.opportunity_version,
                    node_ids[opportunity.company_key],
                    index,
                    "theme_to_company" if path[0][0] == "Theme" else "controller_path",
                    json.dumps(path, sort_keys=True, allow_nan=False),
                    json.dumps(opportunity.evidence_ids, sort_keys=True, allow_nan=False),
                    now,
                ))
        conn.executemany(
            """
            INSERT INTO opportunity_reasoning_paths (
                opportunity_snapshot_id, opportunity_version, company_node_id,
                path_order, path_kind, path_json, evidence_ids_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)

    def get_opportunity_snapshot(
        self, opportunity_version: str
    ) -> OpportunitySnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM opportunity_snapshots WHERE opportunity_version=?",
                (opportunity_version,),
            ).fetchone()
        return self._opportunity_snapshot_from_row(row)

    def get_active_opportunity_snapshot(self) -> OpportunitySnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM opportunity_snapshots
                WHERE status='active'
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
        return self._opportunity_snapshot_from_row(row)

    @staticmethod
    def _opportunity_snapshot_from_row(
        row: sqlite3.Row | None,
    ) -> OpportunitySnapshot | None:
        if row is None:
            return None
        return OpportunitySnapshot(
            id=int(row["id"]),
            opportunity_version=str(row["opportunity_version"]),
            controller_snapshot_id=int(row["controller_snapshot_id"]),
            controller_version=str(row["controller_version"]),
            graph_snapshot_id=int(row["graph_snapshot_id"]),
            graph_build_version=str(row["graph_build_version"]),
            algorithm_version=str(row["algorithm_version"]),
            status=str(row["status"]),
            checksum=str(row["checksum"]),
            company_count=int(row["company_count"]),
            path_count=int(row["path_count"]),
            activated_at=row["activated_at"],
            created_at=str(row["created_at"]),
        )

    def get_opportunity_reasoning_paths(
        self, opportunity_version: str
    ) -> dict[NodeKey, tuple[tuple[NodeKey, ...], ...]]:
        snapshot = self.get_opportunity_snapshot(opportunity_version)
        if snapshot is None:
            return {}
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT op.*, gn.canonical_key AS company_key
                FROM opportunity_reasoning_paths op
                JOIN graph_nodes gn ON gn.id=op.company_node_id
                WHERE op.opportunity_snapshot_id=?
                ORDER BY gn.canonical_key, op.path_order
                """,
                (snapshot.id,),
            ).fetchall()
        grouped: dict[NodeKey, list[tuple[NodeKey, ...]]] = {}
        for row in rows:
            key = ("Company", str(row["company_key"]))
            path = tuple(
                (str(node[0]), str(node[1]))
                for node in json.loads(row["path_json"])
            )
            grouped.setdefault(key, []).append(path)
        return {key: tuple(paths) for key, paths in grouped.items()}

    def get_opportunity_metrics(
        self, opportunity_version: str | None = None
    ) -> list[OpportunityIntelligence]:
        snapshot = (
            self.get_opportunity_snapshot(opportunity_version)
            if opportunity_version
            else self.get_active_opportunity_snapshot()
        )
        if snapshot is None:
            return []
        paths = self.get_opportunity_reasoning_paths(snapshot.opportunity_version)
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT om.*, gn.canonical_key AS company_key
                FROM opportunity_metrics om
                JOIN graph_nodes gn ON gn.id=om.company_node_id
                WHERE om.opportunity_snapshot_id=?
                ORDER BY om.rank, gn.canonical_key
                """,
                (snapshot.id,),
            ).fetchall()
        results: list[OpportunityIntelligence] = []
        for row in rows:
            key = ("Company", str(row["company_key"]))
            market = json.loads(row["source_records_json"])
            results.append(OpportunityIntelligence(
                company_key=key,
                company_name=str(row["company_name"]),
                opportunity_types=tuple(json.loads(row["opportunity_types_json"])),
                controller_component=float(row["controller_component"]),
                constraint_component=float(row["constraint_component"]),
                dependency_component=float(row["dependency_component"]),
                resolution_component=float(row["resolution_component"]),
                criticality_component=float(row["criticality_component"]),
                market_attention=self._market_component_from_dict(
                    market["market_attention_component"]
                ),
                valuation=self._market_component_from_dict(
                    market["valuation_component"]
                ),
                bubble_risk=self._market_component_from_dict(
                    market["bubble_risk_component"]
                ),
                coverage_component=float(row["coverage_component"]),
                coverage_confidence=float(row["coverage_confidence"]),
                base_score=float(row["base_score"]),
                opportunity_score=float(row["opportunity_score"]),
                configured_weights=json.loads(row["configured_weights_json"]),
                applied_weights=json.loads(row["applied_weights_json"]),
                evidence_ids=tuple(json.loads(row["evidence_ids_json"])),
                reasoning_paths=paths.get(key, ()),
                rank=int(row["rank"]),
            ))
        return results

    @staticmethod
    def _market_component_from_dict(payload: dict) -> MarketComponent:
        return MarketComponent(
            name=str(payload["name"]),
            raw_value=payload["raw_value"],
            normalized_value=payload["normalized_value"],
            availability_state=str(payload["availability_state"]),
            configured_weight=float(payload["configured_weight"]),
            applied_weight=float(payload["applied_weight"]),
            source_records=tuple(
                MarketSourceRecord(
                    source_table=str(source["source_table"]),
                    source_record_key=source["source_record_key"],
                    source_timestamp=str(source["source_timestamp"]),
                    source_value=float(source["source_value"]),
                    availability_state=str(source["availability_state"]),
                )
                for source in payload["source_records"]
            ),
            unavailable_reason=payload["unavailable_reason"],
        )

    def next_packet_family_revision(
        self, conn: sqlite3.Connection, opportunity_snapshot_id: int
    ) -> int:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(packet_family_revision), 0) + 1
            FROM decision_packets WHERE opportunity_snapshot_id=?
            """,
            (opportunity_snapshot_id,),
        ).fetchone()
        return int(row[0])

    def insert_decision_packet_family(
        self, conn: sqlite3.Connection, family: DecisionPacketFamily,
        packets: Iterable[DecisionPacket], *,
        graph_build_version: str, controller_version: str,
        opportunity_version: str,
    ) -> int:
        now = utc_now()
        count = 0
        for packet in packets:
            conn.execute(
                """
                INSERT INTO decision_packets (
                    packet_family_version, packet_family_revision, packet_type,
                    subject_type, subject_key, graph_snapshot_id,
                    graph_build_version, controller_snapshot_id,
                    controller_version, opportunity_snapshot_id,
                    opportunity_version, packet_algorithm_version, status,
                    coverage, evidence_coverage, payload_json, packet_checksum,
                    family_checksum, activated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    family.packet_family_version, family.packet_family_revision,
                    packet.packet_type, packet.subject_type, packet.subject_key,
                    family.graph_snapshot_id, graph_build_version,
                    family.controller_snapshot_id, controller_version,
                    family.opportunity_snapshot_id, opportunity_version,
                    family.algorithm_version, family.status, packet.coverage,
                    packet.evidence_coverage,
                    json.dumps(packet.payload, sort_keys=True, allow_nan=False),
                    packet_checksum(packet), family.family_checksum, None, now,
                ),
            )
            packet_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            for index, path in enumerate(packet.paths, 1):
                conn.execute(
                    """
                    INSERT INTO decision_packet_paths (
                        packet_id, path_order, path_kind,
                        source_opportunity_path_order, path_json,
                        evidence_ids_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (packet_id, index, path.path_kind,
                     path.source_opportunity_path_order,
                     json.dumps(path.path, allow_nan=False),
                     json.dumps(path.evidence_ids, allow_nan=False), now),
                )
            for index, evidence in enumerate(packet.evidence, 1):
                conn.execute(
                    """
                    INSERT INTO decision_packet_evidence (
                        packet_id, evidence_order, evidence_kind,
                        original_graph_evidence_id, source_table,
                        source_record_key_json, source_timestamp,
                        source_value_json, source_type, source_record_id,
                        content_hash, citation, review_status,
                        availability_state, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (packet_id, index, evidence.evidence_kind,
                     evidence.original_graph_evidence_id, evidence.source_table,
                     json.dumps(evidence.source_record_key, sort_keys=True),
                     evidence.source_timestamp,
                     json.dumps(evidence.source_value, sort_keys=True, allow_nan=False),
                     evidence.source_type, evidence.source_record_id,
                     evidence.content_hash, evidence.citation,
                     evidence.review_status, evidence.availability_state, now),
                )
            for index, risk in enumerate(packet.risks, 1):
                conn.execute(
                    """
                    INSERT INTO decision_packet_risks (
                        packet_id, risk_order, risk_category, risk_code,
                        risk_state, subject_key, constraint_key, source_table,
                        source_record_key_json, source_timestamp,
                        source_value_json, path_orders_json,
                        evidence_orders_json, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (packet_id, index, risk.risk_category, risk.risk_code,
                     risk.risk_state, risk.subject_key, risk.constraint_key,
                     risk.source_table,
                     json.dumps(risk.source_record_key, sort_keys=True),
                     risk.source_timestamp,
                     json.dumps(risk.source_value, sort_keys=True, allow_nan=False),
                     json.dumps(risk.path_orders),
                     json.dumps(risk.evidence_orders),
                     json.dumps(risk.metadata, sort_keys=True), now),
                )
            count += 1
        return count

    def get_packet_family(
        self, packet_family_version: str
    ) -> DecisionPacketFamily | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT packet_family_version, packet_family_revision,
                       graph_snapshot_id, controller_snapshot_id,
                       opportunity_snapshot_id, packet_algorithm_version,
                       status, family_checksum, activated_at, MIN(created_at) created_at,
                       COUNT(*) packet_count
                FROM decision_packets WHERE packet_family_version=?
                GROUP BY packet_family_version, packet_family_revision,
                         graph_snapshot_id, controller_snapshot_id,
                         opportunity_snapshot_id, packet_algorithm_version,
                         status, family_checksum, activated_at
                """,
                (packet_family_version,),
            ).fetchone()
            if row is None:
                return None
            counts = conn.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM decision_packet_paths p JOIN decision_packets d ON d.id=p.packet_id WHERE d.packet_family_version=?),
                  (SELECT COUNT(*) FROM decision_packet_evidence e JOIN decision_packets d ON d.id=e.packet_id WHERE d.packet_family_version=?),
                  (SELECT COUNT(*) FROM decision_packet_risks r JOIN decision_packets d ON d.id=r.packet_id WHERE d.packet_family_version=?)
                """,
                (packet_family_version,) * 3,
            ).fetchone()
        return DecisionPacketFamily(
            packet_family_version=str(row["packet_family_version"]),
            packet_family_revision=int(row["packet_family_revision"]),
            graph_snapshot_id=int(row["graph_snapshot_id"]),
            controller_snapshot_id=int(row["controller_snapshot_id"]),
            opportunity_snapshot_id=int(row["opportunity_snapshot_id"]),
            algorithm_version=str(row["packet_algorithm_version"]),
            status=str(row["status"]), family_checksum=str(row["family_checksum"]),
            packet_count=int(row["packet_count"]), path_count=int(counts[0]),
            evidence_count=int(counts[1]), risk_count=int(counts[2]),
            activated_at=row["activated_at"], created_at=str(row["created_at"]),
        )

    def get_active_packet_family(self) -> DecisionPacketFamily | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT packet_family_version FROM decision_packets
                WHERE status='active' ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
        return self.get_packet_family(str(row[0])) if row else None

    def get_decision_packets(
        self, packet_family_version: str | None = None
    ) -> list[DecisionPacket]:
        family = (
            self.get_packet_family(packet_family_version)
            if packet_family_version else self.get_active_packet_family()
        )
        if family is None:
            return []
        with self.connect() as conn:
            packet_rows = conn.execute(
                """
                SELECT * FROM decision_packets WHERE packet_family_version=?
                ORDER BY CASE packet_type
                  WHEN 'ThemeDecisionPacket' THEN 1
                  WHEN 'CompanyDecisionPacket' THEN 2 ELSE 3 END, subject_key
                """,
                (family.packet_family_version,),
            ).fetchall()
            results = []
            for row in packet_rows:
                packet_id = int(row["id"])
                paths = tuple(DecisionPacketPath(
                    path_kind=str(p["path_kind"]),
                    source_opportunity_path_order=int(p["source_opportunity_path_order"]),
                    path=tuple((str(n[0]), str(n[1])) for n in json.loads(p["path_json"])),
                    evidence_ids=tuple(json.loads(p["evidence_ids_json"])),
                ) for p in conn.execute(
                    "SELECT * FROM decision_packet_paths WHERE packet_id=? ORDER BY path_order",
                    (packet_id,),
                ).fetchall())
                evidence = tuple(DecisionPacketEvidence(
                    evidence_kind=str(e["evidence_kind"]),
                    original_graph_evidence_id=e["original_graph_evidence_id"],
                    source_table=str(e["source_table"]),
                    source_record_key=json.loads(e["source_record_key_json"]),
                    source_timestamp=e["source_timestamp"],
                    source_value=json.loads(e["source_value_json"]),
                    source_type=str(e["source_type"]),
                    source_record_id=str(e["source_record_id"]),
                    content_hash=str(e["content_hash"]), citation=e["citation"],
                    review_status=e["review_status"],
                    availability_state=str(e["availability_state"]),
                ) for e in conn.execute(
                    "SELECT * FROM decision_packet_evidence WHERE packet_id=? ORDER BY evidence_order",
                    (packet_id,),
                ).fetchall())
                risks = tuple(DecisionPacketRisk(
                    risk_category=str(r["risk_category"]), risk_code=str(r["risk_code"]),
                    risk_state=str(r["risk_state"]), subject_key=str(r["subject_key"]),
                    constraint_key=r["constraint_key"], source_table=r["source_table"],
                    source_record_key=json.loads(r["source_record_key_json"]),
                    source_timestamp=r["source_timestamp"],
                    source_value=json.loads(r["source_value_json"]),
                    path_orders=tuple(json.loads(r["path_orders_json"])),
                    evidence_orders=tuple(json.loads(r["evidence_orders_json"])),
                    metadata=json.loads(r["metadata_json"]),
                ) for r in conn.execute(
                    "SELECT * FROM decision_packet_risks WHERE packet_id=? ORDER BY risk_order",
                    (packet_id,),
                ).fetchall())
                results.append(DecisionPacket(
                    packet_type=str(row["packet_type"]),
                    subject_type=str(row["subject_type"]),
                    subject_key=str(row["subject_key"]),
                    coverage=float(row["coverage"]),
                    evidence_coverage=float(row["evidence_coverage"]),
                    payload=json.loads(row["payload_json"]),
                    paths=paths, evidence=evidence, risks=risks,
                ))
        return results


def export_to_networkx(
    repository: ThemeRepository | None = None,
    build_version: str | None = None,
    relationship_types: set[str] | frozenset[str] | None = None,
) -> nx.MultiDiGraph:
    return IndustrialGraphRepository(repository).export_to_networkx(
        build_version,
        relationship_types,
    )
