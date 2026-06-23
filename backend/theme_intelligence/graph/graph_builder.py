from __future__ import annotations

from theme_intelligence.graph.graph_models import GraphEdge, normalize_graph_id
from theme_intelligence.graph.graph_portfolio import portfolio_edges
from theme_intelligence.graph.graph_supply_chain import supply_chain_edges
from theme_intelligence.storage.theme_repository import ThemeRepository


class GraphBuilder:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()

    def build_base_edges(self) -> list[GraphEdge]:
        self.repository.initialize()
        edges: dict[tuple[str, str, str, str, str], GraphEdge] = {}

        def add(edge: GraphEdge) -> None:
            if not edge.source_id or not edge.target_id:
                return
            prior = edges.get(edge.identity_key)
            if prior is None or edge.strength_score > prior.strength_score:
                edges[edge.identity_key] = edge

        for edge in supply_chain_edges(self.repository.get_entities()):
            add(edge)
        for edge in portfolio_edges(self.repository.get_portfolios(limit=100)):
            add(edge)

        for catalyst in self.repository.get_catalysts():
            theme = normalize_graph_id(str(getattr(catalyst, "theme_name", "")))
            catalyst_name = normalize_graph_id(str(getattr(catalyst, "catalyst_name", "")))
            catalyst_type = normalize_graph_id(str(getattr(catalyst, "catalyst_type", "")))
            catalyst_id = ":".join(part for part in (catalyst_name, catalyst_type) if part)
            add(
                GraphEdge(
                    "theme",
                    theme,
                    "catalyst",
                    catalyst_id,
                    "theme_catalyst",
                    float(getattr(catalyst, "catalyst_strength", 0) or getattr(catalyst, "impact_score", 0) or 0),
                    "theme_catalysts",
                )
            )

        for bottleneck in self.repository.get_bottlenecks():
            theme = normalize_graph_id(str(getattr(bottleneck, "theme_name", "")))
            bottleneck_id = normalize_graph_id(str(getattr(bottleneck, "bottleneck_name", "")))
            strength = float(getattr(bottleneck, "bottleneck_strength", 0) or 0)
            add(GraphEdge("theme", theme, "bottleneck", bottleneck_id, "theme_bottleneck", strength, "theme_bottlenecks"))
            for controller in getattr(bottleneck, "controller_entities", []) or []:
                if not isinstance(controller, dict):
                    continue
                ticker = str(controller.get("ticker") or "").upper()
                if not ticker:
                    continue
                add(GraphEdge("theme", theme, "controller", ticker, "theme_controller", strength, "theme_bottlenecks"))
                add(GraphEdge("company", ticker, "bottleneck", bottleneck_id, "company_bottleneck", strength, "theme_bottlenecks"))

        for beneficiary in self.repository.get_beneficiary_scores():
            theme = normalize_graph_id(str(getattr(beneficiary, "theme_name", "")))
            ticker = str(getattr(beneficiary, "ticker", "") or "").upper()
            beneficiary_type = str(getattr(beneficiary, "beneficiary_type", "") or "")
            strength = float(
                getattr(beneficiary, "allocation_score", 0)
                or getattr(beneficiary, "beneficiary_score", 0)
                or 0
            )
            add(GraphEdge("theme", theme, "beneficiary", ticker, "theme_beneficiary", strength, "theme_beneficiary_scores"))
            add(GraphEdge("company", ticker, "theme", theme, "company_theme", strength, "theme_beneficiary_scores"))
            lowered = beneficiary_type.lower()
            if "controller" in lowered:
                add(GraphEdge("theme", theme, "controller", ticker, "theme_controller", strength, "theme_beneficiary_scores"))
            if "resolution" in lowered:
                add(
                    GraphEdge(
                        "theme",
                        theme,
                        "resolution_enabler",
                        ticker,
                        "theme_resolution_enabler",
                        strength,
                        "theme_beneficiary_scores",
                    )
                )

        return sorted(edges.values(), key=lambda edge: edge.sort_key)
