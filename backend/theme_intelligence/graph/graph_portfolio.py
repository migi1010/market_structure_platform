from __future__ import annotations

from theme_intelligence.graph.graph_models import GraphEdge, normalize_graph_id


def portfolio_edges(portfolios: list[object]) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    for portfolio in portfolios:
        portfolio_id = normalize_graph_id(str(getattr(portfolio, "portfolio_type", "")))
        if not portfolio_id:
            continue
        for allocation in getattr(portfolio, "themes", []) or []:
            theme = normalize_graph_id(
                str(getattr(allocation, "theme_id", "") or getattr(allocation, "theme", ""))
            )
            weight = float(getattr(allocation, "weight", 0) or 0)
            if not theme:
                continue
            edges.extend(
                [
                    GraphEdge("theme", theme, "portfolio", portfolio_id, "theme_portfolio", weight, "theme_portfolios"),
                    GraphEdge("portfolio", portfolio_id, "theme", theme, "portfolio_theme", weight, "theme_portfolios"),
                ]
            )
    return sorted(edges, key=lambda edge: edge.sort_key)
