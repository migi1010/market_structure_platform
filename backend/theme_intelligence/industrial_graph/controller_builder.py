from __future__ import annotations

from dataclasses import replace
from statistics import mean

import networkx as nx

from theme_intelligence.storage.theme_repository import ThemeRepository

from .controller_models import (
    CONTROLLER_TYPE_ORDER,
    DEPENDENCY_PROPAGATION_RELATIONSHIPS,
    POSITIVE_CONTROLLER_RELATIONSHIPS,
    ControllerBuild,
    ControllerIntelligence,
    ControllerMetric,
)
from .graph_models import NodeKey
from .graph_repository import IndustrialGraphRepository


_ANCHOR_REVERSE = frozenset({
    "EQUIPMENT_PRODUCED_BY", "MATERIAL_SUPPLIED_BY",
    "CONSTRAINT_RESOLVED_BY_COMPANY", "PROCESS_RESOLVED_BY_COMPANY",
    "EQUIPMENT_RESOLVED_BY", "MATERIAL_RESOLVED_BY",
})
_DEPENDENCY_REVERSE = frozenset({
    "USES_TECHNOLOGY", "REQUIRES_PROCESS", "PROCESS_REQUIRES_MATERIAL",
    "PROCESS_REQUIRES_EQUIPMENT", "THEME_DEPENDS_ON_MATERIAL",
    "THEME_DEPENDS_ON_EQUIPMENT", "THEME_LIMITED_BY_CONSTRAINT",
    "TECHNOLOGY_LIMITED_BY_CONSTRAINT", "PROCESS_LIMITED_BY_CONSTRAINT",
    "MATERIAL_LIMITED_BY_CONSTRAINT", "EQUIPMENT_LIMITED_BY_CONSTRAINT",
    "CONSTRAINT_DEPENDS_ON_MATERIAL", "CONSTRAINT_DEPENDS_ON_EQUIPMENT",
    "CONSTRAINT_DEPENDS_ON_PROCESS",
})
_RESOLUTION_RELATIONSHIPS = frozenset({
    "CONSTRAINT_RESOLVED_BY_COMPANY", "PROCESS_RESOLVED_BY_COMPANY",
    "EQUIPMENT_RESOLVED_BY", "MATERIAL_RESOLVED_BY",
})
_SUPPLY_RELATIONSHIPS = frozenset({"SUPPLIES", "CUSTOMER_OF", "DEPENDS_ON", "USES_SUPPLIER"})
_RAW_METRICS = (
    "degree_centrality_raw", "betweenness_centrality_raw",
    "dependency_reach_raw", "weighted_dependency_reach_raw",
    "dependency_coverage_raw", "constraint_coverage_raw",
    "material_coverage_raw", "equipment_coverage_raw",
    "process_coverage_raw", "technology_coverage_raw",
    "resolution_edge_count_raw", "supply_chain_edge_count_raw",
    "evidence_count_raw", "reasoning_path_count_raw",
)


def _percent(value: float, total: float) -> float:
    return 0.0 if total <= 0 else min(100.0, max(0.0, value / total * 100.0))


def _rounded(value: float) -> float:
    return round(float(value), 6)


class ControllerBuilder:
    MAX_PATH_DEPTH = 4
    ALGORITHM_VERSION = "controller-v1"

    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = IndustrialGraphRepository(repository or ThemeRepository())

    def build_projection(self, graph_build_version: str | None = None) -> nx.DiGraph:
        source = self.repository.export_controller_source_graph(graph_build_version)
        graph = nx.DiGraph()
        graph.graph.update(source.graph)
        for node, data in sorted(source.nodes(data=True)):
            graph.add_node(node, **data)
        allowed = POSITIVE_CONTROLLER_RELATIONSHIPS | DEPENDENCY_PROPAGATION_RELATIONSHIPS
        edges = sorted(
            source.edges(keys=True, data=True),
            key=lambda row: (row[0], row[1], str(row[2])),
        )
        for source_node, target_node, edge_id, data in edges:
            relationship = str(data["relationship_type"])
            if relationship not in allowed:
                continue
            reverse = relationship in _ANCHOR_REVERSE or relationship in _DEPENDENCY_REVERSE
            projected_source, projected_target = (
                (target_node, source_node) if reverse else (source_node, target_node)
            )
            positive = relationship in POSITIVE_CONTROLLER_RELATIONSHIPS
            strength = max(
                float(data.get("confidence_score") or 0),
                float(data.get("dependency_strength") or 0),
                1.0,
            )
            prior = graph.get_edge_data(projected_source, projected_target, default={})
            relationships = set(prior.get("relationship_types", ()))
            relationships.add(relationship)
            edge_ids = set(prior.get("source_edge_ids", ()))
            edge_ids.add(int(edge_id))
            evidence_ids = set(prior.get("evidence_ids", ()))
            evidence_ids.update(int(item) for item in data.get("evidence_ids", ()))
            graph.add_edge(
                projected_source,
                projected_target,
                relationship_types=tuple(sorted(relationships)),
                source_edge_ids=tuple(sorted(edge_ids)),
                evidence_ids=tuple(sorted(evidence_ids)),
                distance=min(float(prior.get("distance", 100.0)), 100.0 / strength),
                positive_anchor=bool(prior.get("positive_anchor", False) or positive),
                projected_from_reverse=bool(prior.get("projected_from_reverse", False) or reverse),
            )
        return graph

    def reasoning_paths(
        self, projection: nx.DiGraph, company: NodeKey, *, max_depth: int = 4
    ) -> tuple[tuple[NodeKey, ...], ...]:
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        if company not in projection:
            return ()
        paths: set[tuple[NodeKey, ...]] = set()
        for neighbor in sorted(projection.successors(company)):
            if not projection[company][neighbor].get("positive_anchor"):
                continue
            first = (company, neighbor)
            paths.add(first)
            if max_depth == 1:
                continue
            descendants = nx.single_source_shortest_path_length(
                projection, neighbor, cutoff=max_depth - 1
            )
            for target, depth in sorted(descendants.items()):
                if target == neighbor or target[0] == "Company" or depth < 1:
                    continue
                for suffix in nx.all_shortest_paths(projection, neighbor, target):
                    path = (company, *tuple(suffix))
                    if len(path) - 1 <= max_depth:
                        paths.add(path)
        return tuple(sorted(paths, key=lambda path: (len(path), path[-1][0], path[-1][1], path))[:25])

    def build(self, graph_build_version: str | None = None) -> ControllerBuild:
        projection = self.build_projection(graph_build_version)
        graph_snapshot_id = int(projection.graph["graph_snapshot_id"])
        graph_version = str(projection.graph["graph_build_version"])
        candidates = tuple(
            node for node in sorted(projection.nodes)
            if node[0] == "Company"
            and any(projection[node][target].get("positive_anchor") for target in projection.successors(node))
        )
        degree = nx.degree_centrality(projection)
        betweenness = nx.betweenness_centrality(projection, weight="distance", normalized=True)
        totals = {
            node_type: sum(1 for node in projection if node[0] == node_type)
            for node_type in ("Constraint", "Material", "Equipment", "Process", "Technology")
        }
        totals["NonCompany"] = sum(1 for node in projection if node[0] != "Company")
        total_resolution = sum(
            1 for _, _, data in projection.edges(data=True)
            if set(data["relationship_types"]) & _RESOLUTION_RELATIONSHIPS
        )
        total_supply = sum(
            1 for _, _, data in projection.edges(data=True)
            if set(data["relationship_types"]) & _SUPPLY_RELATIONSHIPS
        )
        metrics: list[ControllerMetric] = []
        controllers: list[ControllerIntelligence] = []
        for company in candidates:
            paths = self.reasoning_paths(projection, company)
            reachable = {node for path in paths for node in path[1:] if node[0] != "Company"}
            by_type = {
                node_type: {node for node in reachable if node[0] == node_type}
                for node_type in ("Constraint", "Material", "Equipment", "Process", "Technology")
            }
            path_lengths = {
                node: min(len(path) - 1 for path in paths if path[-1] == node)
                for node in reachable
            }
            anchor_edges = [
                projection[company][target]
                for target in projection.successors(company)
                if projection[company][target].get("positive_anchor")
            ]
            positive_types = {
                relationship for data in anchor_edges
                for relationship in data["relationship_types"]
                if relationship in POSITIVE_CONTROLLER_RELATIONSHIPS
            }
            evidence_ids = {
                evidence_id for path in paths
                for index in range(len(path) - 1)
                for evidence_id in projection[path[index]][path[index + 1]]["evidence_ids"]
            }
            resolution_count = sum(
                1 for data in anchor_edges
                if set(data["relationship_types"]) & _RESOLUTION_RELATIONSHIPS
            )
            supply_count = sum(
                1 for data in anchor_edges
                if set(data["relationship_types"]) & _SUPPLY_RELATIONSHIPS
            )
            weighted_reach = sum(1.0 / length for length in path_lengths.values())
            dependency_score = mean((
                _percent(len(reachable), totals["NonCompany"]),
                _percent(weighted_reach, totals["NonCompany"]),
                degree.get(company, 0.0) * 100.0,
                betweenness.get(company, 0.0) * 100.0,
            ))
            constraint = _percent(len(by_type["Constraint"]), totals["Constraint"])
            material = _percent(len(by_type["Material"]), totals["Material"])
            equipment = _percent(len(by_type["Equipment"]), totals["Equipment"])
            process = _percent(len(by_type["Process"]), totals["Process"])
            technology = _percent(len(by_type["Technology"]), totals["Technology"])
            resolution = _percent(resolution_count, total_resolution)
            supply = _percent(supply_count, total_supply)
            components = (
                dependency_score, constraint, resolution, equipment,
                material, process, technology, supply,
            )
            denominators = (
                totals["NonCompany"], totals["Constraint"], total_resolution,
                totals["Equipment"], totals["Material"], totals["Process"],
                totals["Technology"], total_supply,
            )
            applicable = [value for value, denominator in zip(components, denominators) if denominator > 0]
            coverage = _percent(sum(value > 0 for value in applicable), len(applicable))
            confidence = min(100.0, 20.0 * len(positive_types) + 10.0 * min(len(evidence_ids), 6))
            base = (
                dependency_score * 0.20 + constraint * 0.20 + resolution * 0.15
                + equipment * 0.10 + material * 0.10 + process * 0.10
                + technology * 0.05 + supply * 0.10
            )
            score = base * (0.50 + 0.50 * confidence / 100.0)
            types: list[str] = []
            if technology > 0:
                types.append("Technology Controller")
            if process > 0 or "PROCESS_RESOLVED_BY_COMPANY" in positive_types:
                types.append("Process Controller")
            if positive_types & {"MATERIAL_SUPPLIED_BY", "MATERIAL_RESOLVED_BY"}:
                types.append("Material Controller")
            if positive_types & {"EQUIPMENT_PRODUCED_BY", "EQUIPMENT_RESOLVED_BY"}:
                types.append("Equipment Controller")
            constraint_targets = [
                target for target in projection.successors(company)
                if target[0] == "Constraint"
                and "CONSTRAINT_RESOLVED_BY_COMPANY" in projection[company][target]["relationship_types"]
            ]
            if any(
                projection.nodes[target].get("external_ids", {}).get("category") == "Capacity Constraint"
                for target in constraint_targets
            ):
                types.append("Capacity Controller")
            if constraint_targets:
                types.append("Constraint Controller")
            if supply_count:
                types.append("Supply Chain Controller")
            types_tuple = tuple(item for item in CONTROLLER_TYPE_ORDER if item in types)
            raw = {
                "degree_centrality_raw": degree.get(company, 0.0),
                "betweenness_centrality_raw": betweenness.get(company, 0.0),
                "dependency_reach_raw": len(reachable),
                "weighted_dependency_reach_raw": weighted_reach,
                "dependency_coverage_raw": len(reachable) / totals["NonCompany"] if totals["NonCompany"] else 0,
                "constraint_coverage_raw": len(by_type["Constraint"]) / totals["Constraint"] if totals["Constraint"] else 0,
                "material_coverage_raw": len(by_type["Material"]) / totals["Material"] if totals["Material"] else 0,
                "equipment_coverage_raw": len(by_type["Equipment"]) / totals["Equipment"] if totals["Equipment"] else 0,
                "process_coverage_raw": len(by_type["Process"]) / totals["Process"] if totals["Process"] else 0,
                "technology_coverage_raw": len(by_type["Technology"]) / totals["Technology"] if totals["Technology"] else 0,
                "resolution_edge_count_raw": resolution_count,
                "supply_chain_edge_count_raw": supply_count,
                "evidence_count_raw": len(evidence_ids),
                "reasoning_path_count_raw": len(paths),
            }
            normalized = {
                "degree_centrality_raw": degree.get(company, 0.0) * 100,
                "betweenness_centrality_raw": betweenness.get(company, 0.0) * 100,
                "dependency_reach_raw": _percent(len(reachable), totals["NonCompany"]),
                "weighted_dependency_reach_raw": _percent(weighted_reach, totals["NonCompany"]),
                "dependency_coverage_raw": _percent(len(reachable), totals["NonCompany"]),
                "constraint_coverage_raw": constraint, "material_coverage_raw": material,
                "equipment_coverage_raw": equipment, "process_coverage_raw": process,
                "technology_coverage_raw": technology,
                "resolution_edge_count_raw": resolution,
                "supply_chain_edge_count_raw": supply,
                "evidence_count_raw": min(100.0, len(evidence_ids) * 10.0),
                "reasoning_path_count_raw": min(100.0, len(paths) * 4.0),
            }
            for metric_name in _RAW_METRICS:
                metrics.append(ControllerMetric(
                    company_key=company, metric_name=metric_name,
                    raw_value=_rounded(raw[metric_name]),
                    normalized_value=_rounded(normalized[metric_name]),
                    coverage=_rounded(coverage),
                    metadata={"algorithm_version": self.ALGORITHM_VERSION},
                ))
            controllers.append(ControllerIntelligence(
                company_key=company,
                company_name=str(projection.nodes[company].get("display_name") or company[1]),
                controller_types=types_tuple,
                dependency_score=_rounded(dependency_score),
                controller_score=_rounded(score), base_score=_rounded(base),
                constraint_influence=_rounded(constraint),
                material_control=_rounded(material), equipment_control=_rounded(equipment),
                process_control=_rounded(process), technology_control=_rounded(technology),
                resolution_influence=_rounded(resolution),
                supply_chain_influence=_rounded(supply), coverage=_rounded(coverage),
                coverage_confidence=_rounded(confidence),
                evidence_ids=tuple(sorted(evidence_ids)), reasoning_paths=paths,
            ))
        ranked = sorted(
            controllers,
            key=lambda row: (-row.controller_score, -row.coverage_confidence, -row.dependency_score, row.company_key),
        )
        ranked = [replace(row, rank=index) for index, row in enumerate(ranked, 1)]
        return ControllerBuild(
            graph_snapshot_id=graph_snapshot_id,
            graph_build_version=graph_version,
            algorithm_version=self.ALGORITHM_VERSION,
            metrics=tuple(metrics),
            controllers=tuple(ranked),
        )
