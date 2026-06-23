from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

import networkx as nx

from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository
from theme_intelligence.storage.theme_repository import ThemeRepository
from theme_intelligence.theme_ranking.theme_ranking_engine import ThemeRankingEngine
from theme_intelligence.theme_ranking.theme_ranking_repository import ThemeRankingRepository


@dataclass(frozen=True)
class GraphEdgeProjection:
    source_type: str
    source_key: str
    source_name: str
    relationship_type: str
    target_type: str
    target_key: str
    target_name: str
    confidence_score: float
    dependency_strength: float
    evidence_ids: tuple[int, ...]


@dataclass(frozen=True)
class CompanyMetricProjection:
    company_key: str
    company_name: str
    rank: int
    score: float
    coverage: float
    types: tuple[str, ...]
    evidence_ids: tuple[int, ...]
    reasoning_paths: tuple[tuple[tuple[str, str], ...], ...]


class StockResearchRepository:
    """Read-only source adapter for Stock Research projections."""

    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()
        self.graph_repository = IndustrialGraphRepository(self.repository)

    def initialize(self) -> None:
        self.repository.initialize()

    def load_company_node(self, ticker: str) -> dict[str, Any] | None:
        self.initialize()
        candidates = _company_key_candidates(ticker)
        with self.repository._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM graph_nodes
                WHERE node_type='Company' AND UPPER(canonical_key) IN (?, ?)
                ORDER BY id DESC LIMIT 1
                """,
                candidates,
            ).fetchone()
        return dict(row) if row else None

    def load_active_graph_edges(self) -> list[GraphEdgeProjection]:
        self.initialize()
        with self.repository._connect() as conn:
            snapshot = self._active_graph_snapshot(conn)
            if snapshot is None:
                return []
            rows = conn.execute(
                """
                SELECT e.id, e.relationship_type, e.confidence_score,
                       e.dependency_strength,
                       sn.node_type AS source_type, sn.canonical_key AS source_key,
                       sn.display_name AS source_name,
                       tn.node_type AS target_type, tn.canonical_key AS target_key,
                       tn.display_name AS target_name,
                       GROUP_CONCAT(gee.evidence_id) AS evidence_ids
                FROM graph_edges e
                JOIN graph_nodes sn ON sn.id=e.source_node_id
                JOIN graph_nodes tn ON tn.id=e.target_node_id
                LEFT JOIN graph_edge_evidence gee ON gee.edge_id=e.id
                WHERE e.status='active' AND e.build_version=?
                GROUP BY e.id
                ORDER BY sn.node_type, sn.canonical_key, e.relationship_type,
                         tn.node_type, tn.canonical_key
                """,
                (str(snapshot["build_version"]),),
            ).fetchall()
        return [
            GraphEdgeProjection(
                source_type=str(row["source_type"]),
                source_key=str(row["source_key"]),
                source_name=str(row["source_name"]),
                relationship_type=str(row["relationship_type"]),
                target_type=str(row["target_type"]),
                target_key=str(row["target_key"]),
                target_name=str(row["target_name"]),
                confidence_score=float(row["confidence_score"] or 0),
                dependency_strength=float(row["dependency_strength"] or 0),
                evidence_ids=_parse_evidence_ids(row["evidence_ids"]),
            )
            for row in rows
        ]

    def load_controller_metrics(self, ticker: str) -> list[CompanyMetricProjection]:
        candidates = _company_key_candidates(ticker)
        with self.repository._connect() as conn:
            snapshot = conn.execute(
                "SELECT id FROM controller_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if snapshot is None:
                return []
            rows = conn.execute(
                """
                SELECT cm.*, gn.canonical_key AS company_key
                FROM controller_metrics cm
                JOIN graph_nodes gn ON gn.id=cm.company_node_id
                WHERE cm.controller_snapshot_id=? AND UPPER(gn.canonical_key) IN (?, ?)
                ORDER BY cm.rank, gn.canonical_key
                """,
                (int(snapshot["id"]), *candidates),
            ).fetchall()
        return [
            CompanyMetricProjection(
                company_key=str(row["company_key"]),
                company_name=str(row["company_name"]),
                rank=int(row["rank"]),
                score=float(row["controller_score"]),
                coverage=float(row["coverage"]),
                types=tuple(str(item) for item in _loads(row["controller_types_json"], [])),
                evidence_ids=tuple(int(item) for item in _loads(row["evidence_ids_json"], [])),
                reasoning_paths=_paths(row["reasoning_paths_json"]),
            )
            for row in rows
        ]

    def load_opportunity_metrics(self, ticker: str) -> list[CompanyMetricProjection]:
        candidates = _company_key_candidates(ticker)
        with self.repository._connect() as conn:
            snapshot = conn.execute(
                "SELECT id FROM opportunity_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if snapshot is None:
                return []
            rows = conn.execute(
                """
                SELECT om.*, gn.canonical_key AS company_key,
                       COALESCE((
                         SELECT json_group_array(path_json)
                         FROM opportunity_reasoning_paths p
                         WHERE p.opportunity_snapshot_id=om.opportunity_snapshot_id
                           AND p.company_node_id=om.company_node_id
                       ), '[]') AS path_rows
                FROM opportunity_metrics om
                JOIN graph_nodes gn ON gn.id=om.company_node_id
                WHERE om.opportunity_snapshot_id=? AND UPPER(gn.canonical_key) IN (?, ?)
                ORDER BY om.rank, gn.canonical_key
                """,
                (int(snapshot["id"]), *candidates),
            ).fetchall()
        results: list[CompanyMetricProjection] = []
        for row in rows:
            path_rows = _loads(row["path_rows"], [])
            paths = []
            for raw in path_rows:
                paths.extend(_paths(raw))
            results.append(
                CompanyMetricProjection(
                    company_key=str(row["company_key"]),
                    company_name=str(row["company_name"]),
                    rank=int(row["rank"]),
                    score=float(row["opportunity_score"]),
                    coverage=float(row["coverage_component"]),
                    types=tuple(str(item) for item in _loads(row["opportunity_types_json"], [])),
                    evidence_ids=tuple(int(item) for item in _loads(row["evidence_ids_json"], [])),
                    reasoning_paths=tuple(paths),
                )
            )
        return results

    def load_theme_rankings(self) -> dict[str, dict[str, Any]]:
        ranking_repository = ThemeRankingRepository(self.repository)
        rankings = ThemeRankingEngine().rank_themes(ranking_repository.load_theme_sources())
        return {
            row.theme_id: {
                "rank": index,
                "lifecycle": row.lifecycle,
                "theme_name": row.theme_name,
                "rank_score": row.rank_score,
                "coverage": max(row.evidence_score, row.research_score, row.controller_score, row.opportunity_score),
            }
            for index, row in enumerate(rankings, 1)
        }

    def load_decision_support_by_theme(self) -> dict[str, dict[str, Any]]:
        with self.repository._connect() as conn:
            rows = conn.execute(
                """
                SELECT subject_key, payload_json, coverage, evidence_coverage
                FROM decision_packets
                WHERE status='active' AND packet_type='ThemeDecisionPacket'
                ORDER BY subject_key
                """
            ).fetchall()
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            payload = _loads(row["payload_json"], {})
            result[str(row["subject_key"])] = {
                "payload": payload,
                "coverage": float(row["coverage"] or 0),
                "evidence_coverage": float(row["evidence_coverage"] or 0),
            }
        return result

    def active_lineage(self) -> dict[str, Any]:
        with self.repository._connect() as conn:
            graph = conn.execute(
                "SELECT id, build_version, checksum FROM graph_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            controller = conn.execute(
                "SELECT id, controller_version, checksum FROM controller_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            opportunity = conn.execute(
                "SELECT id, opportunity_version, checksum FROM opportunity_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            packet = conn.execute(
                "SELECT packet_family_version, family_checksum FROM decision_packets WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return {
            "graph_snapshot_id": int(graph["id"]) if graph else None,
            "graph_build_version": str(graph["build_version"]) if graph else None,
            "controller_snapshot_id": int(controller["id"]) if controller else None,
            "controller_version": str(controller["controller_version"]) if controller else None,
            "opportunity_snapshot_id": int(opportunity["id"]) if opportunity else None,
            "opportunity_version": str(opportunity["opportunity_version"]) if opportunity else None,
            "packet_family_version": str(packet["packet_family_version"]) if packet else None,
        }

    @staticmethod
    def _active_graph_snapshot(conn: sqlite3.Connection) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT * FROM graph_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
        ).fetchone()


def build_graph(edges: list[GraphEdgeProjection]) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    for edge in edges:
        source = (edge.source_type, edge.source_key)
        target = (edge.target_type, edge.target_key)
        graph.add_node(source, node_type=edge.source_type, canonical_key=edge.source_key, display_name=edge.source_name)
        graph.add_node(target, node_type=edge.target_type, canonical_key=edge.target_key, display_name=edge.target_name)
        graph.add_edge(
            source,
            target,
            relationship_type=edge.relationship_type,
            evidence_ids=edge.evidence_ids,
            confidence_score=edge.confidence_score,
            dependency_strength=edge.dependency_strength,
        )
    return graph


def _company_key_candidates(ticker: str) -> tuple[str, str]:
    normalized = ticker.strip().upper()
    prefixed = normalized if normalized.startswith("COMPANY:") else f"COMPANY:{normalized}"
    bare = normalized.removeprefix("COMPANY:")
    return bare, prefixed


def edge_evidence_between(graph: nx.MultiDiGraph, left: tuple[str, str], right: tuple[str, str]) -> tuple[int, ...]:
    evidence: set[int] = set()
    for source, target in ((left, right), (right, left)):
        data = graph.get_edge_data(source, target) or {}
        for edge in data.values():
            evidence.update(int(item) for item in edge.get("evidence_ids", ()) if item is not None)
    return tuple(sorted(evidence))


def relationships_between(graph: nx.MultiDiGraph, left: tuple[str, str], right: tuple[str, str]) -> tuple[str, ...]:
    relationships: set[str] = set()
    for source, target in ((left, right), (right, left)):
        data = graph.get_edge_data(source, target) or {}
        for edge in data.values():
            relationship = str(edge.get("relationship_type") or "").strip()
            if relationship:
                relationships.add(relationship)
    return tuple(sorted(relationships))


def _parse_evidence_ids(value: Any) -> tuple[int, ...]:
    if value is None:
        return ()
    return tuple(sorted({int(item) for item in str(value).split(",") if str(item).strip()}))


def _loads(value: Any, fallback: Any) -> Any:
    try:
        if value is None:
            return fallback
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return fallback


def _paths(value: Any) -> tuple[tuple[tuple[str, str], ...], ...]:
    rows = _loads(value, [])
    if not isinstance(rows, list):
        return ()
    if rows and isinstance(rows[0], list) and rows[0] and isinstance(rows[0][0], str):
        rows = [rows]
    paths = []
    for row in rows:
        if isinstance(row, list):
            path = []
            for node in row:
                if isinstance(node, (list, tuple)) and len(node) >= 2:
                    path.append((str(node[0]), str(node[1])))
            if path:
                paths.append(tuple(path))
    return tuple(paths)
