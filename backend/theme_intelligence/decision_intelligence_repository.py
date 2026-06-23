from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from theme_intelligence.research_pipeline.research_pipeline_models import ResearchPipelineCaseDetail
from theme_intelligence.research_pipeline.research_pipeline_repository import ResearchPipelineRepository
from theme_intelligence.storage.theme_repository import ThemeRepository


class DecisionIntelligenceRepository:
    """Read-only source adapter for Decision Intelligence projections."""

    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()
        self.pipeline_repository = ResearchPipelineRepository(self.repository)

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

    def list_research_cases(self) -> tuple[ResearchPipelineCaseDetail, ...]:
        return self.pipeline_repository.list_cases()

    def get_research_case(self, case_id: str) -> ResearchPipelineCaseDetail | None:
        return self.pipeline_repository.get_case(case_id)

    def source_table_counts(self) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            counts: dict[str, int] = {}
            for row in rows:
                table = str(row["name"])
                counts[table] = int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])
            return counts
