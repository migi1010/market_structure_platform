from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import networkx as nx

from .stock_research_models import (
    StockResearchEvidenceStep,
    StockResearchMemo,
    StockResearchRelatedCompany,
    StockResearchRole,
    StockResearchThemeExposure,
)
from .stock_research_repository import (
    CompanyMetricProjection,
    StockResearchRepository,
    build_graph,
    edge_evidence_between,
    relationships_between,
)


ROLE_PRIORITY = {
    "Constraint Resolver": 5,
    "Controller": 4,
    "Supplier": 3,
    "Enabler": 2,
    "Beneficiary": 1,
}

SUPPLIER_RELATIONSHIPS = {
    "EQUIPMENT_PRODUCED_BY",
    "MATERIAL_SUPPLIED_BY",
    "SUPPLIES",
    "USES_SUPPLIER",
    "SUPPLY_CHAIN_ROLE",
}

RESOLVER_RELATIONSHIPS = {
    "CONSTRAINT_RESOLVED_BY_COMPANY",
    "PROCESS_RESOLVED_BY_COMPANY",
    "MATERIAL_RESOLVED_BY",
    "EQUIPMENT_RESOLVED_BY",
    "RESOLVED_BY",
}

ENABLER_RELATIONSHIPS = {
    "ENABLES",
    "MATERIAL_ENABLES_PROCESS",
    "EQUIPMENT_ENABLES_PROCESS",
    "TECHNOLOGY_ENABLES_PROCESS",
}

BENEFICIARY_RELATIONSHIPS = {
    "COMPANY_EXPOSED_TO_CONSTRAINT",
}


class StockResearchEngine:
    def __init__(self, repository: StockResearchRepository | None = None) -> None:
        self.repository = repository or StockResearchRepository()

    def build(self, ticker: str) -> StockResearchMemo:
        symbol = ticker.strip().upper()
        company_node = self.repository.load_company_node(symbol)
        company_name = str(company_node["display_name"]) if company_node else symbol
        edges = self.repository.load_active_graph_edges()
        graph = build_graph(edges)
        company_key = ("Company", str(company_node["canonical_key"]) if company_node else symbol)
        rankings = self.repository.load_theme_rankings()
        controllers = self.repository.load_controller_metrics(symbol)
        opportunities = self.repository.load_opportunity_metrics(symbol)
        decision_support = self.repository.load_decision_support_by_theme()

        exposures, paths = self._theme_exposure(graph, company_key, rankings)
        primary = exposures[0] if exposures else None
        roles = self._roles(graph, company_key, controllers, opportunities)
        evidence_chain = self._evidence_chain(
            graph,
            company_key,
            paths.get(primary.theme_id) if primary else None,
            roles,
            company_name,
        )
        completeness = self._research_completeness(
            exposures,
            roles,
            evidence_chain,
            controllers,
            opportunities,
        )
        support = self._decision_support(primary.theme_id if primary else None, decision_support)
        memo = StockResearchMemo(
            available=True,
            ticker=symbol,
            generated_at=datetime.now(UTC).isoformat(),
            company_header={
                "company_name": company_name,
                "ticker": symbol,
                "theme_rank": primary.rank if primary else None,
                "theme_lifecycle": primary.lifecycle if primary else "Unavailable",
                "research_coverage": completeness["coverage"],
                "primary_theme": primary.theme_name if primary else "Unavailable",
                "lineage": self.repository.active_lineage(),
            },
            supply_chain_roles=tuple(roles),
            theme_exposure=tuple(exposures),
            investment_thesis=self._investment_thesis(primary, roles, completeness),
            evidence_chain=tuple(evidence_chain),
            research_completeness=completeness,
            decision_support=support,
            related_companies=self._related_companies(graph, company_key, paths.get(primary.theme_id) if primary else None),
        )
        return memo

    @staticmethod
    def _theme_exposure(
        graph: nx.MultiDiGraph,
        company_key: tuple[str, str],
        rankings: dict[str, dict[str, Any]],
    ) -> tuple[list[StockResearchThemeExposure], dict[str, tuple[tuple[str, str], ...]]]:
        if company_key not in graph:
            return [], {}
        undirected = graph.to_undirected(as_view=True)
        rows: list[StockResearchThemeExposure] = []
        paths: dict[str, tuple[tuple[str, str], ...]] = {}
        for node, data in sorted(graph.nodes(data=True), key=lambda item: (item[0][0], item[0][1])):
            if node[0] != "Theme":
                continue
            try:
                path = tuple(nx.shortest_path(undirected, node, company_key))
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            if len(path) > 8:
                continue
            evidence_ids = _path_evidence(graph, path)
            ranking = rankings.get(str(node[1]), {})
            rank = ranking.get("rank")
            path_score = max(0.0, 100.0 - (len(path) - 2) * 12.5)
            evidence_score = min(100.0, len(evidence_ids) * 20.0)
            rows.append(
                StockResearchThemeExposure(
                    theme_id=str(node[1]),
                    theme_name=str(ranking.get("theme_name") or data.get("display_name") or node[1]),
                    rank=int(rank) if rank is not None else None,
                    lifecycle=str(ranking.get("lifecycle") or "MONITORING"),
                    importance=(path_score + evidence_score) / 2.0,
                    coverage=float(ranking.get("coverage") or evidence_score),
                    evidence_count=len(evidence_ids),
                )
            )
            paths[str(node[1])] = path
        rows.sort(key=lambda row: (row.rank if row.rank is not None else 9999, -row.importance, row.theme_id))
        return rows, paths

    @staticmethod
    def _roles(
        graph: nx.MultiDiGraph,
        company_key: tuple[str, str],
        controllers: list[CompanyMetricProjection],
        opportunities: list[CompanyMetricProjection],
    ) -> list[StockResearchRole]:
        buckets: dict[str, dict[str, Any]] = {}

        def add(role_type: str, description: str, importance: float, evidence_ids: tuple[int, ...]) -> None:
            current = buckets.setdefault(
                role_type,
                {
                    "role_type": role_type,
                    "role_description": description,
                    "role_importance": 0.0,
                    "evidence_ids": set(),
                },
            )
            current["role_importance"] = max(float(current["role_importance"]), float(importance))
            current["evidence_ids"].update(evidence_ids)

        for metric in controllers:
            add("Controller", ", ".join(metric.types) or "Evidence-backed controller metric", metric.score, metric.evidence_ids)
        for metric in opportunities:
            add("Beneficiary", ", ".join(metric.types) or "Evidence-backed opportunity metric", metric.score, metric.evidence_ids)

        if company_key in graph:
            connected = set(graph.predecessors(company_key)) | set(graph.successors(company_key))
            for neighbor in connected:
                relationships = set(relationships_between(graph, neighbor, company_key))
                evidence_ids = edge_evidence_between(graph, neighbor, company_key)
                importance = max(50.0, min(100.0, len(evidence_ids) * 20.0 + 50.0))
                if relationships & RESOLVER_RELATIONSHIPS:
                    add("Constraint Resolver", "Company resolves or relieves a persisted constraint/process bottleneck.", importance, evidence_ids)
                if relationships & SUPPLIER_RELATIONSHIPS:
                    add("Supplier", "Company supplies a persisted material, equipment, or supply-chain role.", importance, evidence_ids)
                if relationships & ENABLER_RELATIONSHIPS:
                    add("Enabler", "Company enables a persisted technology, process, or equipment path.", importance, evidence_ids)
                if relationships & BENEFICIARY_RELATIONSHIPS:
                    add("Beneficiary", "Company is explicitly exposed to a persisted constraint.", importance, evidence_ids)

        rows = [
            StockResearchRole(
                role_type=str(value["role_type"]),
                role_description=str(value["role_description"]),
                role_importance=float(value["role_importance"]),
                evidence_count=len(value["evidence_ids"]),
                evidence_ids=tuple(sorted(value["evidence_ids"])),
            )
            for value in buckets.values()
        ]
        return sorted(rows, key=lambda row: (-ROLE_PRIORITY.get(row.role_type, 0), -row.role_importance, row.role_type))

    @staticmethod
    def _evidence_chain(
        graph: nx.MultiDiGraph,
        company_key: tuple[str, str],
        path: tuple[tuple[str, str], ...] | None,
        roles: list[StockResearchRole],
        company_name: str,
    ) -> list[StockResearchEvidenceStep]:
        if not path:
            return [StockResearchEvidenceStep("Company", company_name, "graph_nodes" if company_key in graph else "ticker")]
        steps: list[StockResearchEvidenceStep] = []
        for index, node in enumerate(path):
            node_data = graph.nodes[node] if node in graph else {}
            step_type = "Bottleneck" if node[0] == "Constraint" else node[0]
            if node == company_key and roles:
                step_type = roles[0].role_type
            evidence_ids: tuple[int, ...] = ()
            if index > 0:
                evidence_ids = edge_evidence_between(graph, path[index - 1], node)
            steps.append(
                StockResearchEvidenceStep(
                    step_type=step_type,
                    label=str(node_data.get("display_name") or company_name if node == company_key else node[1]),
                    source="industrial_graph",
                    evidence_ids=evidence_ids,
                )
            )
        if steps[-1].step_type != "Company":
            steps.append(
                StockResearchEvidenceStep(
                    "Company",
                    company_name,
                    "industrial_graph",
                    evidence_ids=steps[-1].evidence_ids,
                )
            )
        return steps

    @staticmethod
    def _research_completeness(
        exposures: list[StockResearchThemeExposure],
        roles: list[StockResearchRole],
        chain: list[StockResearchEvidenceStep],
        controllers: list[CompanyMetricProjection],
        opportunities: list[CompanyMetricProjection],
    ) -> dict[str, Any]:
        evidence_count = len({item for step in chain for item in step.evidence_ids})
        role_score = min(100.0, len(roles) * 20.0)
        exposure_score = min(100.0, len(exposures) * 25.0)
        metric_score = min(100.0, (len(controllers) + len(opportunities)) * 30.0)
        evidence_strength = min(100.0, evidence_count * 20.0)
        coverage = round((role_score + exposure_score + metric_score + evidence_strength) / 4.0, 4)
        gaps = []
        if not exposures:
            gaps.append("No persisted theme exposure path for this ticker.")
        if not roles:
            gaps.append("No persisted controller, supplier, resolver, enabler, or beneficiary role.")
        if not opportunities:
            gaps.append("No active opportunity metric for this ticker.")
        return {
            "coverage": coverage,
            "evidence_strength": evidence_strength,
            "validation_status": "Evidence Available" if evidence_count > 0 else "Research Incomplete",
            "open_questions": ["Which additional evidence would change the company role?"] if gaps else [],
            "research_gaps": gaps,
        }

    @staticmethod
    def _decision_support(theme_id: str | None, support: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if not theme_id or theme_id not in support:
            return {
                "research_state": "Research Incomplete",
                "bull_case": [],
                "bear_case": [],
                "monitoring_triggers": [],
                "research_gaps": ["No active decision packet matched this stock's primary theme."],
            }
        payload = support[theme_id]["payload"]
        sections = payload.get("sections") if isinstance(payload, dict) else {}
        sections = sections if isinstance(sections, dict) else {}
        return {
            "research_state": "Evidence Available",
            "bull_case": _rows(sections.get("bull_case")),
            "bear_case": _rows(sections.get("bear_case")),
            "monitoring_triggers": _rows(sections.get("monitoring_triggers")),
            "research_gaps": _rows(sections.get("research_gaps")),
        }

    @staticmethod
    def _investment_thesis(
        primary: StockResearchThemeExposure | None,
        roles: list[StockResearchRole],
        completeness: dict[str, Any],
    ) -> dict[str, list[str]]:
        theme = primary.theme_name if primary else "No primary theme"
        role = roles[0].role_type if roles else "Role unavailable"
        return {
            "why_it_matters": [
                f"{theme}: company relevance is based on persisted {role} evidence."
            ] if primary and roles else [],
            "current_drivers": [
                f"Theme lifecycle: {primary.lifecycle}."
            ] if primary else [],
            "catalysts": [],
            "risks": list(completeness.get("research_gaps") or []),
            "research_gaps": list(completeness.get("research_gaps") or []),
        }

    @staticmethod
    def _related_companies(
        graph: nx.MultiDiGraph,
        company_key: tuple[str, str],
        path: tuple[tuple[str, str], ...] | None,
    ) -> dict[str, tuple[StockResearchRelatedCompany, ...]]:
        if not path:
            return {"same_theme": (), "same_bottleneck": (), "same_controller": (), "same_opportunity": ()}
        theme = next((node for node in path if node[0] == "Theme"), None)
        constraint = next((node for node in path if node[0] == "Constraint"), None)
        same_theme = _companies_near(graph, theme, company_key, "Same Theme", 6) if theme else ()
        same_bottleneck = _companies_near(graph, constraint, company_key, "Same Bottleneck", 3) if constraint else ()
        return {
            "same_theme": same_theme[:6],
            "same_bottleneck": same_bottleneck[:6],
            "same_controller": (),
            "same_opportunity": (),
        }


def _path_evidence(graph: nx.MultiDiGraph, path: tuple[tuple[str, str], ...]) -> tuple[int, ...]:
    evidence: set[int] = set()
    for index in range(1, len(path)):
        evidence.update(edge_evidence_between(graph, path[index - 1], path[index]))
    return tuple(sorted(evidence))


def _rows(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value] if isinstance(value, list) else []


def _companies_near(
    graph: nx.MultiDiGraph,
    start: tuple[str, str] | None,
    company_key: tuple[str, str],
    relationship: str,
    max_depth: int,
) -> tuple[StockResearchRelatedCompany, ...]:
    if start is None or start not in graph:
        return ()
    undirected = graph.to_undirected(as_view=True)
    rows: list[StockResearchRelatedCompany] = []
    for node, data in sorted(graph.nodes(data=True), key=lambda item: item[0][1]):
        if node[0] != "Company" or node == company_key:
            continue
        try:
            path = tuple(nx.shortest_path(undirected, start, node))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
        if len(path) > max_depth + 1:
            continue
        rows.append(
            StockResearchRelatedCompany(
                ticker=_display_ticker(str(node[1])),
                company_name=str(data.get("display_name") or node[1]),
                relationship=relationship,
                evidence_count=len(_path_evidence(graph, path)),
            )
        )
    return tuple(sorted(rows, key=lambda row: (-row.evidence_count, row.ticker)))


def _display_ticker(value: str) -> str:
    return value.removeprefix("company:").removeprefix("COMPANY:").upper()
