from __future__ import annotations

from theme_intelligence.graph.graph_builder import GraphBuilder
from theme_intelligence.graph.graph_models import GraphEdge, ThemeOverlap, normalize_graph_id
from theme_intelligence.graph.graph_overlap import GraphOverlap
from theme_intelligence.graph.graph_ranker import rank_overlaps
from theme_intelligence.graph.graph_repository import GraphRepository
from theme_intelligence.storage.theme_repository import ThemeRepository


class GraphEngine:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()
        self.graph_repository = GraphRepository(self.repository)
        self.overlap = GraphOverlap()

    def rebuild(self) -> dict:
        base_edges = GraphBuilder(self.repository).build_base_edges()
        overlaps = self.overlap.all_overlaps(base_edges)
        overlap_edges: list[GraphEdge] = []
        for row in overlaps:
            overlap_edges.extend(
                [
                    GraphEdge("theme", row.theme_id, "theme", row.related_theme_id, "theme_overlap", row.overlap_score, "graph_overlap"),
                    GraphEdge("theme", row.related_theme_id, "theme", row.theme_id, "theme_overlap", row.overlap_score, "graph_overlap"),
                ]
            )
        count = self.graph_repository.replace_edges([*base_edges, *overlap_edges])
        return {"edge_count": count, "overlap_count": len(overlaps)}

    def get_graph(self) -> dict:
        edges = self.graph_repository.get_edges()
        return {
            "edges": [edge.to_api() for edge in edges],
            "source_status": {"edge_count": len(edges), "source": "persisted_phase_10"},
        }

    def get_theme_graph(self, theme_id: str) -> dict:
        normalized = normalize_graph_id(theme_id)
        edges = self.graph_repository.get_theme_edges(normalized)
        return {
            "theme_id": normalized,
            "edges": [edge.to_api() for edge in edges],
            "source_status": {"edge_count": len(edges), "source": "persisted_phase_10"},
        }

    def get_overlap(self, theme_id: str) -> dict:
        normalized = normalize_graph_id(theme_id)
        overlap_edges = [
            edge
            for edge in self.graph_repository.get_theme_edges(normalized)
            if edge.relationship_type == "theme_overlap"
        ]
        related = []
        for edge in sorted(overlap_edges, key=lambda row: row.strength_score, reverse=True):
            evidence_edges = self._base_edges(
                [
                    *self.graph_repository.get_theme_edges(normalized),
                    *self.graph_repository.get_theme_edges(edge.target_id),
                ]
            )
            detail = self.overlap.compare(normalized, edge.target_id, evidence_edges).to_api()
            detail["theme_id"] = normalized
            detail["related_theme_id"] = edge.target_id
            detail["overlap_score"] = round(edge.strength_score, 2)
            related.append(detail)
        return {"theme_id": normalized, "related_themes": related}

    def relationship_intelligence(self, theme_id: str) -> dict:
        overlap = self.get_overlap(theme_id)
        related = overlap["related_themes"]
        return {
            "related_themes": related,
            "shared_controllers": self._shared_values(related, "shared_controllers"),
            "shared_beneficiaries": self._shared_values(related, "shared_beneficiaries"),
            "portfolio_exposure": self._shared_values(related, "shared_portfolios"),
            "shared_supply_chain_roles": self._shared_values(related, "shared_supply_chain_roles"),
        }

    @staticmethod
    def _base_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
        return [edge for edge in edges if edge.relationship_type != "theme_overlap"]

    @staticmethod
    def _oriented(row: ThemeOverlap, theme_id: str) -> dict:
        payload = row.to_api()
        related_theme_id = row.related_theme_id if row.theme_id == theme_id else row.theme_id
        payload["theme_id"] = theme_id
        payload["related_theme_id"] = related_theme_id
        return payload

    @staticmethod
    def _shared_values(rows: list[dict], key: str) -> list[str]:
        return sorted({value for row in rows for value in row.get(key, [])})


def get_theme_graph() -> dict:
    return GraphEngine().get_graph()


def get_theme_graph_detail(theme_id: str) -> dict:
    return GraphEngine().get_theme_graph(theme_id)


def get_theme_overlap(theme_id: str) -> dict:
    return GraphEngine().get_overlap(theme_id)
