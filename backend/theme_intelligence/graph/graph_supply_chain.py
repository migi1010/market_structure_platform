from __future__ import annotations

from theme_intelligence.graph.graph_models import GraphEdge, normalize_graph_id


def supply_chain_edges(entities: list[object]) -> list[GraphEdge]:
    edges: dict[tuple[str, str, str, str, str], GraphEdge] = {}
    for entity in entities:
        theme = normalize_graph_id(str(getattr(entity, "theme_name", "")))
        ticker = str(getattr(entity, "ticker", "") or "").upper()
        role = normalize_graph_id(str(getattr(entity, "entity_type", "")))
        strength = float(getattr(entity, "relationship_strength", 0) or 0)
        if not theme:
            continue
        if ticker:
            for edge in (
                GraphEdge("theme", theme, "company", ticker, "theme_company", strength, "theme_entities"),
                GraphEdge("company", ticker, "theme", theme, "company_theme", strength, "theme_entities"),
            ):
                edges[edge.identity_key] = edge
        if role:
            edge = GraphEdge(
                "theme",
                theme,
                "supply_chain_role",
                role,
                "theme_supply_chain_role",
                strength,
                "theme_entities",
            )
            prior = edges.get(edge.identity_key)
            if prior is None or edge.strength_score > prior.strength_score:
                edges[edge.identity_key] = edge
    return sorted(edges.values(), key=lambda edge: edge.sort_key)
