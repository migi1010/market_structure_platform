from __future__ import annotations

import re
import sqlite3
from collections import defaultdict

from theme_intelligence.storage.theme_repository import ThemeRepository
from theme_intelligence.theme_registry.theme_registry_repository import (
    ThemeRegistryRepository,
)

from .theme_ranking_models import ThemeRankingSource


def _theme_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


class ThemeRankingRepository:
    """Read-only projection adapter over persisted theme source systems."""

    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()
        self.registry_repository = ThemeRegistryRepository(self.repository)

    def initialize(self) -> None:
        self.repository.initialize()

    def load_theme_sources(self) -> list[ThemeRankingSource]:
        self.initialize()
        registry_rows = self.registry_repository.graph_themes() + self.registry_repository.scout_themes() + self.registry_repository.pipeline_themes()
        sources: dict[str, dict[str, object]] = {}
        for row in registry_rows:
            sources.setdefault(row.theme_id, self._empty_source(row.theme_id, row.theme_name))
            target = sources[row.theme_id]
            target["theme_name"] = row.theme_name if row.source == "GRAPH" else target["theme_name"]
            target["has_active_graph"] = bool(target["has_active_graph"]) or row.graph_snapshot_count > 0
            target["has_scout_signal"] = bool(target["has_scout_signal"]) or row.source == "SCOUT"
            target["research_case_count"] = max(int(target["research_case_count"]), row.research_case_count)
            target["controller_count"] = max(int(target["controller_count"]), row.controller_count)
            target["opportunity_count"] = max(int(target["opportunity_count"]), row.opportunity_count)
            target["updated_at"] = max(str(target["updated_at"]), row.updated_at)

        with self.repository._connect() as conn:
            for theme_id, values in self._scout_metrics(conn).items():
                sources.setdefault(theme_id, self._empty_source(theme_id, values["theme_name"]))
                target = sources[theme_id]
                target.update(values)
                target["has_scout_signal"] = True
                target["updated_at"] = max(str(target["updated_at"]), str(values["updated_at"]))
            for theme_id, values in self._pipeline_counts(conn).items():
                sources.setdefault(theme_id, self._empty_source(theme_id, values["theme_name"]))
                target = sources[theme_id]
                for key in ("research_case_count", "approved_research_count", "monitoring_research_count"):
                    target[key] = max(int(target[key]), int(values[key]))
                target["updated_at"] = max(str(target["updated_at"]), str(values["updated_at"]))
            for theme_id, count in self._graph_evidence_counts(conn).items():
                sources.setdefault(theme_id, self._empty_source(theme_id, theme_id.replace("_", " ").title()))
                sources[theme_id]["graph_evidence_count"] = count

        return [ThemeRankingSource(**values) for _, values in sorted(sources.items())]

    @staticmethod
    def _empty_source(theme_id: str, theme_name: str) -> dict[str, object]:
        return {
            "theme_id": theme_id,
            "theme_name": theme_name or theme_id.replace("_", " ").title(),
            "has_active_graph": False,
            "has_scout_signal": False,
            "scout_theme_score": 0.0,
            "scout_velocity_score": 0.0,
            "scout_evidence_count": 0,
            "scout_signal_count": 0,
            "research_case_count": 0,
            "approved_research_count": 0,
            "monitoring_research_count": 0,
            "controller_count": 0,
            "opportunity_count": 0,
            "graph_evidence_count": 0,
            "updated_at": "",
        }

    @staticmethod
    def _scout_metrics(conn: sqlite3.Connection) -> dict[str, dict[str, object]]:
        snapshot = conn.execute(
            "SELECT id FROM theme_scout_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if snapshot is None:
            return {}
        rows = conn.execute(
            """
            SELECT candidate_key, name, theme_score, velocity_score, evidence_count,
                   signal_count, updated_at
            FROM theme_candidates
            WHERE snapshot_id=?
            ORDER BY candidate_key
            """,
            (int(snapshot["id"]),),
        ).fetchall()
        result: dict[str, dict[str, object]] = {}
        for row in rows:
            raw_key = str(row["candidate_key"] or "")
            if raw_key.startswith("candidate:"):
                raw_key = raw_key.split(":", 1)[1]
            theme_id = _theme_id(raw_key or str(row["name"]))
            result[theme_id] = {
                "theme_name": str(row["name"]),
                "scout_theme_score": float(row["theme_score"] or 0),
                "scout_velocity_score": float(row["velocity_score"] or 0),
                "scout_evidence_count": int(row["evidence_count"] or 0),
                "scout_signal_count": int(row["signal_count"] or 0),
                "updated_at": str(row["updated_at"] or ""),
            }
        return result

    @staticmethod
    def _pipeline_counts(conn: sqlite3.Connection) -> dict[str, dict[str, object]]:
        rows = conn.execute(
            """
            SELECT theme_id, MAX(title) AS title, MAX(updated_at) AS updated_at,
                   COUNT(*) AS total_count,
                   SUM(CASE WHEN status='APPROVED_RESEARCH' THEN 1 ELSE 0 END) AS approved_count,
                   SUM(CASE WHEN status='MONITORING' THEN 1 ELSE 0 END) AS monitoring_count
            FROM research_pipeline_cases
            WHERE status <> 'ARCHIVED'
            GROUP BY theme_id
            ORDER BY theme_id
            """
        ).fetchall()
        return {
            str(row["theme_id"]): {
                "theme_name": str(row["title"] or str(row["theme_id"]).replace("_", " ").title()),
                "research_case_count": int(row["total_count"] or 0),
                "approved_research_count": int(row["approved_count"] or 0),
                "monitoring_research_count": int(row["monitoring_count"] or 0),
                "updated_at": str(row["updated_at"] or ""),
            }
            for row in rows
        }

    @staticmethod
    def _graph_evidence_counts(conn: sqlite3.Connection) -> dict[str, int]:
        snapshot = conn.execute(
            "SELECT build_version FROM graph_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if snapshot is None:
            return {}
        rows = conn.execute(
            """
            SELECT gn.canonical_key AS theme_id, COUNT(DISTINCT gee.evidence_id) AS evidence_count
            FROM graph_nodes gn
            JOIN graph_edges ge
              ON ge.build_version=?
             AND ge.status='active'
             AND (ge.source_node_id=gn.id OR ge.target_node_id=gn.id)
            JOIN graph_edge_evidence gee ON gee.edge_id=ge.id
            WHERE gn.node_type='Theme'
            GROUP BY gn.canonical_key
            """,
            (str(snapshot["build_version"]),),
        ).fetchall()
        counts: defaultdict[str, int] = defaultdict(int)
        for row in rows:
            counts[str(row["theme_id"])] = int(row["evidence_count"] or 0)
        return dict(counts)
