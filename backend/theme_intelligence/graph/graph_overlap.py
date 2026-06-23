from __future__ import annotations

from itertools import combinations

from theme_intelligence.graph.graph_models import GraphEdge, ThemeOverlap


RELATIONSHIP_COMPONENTS = {
    "theme_beneficiary": ("beneficiary_overlap", "shared_beneficiaries", 0.35),
    "theme_controller": ("controller_overlap", "shared_controllers", 0.25),
    "theme_bottleneck": ("bottleneck_overlap", "shared_bottlenecks", 0.15),
    "theme_catalyst": ("catalyst_overlap", "shared_catalysts", 0.15),
    "theme_portfolio": ("portfolio_overlap", "shared_portfolios", 0.10),
}


class GraphOverlap:
    def compare(self, first_theme: str, second_theme: str, edges: list[GraphEdge]) -> ThemeOverlap:
        first = self._evidence(first_theme, edges)
        second = self._evidence(second_theme, edges)
        components: dict[str, float] = {}
        shared: dict[str, list[str]] = {}
        score = 0.0
        for relationship, (component_name, shared_name, weight) in RELATIONSHIP_COMPONENTS.items():
            left = first.get(relationship, set())
            right = second.get(relationship, set())
            intersection = sorted(left & right)
            union = left | right
            component = round((len(intersection) / len(union) * 100.0) if union else 0.0, 2)
            components[component_name] = component
            shared[shared_name] = intersection
            score += component * weight
        supply_roles = sorted(
            first.get("theme_supply_chain_role", set())
            & second.get("theme_supply_chain_role", set())
        )
        return ThemeOverlap(
            theme_id=first_theme,
            related_theme_id=second_theme,
            overlap_score=round(max(0.0, min(100.0, score)), 2),
            components=components,
            shared_beneficiaries=shared["shared_beneficiaries"],
            shared_controllers=shared["shared_controllers"],
            shared_bottlenecks=shared["shared_bottlenecks"],
            shared_catalysts=shared["shared_catalysts"],
            shared_portfolios=shared["shared_portfolios"],
            shared_supply_chain_roles=supply_roles,
        )

    def all_overlaps(self, edges: list[GraphEdge]) -> list[ThemeOverlap]:
        themes = sorted({edge.source_id for edge in edges if edge.source_type == "theme"})
        rows: list[ThemeOverlap] = []
        for first, second in combinations(themes, 2):
            overlap = self.compare(first, second, edges)
            if overlap.overlap_score > 0:
                rows.append(overlap)
        return sorted(rows, key=lambda row: (-row.overlap_score, row.theme_id, row.related_theme_id))

    @staticmethod
    def _evidence(theme_id: str, edges: list[GraphEdge]) -> dict[str, set[str]]:
        grouped: dict[str, set[str]] = {}
        for edge in edges:
            if edge.source_type == "theme" and edge.source_id == theme_id:
                grouped.setdefault(edge.relationship_type, set()).add(edge.target_id)
        return grouped
