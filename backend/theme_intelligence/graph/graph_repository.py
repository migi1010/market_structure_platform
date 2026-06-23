from __future__ import annotations

from collections.abc import Iterable

from theme_intelligence.graph.graph_models import GraphEdge
from theme_intelligence.storage.theme_repository import ThemeRepository


class GraphRepository:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()

    def replace_edges(self, edges: Iterable[GraphEdge]) -> int:
        rows = sorted({edge.identity_key: edge for edge in edges}.values(), key=lambda edge: edge.sort_key)
        self.repository.initialize()
        with self.repository._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM theme_graph_edges")
            conn.executemany(
                """
                INSERT INTO theme_graph_edges (
                    source_type, source_id, target_type, target_id, relationship_type,
                    strength_score, evidence_source, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        edge.source_type,
                        edge.source_id,
                        edge.target_type,
                        edge.target_id,
                        edge.relationship_type,
                        max(0.0, min(100.0, float(edge.strength_score))),
                        edge.evidence_source,
                        edge.updated_at,
                    )
                    for edge in rows
                ],
            )
            conn.commit()
        return len(rows)

    def get_edges(
        self,
        *,
        source_type: str | None = None,
        source_id: str | None = None,
        relationship_type: str | None = None,
    ) -> list[GraphEdge]:
        self.repository.initialize()
        clauses: list[str] = []
        values: list[str] = []
        if source_type:
            clauses.append("source_type = ?")
            values.append(source_type)
        if source_id:
            clauses.append("source_id = ?")
            values.append(source_id)
        if relationship_type:
            clauses.append("relationship_type = ?")
            values.append(relationship_type)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.repository._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM theme_graph_edges
                {where}
                ORDER BY source_type, source_id, target_type, target_id, relationship_type
                """,
                values,
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get_theme_edges(self, theme_id: str) -> list[GraphEdge]:
        return self.get_edges(source_type="theme", source_id=theme_id)

    @staticmethod
    def _from_row(row: object) -> GraphEdge:
        return GraphEdge(
            id=int(row["id"]),  # type: ignore[index]
            source_type=str(row["source_type"]),  # type: ignore[index]
            source_id=str(row["source_id"]),  # type: ignore[index]
            target_type=str(row["target_type"]),  # type: ignore[index]
            target_id=str(row["target_id"]),  # type: ignore[index]
            relationship_type=str(row["relationship_type"]),  # type: ignore[index]
            strength_score=float(row["strength_score"]),  # type: ignore[index]
            evidence_source=str(row["evidence_source"]),  # type: ignore[index]
            updated_at=str(row["updated_at"]),  # type: ignore[index]
        )
