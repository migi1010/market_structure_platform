from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from typing import Iterator

from theme_intelligence.industrial_graph.graph_models import utc_now
from theme_intelligence.storage.theme_repository import ThemeRepository

from .research_pipeline_models import (
    ResearchPipelineCase,
    ResearchPipelineCaseDetail,
    ResearchPipelineEvent,
    ResearchPipelineLink,
    calculate_progress_from_link_types,
    lineage_checksum,
    validate_link_type,
    validate_source_type,
    validate_status,
)


class ResearchPipelineRepository:
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

    def create_case(
        self,
        *,
        source_type: str,
        source_id: str,
        theme_id: str,
        title: str,
    ) -> ResearchPipelineCase:
        normalized_source_type = validate_source_type(source_type)
        normalized_theme = theme_id.strip()
        normalized_source_id = source_id.strip()
        normalized_title = title.strip()
        if not normalized_source_id or not normalized_theme or not normalized_title:
            raise ValueError("Research pipeline case requires source_id, theme_id, and title")
        now = utc_now()
        case_id = f"research-case-{uuid.uuid4().hex}"
        checksum = lineage_checksum(
            normalized_source_type,
            normalized_source_id,
            normalized_theme,
            normalized_title,
        )
        with self.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                existing = conn.execute(
                    """
                    SELECT * FROM research_pipeline_cases
                    WHERE source_type=? AND source_id=?
                    """,
                    (normalized_source_type, normalized_source_id),
                ).fetchone()
                if existing is not None:
                    conn.commit()
                    return self._case_from_row(existing)
                conn.execute(
                    """
                    INSERT INTO research_pipeline_cases (
                        case_id, source_type, source_id, theme_id, title, status,
                        created_at, updated_at, activated_at, archived_at,
                        lineage_checksum
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id, normalized_source_type, normalized_source_id,
                        normalized_theme, normalized_title, "DISCOVERED",
                        now, now, None, None, checksum,
                    ),
                )
                self._insert_event(conn, case_id, None, "DISCOVERED", "case created", now)
                self._insert_link(conn, case_id, normalized_source_type, normalized_source_id, now)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        detail = self.get_case(case_id)
        if detail is None:
            raise RuntimeError("Research pipeline case was not persisted")
        return detail.case

    def list_cases(self) -> tuple[ResearchPipelineCaseDetail, ...]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM research_pipeline_cases ORDER BY updated_at DESC, created_at DESC, case_id"
            ).fetchall()
        return tuple(detail for row in rows if (detail := self.get_case(str(row["case_id"]))) is not None)

    def get_case(self, case_id: str) -> ResearchPipelineCaseDetail | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM research_pipeline_cases WHERE case_id=?",
                (case_id,),
            ).fetchone()
            if row is None:
                return None
            events = tuple(
                self._event_from_row(event)
                for event in conn.execute(
                    "SELECT * FROM research_pipeline_events WHERE case_id=? ORDER BY created_at, id",
                    (case_id,),
                ).fetchall()
            )
            links = tuple(
                self._link_from_row(link)
                for link in conn.execute(
                    "SELECT * FROM research_pipeline_links WHERE case_id=? ORDER BY linked_type, linked_id",
                    (case_id,),
                ).fetchall()
            )
        linked_types = {link.linked_type for link in links}
        return ResearchPipelineCaseDetail(
            case=self._case_from_row(row),
            events=events,
            links=links,
            progress=calculate_progress_from_link_types(linked_types),
        )

    def update_status(self, case_id: str, new_status: str, reason: str) -> ResearchPipelineCase:
        target = validate_status(new_status)
        now = utc_now()
        with self.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT * FROM research_pipeline_cases WHERE case_id=?",
                    (case_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Unknown research pipeline case: {case_id}")
                previous = str(row["status"])
                archived_at = now if target == "ARCHIVED" else row["archived_at"]
                activated_at = row["activated_at"] or (now if target == "APPROVED_RESEARCH" else None)
                conn.execute(
                    """
                    UPDATE research_pipeline_cases
                    SET status=?, updated_at=?, activated_at=?, archived_at=?
                    WHERE case_id=?
                    """,
                    (target, now, activated_at, archived_at, case_id),
                )
                self._insert_event(conn, case_id, previous, target, reason, now)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        detail = self.get_case(case_id)
        if detail is None:
            raise RuntimeError("Research pipeline case disappeared")
        return detail.case

    def link_artifact(self, case_id: str, linked_type: str, linked_id: str) -> ResearchPipelineLink:
        normalized_type = validate_link_type(linked_type)
        normalized_id = linked_id.strip()
        if not normalized_id:
            raise ValueError("Research pipeline link requires linked_id")
        now = utc_now()
        with self.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                if conn.execute("SELECT 1 FROM research_pipeline_cases WHERE case_id=?", (case_id,)).fetchone() is None:
                    raise KeyError(f"Unknown research pipeline case: {case_id}")
                link_id = self._insert_link(conn, case_id, normalized_type, normalized_id, now)
                conn.execute(
                    "UPDATE research_pipeline_cases SET updated_at=? WHERE case_id=?",
                    (now, case_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        detail = self.get_case(case_id)
        if detail is None:
            raise RuntimeError("Research pipeline case disappeared")
        return next(link for link in detail.links if link.link_id == link_id)

    @staticmethod
    def _insert_event(
        conn: sqlite3.Connection,
        case_id: str,
        previous_status: str | None,
        new_status: str,
        reason: str,
        now: str,
    ) -> str:
        event_id = f"research-event-{uuid.uuid4().hex}"
        conn.execute(
            """
            INSERT INTO research_pipeline_events (
                event_id, case_id, previous_status, new_status, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, case_id, previous_status, new_status, reason.strip(), now),
        )
        return event_id

    @staticmethod
    def _insert_link(
        conn: sqlite3.Connection,
        case_id: str,
        linked_type: str,
        linked_id: str,
        now: str,
    ) -> str:
        existing = conn.execute(
            """
            SELECT link_id FROM research_pipeline_links
            WHERE case_id=? AND linked_type=? AND linked_id=?
            """,
            (case_id, linked_type, linked_id),
        ).fetchone()
        if existing is not None:
            return str(existing["link_id"])
        link_id = f"research-link-{uuid.uuid4().hex}"
        conn.execute(
            """
            INSERT INTO research_pipeline_links (
                link_id, case_id, linked_type, linked_id, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (link_id, case_id, linked_type, linked_id, now),
        )
        return link_id

    @staticmethod
    def _case_from_row(row: sqlite3.Row) -> ResearchPipelineCase:
        return ResearchPipelineCase(
            case_id=str(row["case_id"]),
            source_type=str(row["source_type"]),
            source_id=str(row["source_id"]),
            theme_id=str(row["theme_id"]),
            title=str(row["title"]),
            status=str(row["status"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            activated_at=row["activated_at"],
            archived_at=row["archived_at"],
            lineage_checksum=str(row["lineage_checksum"]),
        )

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> ResearchPipelineEvent:
        return ResearchPipelineEvent(
            event_id=str(row["event_id"]),
            case_id=str(row["case_id"]),
            previous_status=row["previous_status"],
            new_status=str(row["new_status"]),
            reason=str(row["reason"]),
            created_at=str(row["created_at"]),
        )

    @staticmethod
    def _link_from_row(row: sqlite3.Row) -> ResearchPipelineLink:
        return ResearchPipelineLink(
            link_id=str(row["link_id"]),
            case_id=str(row["case_id"]),
            linked_type=str(row["linked_type"]),
            linked_id=str(row["linked_id"]),
            created_at=str(row["created_at"]),
        )
