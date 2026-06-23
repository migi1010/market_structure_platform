from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import replace
from typing import Any

from theme_intelligence.industrial_graph.graph_builder import IndustrialGraphBuilder
from theme_intelligence.industrial_graph.graph_models import (
    IndustrialGraphBuild,
    IndustrialGraphSnapshot,
    canonical_json,
    utc_now,
)
from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository
from theme_intelligence.industrial_graph.graph_validator import GraphValidator
from theme_intelligence.storage.theme_repository import ThemeRepository


def _node_payload(node: Any) -> dict[str, Any]:
    return {
        "node_type": node.node_type,
        "canonical_key": node.canonical_key,
        "display_name": node.display_name,
        "aliases": list(node.aliases),
        "external_ids": dict(node.external_ids),
        "status": node.status,
        "valid_from": node.valid_from,
        "valid_to": node.valid_to,
    }


def _edge_payload(edge: Any) -> dict[str, Any]:
    return {
        "source_key": edge.source_key,
        "relationship_type": edge.relationship_type,
        "target_key": edge.target_key,
        "confidence_score": edge.confidence_score,
        "dependency_strength": edge.dependency_strength,
        "status": "building",
        "valid_to": edge.valid_to,
    }


def _evidence_payload(row: Any) -> dict[str, Any]:
    return {
        "source_type": row.source_type,
        "source_record_id": row.source_record_id,
        "content_hash": row.content_hash,
        "citation": row.citation,
        "observed_date": row.observed_date,
        "review_status": row.review_status,
    }


def build_checksum(build: IndustrialGraphBuild) -> str:
    payload = {
        "nodes": [_node_payload(row) for row in build.nodes],
        "edges": [_edge_payload(row) for row in build.edges],
        "evidence": [_evidence_payload(row) for row in build.evidence],
        "edge_evidence": [
            {"edge_key": row.edge_key, "evidence_key": row.evidence_key}
            for row in build.edge_evidence
        ],
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class IndustrialGraphSnapshotService:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        theme_repository = repository or ThemeRepository()
        self.repository = IndustrialGraphRepository(theme_repository)
        self.builder = IndustrialGraphBuilder(theme_repository)
        self.validator = GraphValidator()

    def build_and_activate(self) -> IndustrialGraphSnapshot:
        build = self.builder.build()
        self.validator.validate(build)
        staged = self.stage(build)
        return self.activate(staged.build_version)

    def stage(self, build: IndustrialGraphBuild) -> IndustrialGraphSnapshot:
        self.validator.validate(build)
        build_version = f"industrial-{uuid.uuid4().hex}"
        staged_at = utc_now()
        checksum = build_checksum(build)
        staged_edges = tuple(
            replace(
                edge,
                build_version=build_version,
                status="building",
                valid_from=staged_at,
                created_at=staged_at,
                updated_at=staged_at,
            )
            for edge in build.edges
        )
        referenced_nodes = {
            endpoint
            for edge in build.edges
            for endpoint in (edge.source_key, edge.target_key)
        }
        snapshot = IndustrialGraphSnapshot(
            build_version=build_version,
            status="building",
            source_watermark=build.source_watermark,
            node_count=len(referenced_nodes),
            edge_count=len(staged_edges),
            checksum=checksum,
            created_at=staged_at,
        )
        with self.repository.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                node_ids = self.repository.resolve_nodes(conn, build.nodes)
                evidence_ids = self.repository.resolve_evidence(conn, build.evidence)
                edge_ids = self.repository.insert_edges(conn, staged_edges, node_ids)
                self.repository.attach_evidence(conn, build.edge_evidence, edge_ids, evidence_ids)
                conn.execute(
                    """
                    INSERT INTO graph_snapshots (
                        build_version, status, source_watermark, node_count,
                        edge_count, checksum, activated_at, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.build_version,
                        snapshot.status,
                        snapshot.source_watermark,
                        snapshot.node_count,
                        snapshot.edge_count,
                        snapshot.checksum,
                        snapshot.activated_at,
                        snapshot.created_at,
                    ),
                )
                stored_edge_count = int(conn.execute(
                    "SELECT COUNT(*) FROM graph_edges WHERE build_version=?",
                    (build_version,),
                ).fetchone()[0])
                stored_node_count = int(conn.execute(
                    """
                    SELECT COUNT(DISTINCT node_id) FROM (
                        SELECT source_node_id AS node_id FROM graph_edges WHERE build_version=?
                        UNION
                        SELECT target_node_id AS node_id FROM graph_edges WHERE build_version=?
                    )
                    """,
                    (build_version, build_version),
                ).fetchone()[0])
                if stored_edge_count != snapshot.edge_count or stored_node_count != snapshot.node_count:
                    raise RuntimeError("staged graph counts do not match snapshot")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return snapshot

    def activate(self, build_version: str) -> IndustrialGraphSnapshot:
        with self.repository.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._activate_in_transaction(conn, build_version)
                row = conn.execute(
                    "SELECT * FROM graph_snapshots WHERE build_version=?",
                    (build_version,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Unknown graph build: {build_version}")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
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

    @staticmethod
    def _activate_in_transaction(conn: Any, build_version: str) -> None:
        row = conn.execute(
            "SELECT status FROM graph_snapshots WHERE build_version=?",
            (build_version,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown graph build: {build_version}")
        if str(row["status"]) not in {"building", "active"}:
            raise ValueError(f"Graph build is not activatable: {build_version}")
        activated_at = utc_now()
        conn.execute(
            """
            UPDATE graph_snapshots
            SET status='superseded'
            WHERE status='active' AND build_version<>?
            """,
            (build_version,),
        )
        conn.execute(
            """
            UPDATE graph_edges
            SET status='superseded', valid_to=?, updated_at=?
            WHERE status='active' AND build_version<>?
            """,
            (activated_at, activated_at, build_version),
        )
        conn.execute(
            """
            UPDATE graph_snapshots
            SET status='active', activated_at=?
            WHERE build_version=?
            """,
            (activated_at, build_version),
        )
        conn.execute(
            """
            UPDATE graph_edges
            SET status='active', updated_at=?
            WHERE build_version=?
            """,
            (activated_at, build_version),
        )

