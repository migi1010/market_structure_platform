from __future__ import annotations

import re
import sqlite3

from theme_intelligence.storage.theme_repository import ThemeRepository

from .theme_registry_models import ThemeRegistryEntry


def _theme_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _candidate_theme_id(candidate_key: str, name: str) -> str:
    raw = str(candidate_key or "").strip()
    if raw.startswith("candidate:"):
        raw = raw.split(":", 1)[1]
    return _theme_id(raw or name)


def _status_from_graph_node(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized == "archived":
        return "ARCHIVED"
    return "ACTIVE"


def _pipeline_registry_status(status: str) -> str:
    normalized = str(status or "").strip().upper()
    if normalized == "ARCHIVED":
        return "ARCHIVED"
    return "ACTIVE"


class ThemeRegistryRepository:
    """Read-only projection over persisted theme source systems."""

    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()

    def initialize(self) -> None:
        self.repository.initialize()

    def graph_themes(self) -> list[ThemeRegistryEntry]:
        self.initialize()
        with self.repository._connect() as conn:
            snapshot = conn.execute(
                "SELECT id, activated_at, created_at FROM graph_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if snapshot is None:
                return []
            rows = conn.execute(
                """
                SELECT
                    gn.canonical_key,
                    gn.display_name,
                    gn.status,
                    gn.updated_at,
                    COALESCE(tfs.research_importance, tds.final_ai_score, 0) AS rank_value,
                    COALESCE(rc.research_case_count, 0) AS research_case_count
                FROM graph_nodes gn
                LEFT JOIN theme_final_scores tfs
                    ON lower(tfs.theme_name)=lower(gn.display_name)
                LEFT JOIN theme_discovery_scores tds
                    ON tds.theme_id=gn.canonical_key
                       OR lower(tds.theme_name)=lower(gn.display_name)
                LEFT JOIN (
                    SELECT theme_id, COUNT(*) AS research_case_count
                    FROM research_pipeline_cases
                    WHERE status IN ('APPROVED_RESEARCH', 'MONITORING')
                    GROUP BY theme_id
                ) rc ON rc.theme_id=gn.canonical_key
                WHERE gn.node_type='Theme'
                  AND gn.status IN ('active', 'archived')
                ORDER BY gn.canonical_key
                """
            ).fetchall()
            controller_counts = self._controller_counts(conn)
            opportunity_counts = self._opportunity_counts(conn)
        return [
            ThemeRegistryEntry(
                theme_id=str(row["canonical_key"]),
                theme_name=str(row["display_name"]),
                status=_status_from_graph_node(str(row["status"])),  # type: ignore[arg-type]
                source="GRAPH",
                theme_type="INDUSTRIAL",
                rank=float(row["rank_value"] or 0),
                research_case_count=int(row["research_case_count"] or 0),
                graph_snapshot_count=1,
                controller_count=controller_counts.get(str(row["canonical_key"]), 0),
                opportunity_count=opportunity_counts.get(str(row["canonical_key"]), 0),
                updated_at=str(row["updated_at"] or snapshot["activated_at"] or snapshot["created_at"]),
            )
            for row in rows
        ]

    def scout_themes(self) -> list[ThemeRegistryEntry]:
        self.initialize()
        with self.repository._connect() as conn:
            snapshot = conn.execute(
                "SELECT id FROM theme_scout_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if snapshot is None:
                return []
            rows = conn.execute(
                """
                SELECT
                    candidate_key, name, status, theme_score, rank, updated_at
                FROM theme_candidates
                WHERE snapshot_id=?
                ORDER BY rank, candidate_key
                """,
                (int(snapshot["id"]),),
            ).fetchall()
        return [
            ThemeRegistryEntry(
                theme_id=_candidate_theme_id(str(row["candidate_key"]), str(row["name"])),
                theme_name=str(row["name"]),
                status="DISCOVERED" if str(row["status"]).upper() != "ARCHIVED" else "ARCHIVED",
                source="SCOUT",
                theme_type="EMERGING",
                rank=float(row["theme_score"] or 0),
                research_case_count=0,
                graph_snapshot_count=0,
                controller_count=0,
                opportunity_count=0,
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def pipeline_themes(self) -> list[ThemeRegistryEntry]:
        self.initialize()
        with self.repository._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    theme_id,
                    MAX(title) AS title,
                    MAX(updated_at) AS updated_at,
                    MAX(CASE WHEN status='ARCHIVED' THEN 1 ELSE 0 END) AS has_archived,
                    COUNT(*) AS research_case_count
                FROM research_pipeline_cases
                WHERE status IN ('APPROVED_RESEARCH', 'MONITORING', 'ARCHIVED')
                GROUP BY theme_id
                ORDER BY theme_id
                """
            ).fetchall()
        return [
            ThemeRegistryEntry(
                theme_id=str(row["theme_id"]),
                theme_name=str(row["title"] or str(row["theme_id"]).replace("_", " ").title()),
                status=_pipeline_registry_status("ARCHIVED" if int(row["has_archived"] or 0) else "APPROVED_RESEARCH"),  # type: ignore[arg-type]
                source="MANUAL",
                theme_type="INDUSTRIAL",
                rank=0,
                research_case_count=int(row["research_case_count"] or 0),
                graph_snapshot_count=0,
                controller_count=0,
                opportunity_count=0,
                updated_at=str(row["updated_at"] or ""),
            )
            for row in rows
        ]

    @staticmethod
    def _controller_counts(conn: sqlite3.Connection) -> dict[str, int]:
        rows = conn.execute(
            """
            SELECT gn.canonical_key AS theme_id, COUNT(DISTINCT cm.company_node_id) AS count_value
            FROM controller_metrics cm
            JOIN controller_snapshots cs ON cs.id=cm.controller_snapshot_id AND cs.status='active'
            JOIN graph_edges ge ON ge.build_version=cs.graph_build_version AND ge.status='active'
            JOIN graph_nodes gn ON gn.id=ge.source_node_id AND gn.node_type='Theme'
            GROUP BY gn.canonical_key
            """
        ).fetchall()
        return {str(row["theme_id"]): int(row["count_value"] or 0) for row in rows}

    @staticmethod
    def _opportunity_counts(conn: sqlite3.Connection) -> dict[str, int]:
        rows = conn.execute(
            """
            SELECT gn.canonical_key AS theme_id, COUNT(DISTINCT om.company_node_id) AS count_value
            FROM opportunity_metrics om
            JOIN opportunity_snapshots os ON os.id=om.opportunity_snapshot_id AND os.status='active'
            JOIN graph_edges ge ON ge.build_version=os.graph_build_version AND ge.status='active'
            JOIN graph_nodes gn ON gn.id=ge.source_node_id AND gn.node_type='Theme'
            GROUP BY gn.canonical_key
            """
        ).fetchall()
        return {str(row["theme_id"]): int(row["count_value"] or 0) for row in rows}
