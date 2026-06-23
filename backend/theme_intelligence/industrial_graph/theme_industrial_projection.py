from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from theme_intelligence.discovery.discovery_models import theme_id
from theme_intelligence.industrial_graph.graph_models import (
    IndustrialGraphEdge,
    IndustrialGraphNode,
    NodeKey,
)
from theme_intelligence.industrial_graph.graph_repository import (
    IndustrialGraphRepository,
)
from theme_intelligence.storage.theme_repository import ThemeRepository


MAX_PATH_DEPTH = 7
DISPLAY_NODE_TYPES = frozenset({
    "Theme", "Industry", "Technology", "Process", "Material", "Equipment",
    "Constraint", "Company",
})
TERMINAL_NODE_TYPES = frozenset({"Company", "Supplier", "Customer"})
INDUSTRIAL_DEPENDENCY_RELATIONSHIPS = frozenset({
    "PART_OF_SUPPLY_CHAIN",
    "SUPPLY_CHAIN_ROLE",
    "SUPPLIES",
    "CUSTOMER_OF",
    "DEPENDS_ON",
    "USES_SUPPLIER",
    "USES_TECHNOLOGY",
    "REQUIRES_PROCESS",
    "TECHNOLOGY_ENABLES_PROCESS",
    "PROCESS_PRECEDES_PROCESS",
    "PROCESS_DEPENDS_ON_PROCESS",
    "PROCESS_REQUIRES_MATERIAL",
    "MATERIAL_ENABLES_PROCESS",
    "THEME_DEPENDS_ON_MATERIAL",
    "MATERIAL_SUPPLIED_BY",
    "PROCESS_REQUIRES_EQUIPMENT",
    "EQUIPMENT_ENABLES_PROCESS",
    "THEME_DEPENDS_ON_EQUIPMENT",
    "EQUIPMENT_PRODUCED_BY",
    "THEME_LIMITED_BY_CONSTRAINT",
    "TECHNOLOGY_LIMITED_BY_CONSTRAINT",
    "PROCESS_LIMITED_BY_CONSTRAINT",
    "MATERIAL_LIMITED_BY_CONSTRAINT",
    "EQUIPMENT_LIMITED_BY_CONSTRAINT",
    "CONSTRAINT_DEPENDS_ON_MATERIAL",
    "CONSTRAINT_DEPENDS_ON_EQUIPMENT",
    "CONSTRAINT_DEPENDS_ON_PROCESS",
    "CONSTRAINT_RESOLVED_BY_COMPANY",
    "PROCESS_RESOLVED_BY_COMPANY",
    "MATERIAL_RESOLVED_BY",
    "EQUIPMENT_RESOLVED_BY",
    "COMPANY_EXPOSED_TO_CONSTRAINT",
})
APPROVED_THEME_ALIASES = {
    "cpo": "cpo_photonics",
    "co_packaged_optics": "cpo_photonics",
    "cpo_photonics": "cpo_photonics",
}
CANONICAL_THEME_DISPLAY_NAMES = {
    "cpo_photonics": "CPO Photonics",
}
GAP_ORDER = {
    "NO_GRAPH_PATH": 0,
    "NO_TECHNOLOGY_EVIDENCE": 1,
    "NO_PROCESS_EVIDENCE": 2,
    "NO_MATERIAL_EVIDENCE": 3,
    "NO_EQUIPMENT_EVIDENCE": 4,
    "NO_CONSTRAINT_EVIDENCE": 5,
    "NO_COMPANY_EVIDENCE": 6,
    "NO_CONTROLLER_EVIDENCE": 7,
    "NO_OPPORTUNITY_EVIDENCE": 8,
    "NO_DECISION_PACKET_EVIDENCE": 9,
    "INCOMPLETE_LINEAGE": 10,
    "UNMATCHED_CONSTRAINT_SEVERITY": 11,
}
GAP_LABELS = {
    "NO_GRAPH_PATH": "No evidenced industrial dependency path",
    "NO_TECHNOLOGY_EVIDENCE": "Missing Technology evidence",
    "NO_PROCESS_EVIDENCE": "Missing Process evidence",
    "NO_MATERIAL_EVIDENCE": "Missing Material evidence",
    "NO_EQUIPMENT_EVIDENCE": "Missing Equipment evidence",
    "NO_CONSTRAINT_EVIDENCE": "Missing Constraint evidence",
    "NO_COMPANY_EVIDENCE": "Missing Company evidence",
    "NO_CONTROLLER_EVIDENCE": "Missing Controller evidence",
    "NO_OPPORTUNITY_EVIDENCE": "Missing Opportunity evidence",
    "NO_DECISION_PACKET_EVIDENCE": "Missing Decision Packet evidence",
    "INCOMPLETE_LINEAGE": "Active Phase 12 lineage is incomplete",
    "UNMATCHED_CONSTRAINT_SEVERITY": "Constraint severity is not established",
}


def _slug(value: str) -> str:
    return "_".join(part for part in theme_id(str(value or "")).split("_") if part)


@dataclass(frozen=True)
class CanonicalThemeIdentity:
    requested_theme_id: str
    canonical_theme_key: str
    display_name: str
    aliases: tuple[str, ...]
    resolution_state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CanonicalThemeResolver:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()
        self.graph_repository = IndustrialGraphRepository(self.repository)

    def resolve(self, value: str) -> CanonicalThemeIdentity:
        requested = _slug(value)
        nodes = [
            node for node in self.graph_repository.get_nodes()
            if node.node_type == "Theme"
        ]
        by_key = {node.canonical_key: node for node in nodes}
        by_name: dict[str, IndustrialGraphNode] = {}
        by_alias: dict[str, IndustrialGraphNode] = {}
        for node in nodes:
            by_name[_slug(node.display_name)] = node
            for alias in node.aliases:
                by_alias[_slug(alias)] = node

        node = by_key.get(requested) or by_name.get(requested) or by_alias.get(requested)
        resolution_state = "canonical"
        if node is None:
            alias_key = APPROVED_THEME_ALIASES.get(requested)
            node = by_key.get(alias_key or "")
            resolution_state = "alias"
        elif node.canonical_key != requested:
            resolution_state = "alias"
        if node is None:
            display_name = str(value or requested.replace("_", " ").title()).strip()
            return CanonicalThemeIdentity(
                requested_theme_id=requested,
                canonical_theme_key=requested,
                display_name=display_name,
                aliases=(),
                resolution_state="unresolved",
            )
        return CanonicalThemeIdentity(
            requested_theme_id=requested,
            canonical_theme_key=node.canonical_key,
            display_name=CANONICAL_THEME_DISPLAY_NAMES.get(
                node.canonical_key,
                node.display_name,
            ),
            aliases=node.aliases,
            resolution_state=resolution_state,
        )


class ThemeIndustrialProjectionService:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()
        self.graph_repository = IndustrialGraphRepository(self.repository)
        self.identity_resolver = CanonicalThemeResolver(self.repository)

    def get_theme(self, theme_value: str) -> dict[str, Any]:
        self.repository.initialize()
        identity = self.identity_resolver.resolve(theme_value)
        root = ("Theme", identity.canonical_theme_key)
        snapshot = self.graph_repository.get_active_snapshot()
        if snapshot is None:
            return self._empty_projection(identity, "unavailable")

        nodes = {node.identity_key: node for node in self.graph_repository.get_nodes()}
        all_edges = [
            edge for edge in self.graph_repository.get_edges(snapshot.build_version)
            if edge.relationship_type in INDUSTRIAL_DEPENDENCY_RELATIONSHIPS
        ]
        evidence_by_edge = {
            int(edge.id or 0): self.graph_repository.get_evidence_for_edge(int(edge.id or 0))
            for edge in all_edges
        }
        candidate_edges, candidate_nodes = self._bounded_candidates(root, all_edges)
        evidenced_edges = [
            edge for edge in candidate_edges
            if evidence_by_edge.get(int(edge.id or 0))
        ]
        dependency_paths = self._dependency_paths(
            root,
            evidenced_edges,
            nodes,
            evidence_by_edge,
        )
        visible_edge_keys = {
            (
                (edge["source_type"], edge["source_key"]),
                edge["relationship_type"],
                (edge["target_type"], edge["target_key"]),
            )
            for path in dependency_paths
            for edge in path["edges"]
        }
        visible_edges = [
            edge for edge in evidenced_edges
            if edge.base_identity_key in visible_edge_keys
        ]
        visible_node_keys = {
            key for edge in visible_edges for key in (edge.source_key, edge.target_key)
        }
        if root in nodes:
            visible_node_keys.add(root)

        controller_snapshot = self.graph_repository.get_active_controller_snapshot()
        opportunity_snapshot = self.graph_repository.get_active_opportunity_snapshot()
        packet_family = self.graph_repository.get_active_packet_family()
        lineage_state = self._lineage_state(
            snapshot.id,
            controller_snapshot,
            opportunity_snapshot,
            packet_family,
        )
        valid_pairs = self._valid_adjacency(all_edges)
        controllers = self._controllers(
            root, controller_snapshot, snapshot.id, valid_pairs, nodes
        )
        opportunities = self._opportunities(
            root, opportunity_snapshot, controller_snapshot, snapshot.id,
            valid_pairs, nodes,
        )
        packets = self._packets(
            root,
            packet_family,
            snapshot.id,
            controller_snapshot,
            opportunity_snapshot,
            {row["company_key"] for row in controllers},
            {row["company_key"] for row in opportunities},
            nodes,
        )
        constraints = self._constraints(
            visible_node_keys,
            visible_edges,
            evidence_by_edge,
            nodes,
            identity.display_name,
        )
        coverage = self._coverage(
            candidate_nodes,
            candidate_edges,
            evidence_by_edge,
        )
        gaps = self._gaps(
            visible_node_keys,
            dependency_paths,
            constraints,
            controllers,
            opportunities,
            packets,
            lineage_state,
        )
        graph_evidence_ids = {
            evidence.id
            for edge in visible_edges
            for evidence in evidence_by_edge.get(int(edge.id or 0), ())
            if evidence.id is not None
        }
        return {
            "identity": identity.to_dict(),
            "lineage": {
                "graph_snapshot_id": snapshot.id,
                "graph_build_version": snapshot.build_version,
                "controller_snapshot_id": getattr(controller_snapshot, "id", None),
                "controller_version": getattr(controller_snapshot, "controller_version", None),
                "opportunity_snapshot_id": getattr(opportunity_snapshot, "id", None),
                "opportunity_version": getattr(opportunity_snapshot, "opportunity_version", None),
                "packet_family_version": getattr(packet_family, "packet_family_version", None),
                "packet_family_revision": getattr(packet_family, "packet_family_revision", None),
                "lineage_state": lineage_state,
            },
            "graph": {
                "snapshot_id": snapshot.id,
                "build_version": snapshot.build_version,
                "nodes": [
                    self._node_dict(nodes[key])
                    for key in sorted(visible_node_keys)
                    if key in nodes and key[0] in DISPLAY_NODE_TYPES
                ],
                "edges": [
                    self._edge_dict(edge, evidence_by_edge)
                    for edge in sorted(visible_edges, key=lambda row: row.sort_key)
                ],
                "evidence_count": len(graph_evidence_ids),
                "dependency_paths": dependency_paths,
                "counts_by_type": self._counts_by_type(visible_node_keys),
            },
            "constraints": constraints,
            "controllers": controllers,
            "opportunities": opportunities,
            "decision_packets": packets,
            "coverage": coverage,
            "research_gaps": gaps,
        }

    def _empty_projection(
        self,
        identity: CanonicalThemeIdentity,
        lineage_state: str,
    ) -> dict[str, Any]:
        return {
            "identity": identity.to_dict(),
            "lineage": {
                "graph_snapshot_id": None,
                "graph_build_version": None,
                "controller_snapshot_id": None,
                "controller_version": None,
                "opportunity_snapshot_id": None,
                "opportunity_version": None,
                "packet_family_version": None,
                "packet_family_revision": None,
                "lineage_state": lineage_state,
            },
            "graph": {
                "snapshot_id": None,
                "build_version": None,
                "nodes": [],
                "edges": [],
                "evidence_count": 0,
                "dependency_paths": [],
                "counts_by_type": {},
            },
            "constraints": [],
            "controllers": [],
            "opportunities": [],
            "decision_packets": self._empty_packets(),
            "coverage": self._coverage(set(), [], {}),
            "research_gaps": [self._gap("NO_GRAPH_PATH", "graph", 0)],
        }

    @staticmethod
    def _bounded_candidates(
        root: NodeKey,
        edges: list[IndustrialGraphEdge],
    ) -> tuple[list[IndustrialGraphEdge], set[NodeKey]]:
        outgoing: dict[NodeKey, list[IndustrialGraphEdge]] = defaultdict(list)
        for edge in edges:
            outgoing[edge.source_key].append(edge)
        for rows in outgoing.values():
            rows.sort(key=lambda row: row.sort_key)
        candidate_edges: dict[object, IndustrialGraphEdge] = {}
        candidate_nodes: set[NodeKey] = {root}
        stack: list[tuple[NodeKey, int, frozenset[NodeKey]]] = [
            (root, 0, frozenset({root}))
        ]
        while stack:
            node, depth, seen = stack.pop()
            if depth >= MAX_PATH_DEPTH or node[0] in TERMINAL_NODE_TYPES:
                continue
            for edge in reversed(outgoing.get(node, ())):
                target = edge.target_key
                if target in seen:
                    continue
                if target[0] == "Theme" and target != root:
                    continue
                candidate_edges[edge.base_identity_key] = edge
                candidate_nodes.add(target)
                stack.append((target, depth + 1, seen | {target}))
        return (
            sorted(candidate_edges.values(), key=lambda row: row.sort_key),
            candidate_nodes,
        )

    def _dependency_paths(
        self,
        root: NodeKey,
        edges: list[IndustrialGraphEdge],
        nodes: dict[NodeKey, IndustrialGraphNode],
        evidence_by_edge: dict[int, list[Any]],
    ) -> list[dict[str, Any]]:
        outgoing: dict[NodeKey, list[IndustrialGraphEdge]] = defaultdict(list)
        for edge in edges:
            outgoing[edge.source_key].append(edge)
        for rows in outgoing.values():
            rows.sort(key=lambda row: row.sort_key)
        paths: list[tuple[tuple[NodeKey, ...], tuple[IndustrialGraphEdge, ...]]] = []

        def walk(
            node: NodeKey,
            path_nodes: tuple[NodeKey, ...],
            path_edges: tuple[IndustrialGraphEdge, ...],
        ) -> None:
            if path_edges and (
                node[0] in TERMINAL_NODE_TYPES
                or len(path_edges) >= MAX_PATH_DEPTH
                or not outgoing.get(node)
            ):
                paths.append((path_nodes, path_edges))
                return
            advanced = False
            for edge in outgoing.get(node, ()):
                target = edge.target_key
                if target in path_nodes:
                    continue
                if target[0] == "Theme" and target != root:
                    continue
                advanced = True
                walk(target, path_nodes + (target,), path_edges + (edge,))
            if path_edges and not advanced:
                paths.append((path_nodes, path_edges))

        if root in nodes:
            walk(root, (root,), ())
        unique = {
            (
                tuple(path_nodes),
                tuple(edge.base_identity_key for edge in path_edges),
            ): (path_nodes, path_edges)
            for path_nodes, path_edges in paths
        }
        result = []
        for index, (path_nodes, path_edges) in enumerate(
            sorted(
                unique.values(),
                key=lambda value: (
                    len(value[1]),
                    value[0],
                    tuple(edge.relationship_type for edge in value[1]),
                ),
            ),
            1,
        ):
            evidence_ids = sorted({
                evidence.id
                for edge in path_edges
                for evidence in evidence_by_edge.get(int(edge.id or 0), ())
                if evidence.id is not None
            })
            result.append({
                "path_id": f"path-{index:04d}",
                "depth": len(path_edges),
                "nodes": [self._node_dict(nodes[key]) for key in path_nodes],
                "edges": [
                    self._edge_dict(edge, evidence_by_edge) for edge in path_edges
                ],
                "evidence_ids": evidence_ids,
            })
        return result

    @staticmethod
    def _lineage_state(
        graph_snapshot_id: int | None,
        controller: Any,
        opportunity: Any,
        family: Any,
    ) -> str:
        if graph_snapshot_id is None:
            return "unavailable"
        if controller is None:
            return "graph_only"
        if controller.graph_snapshot_id != graph_snapshot_id:
            return "partial"
        if opportunity is None:
            return "partial"
        if (
            opportunity.graph_snapshot_id != graph_snapshot_id
            or opportunity.controller_snapshot_id != controller.id
        ):
            return "partial"
        if family is None:
            return "partial"
        if (
            family.graph_snapshot_id != graph_snapshot_id
            or family.controller_snapshot_id != controller.id
            or family.opportunity_snapshot_id != opportunity.id
        ):
            return "partial"
        return "complete"

    @staticmethod
    def _valid_adjacency(
        edges: Iterable[IndustrialGraphEdge],
    ) -> set[tuple[NodeKey, NodeKey]]:
        pairs = set()
        for edge in edges:
            pairs.add((edge.source_key, edge.target_key))
            pairs.add((edge.target_key, edge.source_key))
        return pairs

    @staticmethod
    def _valid_reasoning_path(
        path: tuple[NodeKey, ...],
        root: NodeKey,
        valid_pairs: set[tuple[NodeKey, NodeKey]],
    ) -> bool:
        if root not in path or len(path) < 2 or len(path) - 1 > MAX_PATH_DEPTH:
            return False
        if any(node[0] == "Theme" and node != root for node in path):
            return False
        return all((left, right) in valid_pairs for left, right in zip(path, path[1:]))

    def _path_dict(
        self,
        path: tuple[NodeKey, ...],
        root: NodeKey,
        nodes: dict[NodeKey, IndustrialGraphNode],
    ) -> dict[str, Any]:
        ordered = path[::-1] if path[-1] == root else path
        return {
            "nodes": [
                self._node_dict(nodes[key])
                if key in nodes
                else {
                    "node_type": key[0],
                    "canonical_key": key[1],
                    "display_name": key[1].split(":", 1)[-1].replace("_", " ").title(),
                    "aliases": [],
                    "external_ids": {},
                }
                for key in ordered
            ],
            "depth": len(ordered) - 1,
        }

    def _controllers(
        self,
        root: NodeKey,
        snapshot: Any,
        graph_snapshot_id: int | None,
        valid_pairs: set[tuple[NodeKey, NodeKey]],
        nodes: dict[NodeKey, IndustrialGraphNode],
    ) -> list[dict[str, Any]]:
        if snapshot is None or snapshot.graph_snapshot_id != graph_snapshot_id:
            return []
        result = []
        for row in self.graph_repository.get_controller_metrics(snapshot.controller_version):
            paths = [
                path for path in row.reasoning_paths
                if self._valid_reasoning_path(path, root, valid_pairs)
            ]
            if not paths:
                continue
            result.append({
                "company_key": row.company_key[1],
                "company_name": row.company_name,
                "rank": row.rank,
                "controller_score": row.controller_score,
                "controller_types": list(row.controller_types),
                "coverage": row.coverage,
                "coverage_confidence": row.coverage_confidence,
                "evidence_count": len(row.evidence_ids),
                "evidence_ids": list(row.evidence_ids),
                "reasoning_paths": [
                    self._path_dict(path, root, nodes) for path in sorted(paths)
                ],
            })
        return sorted(result, key=lambda item: (item["rank"], item["company_key"]))

    def _opportunities(
        self,
        root: NodeKey,
        snapshot: Any,
        controller_snapshot: Any,
        graph_snapshot_id: int | None,
        valid_pairs: set[tuple[NodeKey, NodeKey]],
        nodes: dict[NodeKey, IndustrialGraphNode],
    ) -> list[dict[str, Any]]:
        if (
            snapshot is None
            or controller_snapshot is None
            or snapshot.graph_snapshot_id != graph_snapshot_id
            or snapshot.controller_snapshot_id != controller_snapshot.id
        ):
            return []
        result = []
        for row in self.graph_repository.get_opportunity_metrics(snapshot.opportunity_version):
            paths = [
                path for path in row.reasoning_paths
                if self._valid_reasoning_path(path, root, valid_pairs)
            ]
            if not paths:
                continue
            result.append({
                "company_key": row.company_key[1],
                "company_name": row.company_name,
                "rank": row.rank,
                "opportunity_score": row.opportunity_score,
                "opportunity_types": list(row.opportunity_types),
                "coverage_component": row.coverage_component,
                "coverage_confidence": row.coverage_confidence,
                "controller_contribution": row.controller_component,
                "constraint_contribution": row.constraint_component,
                "evidence_count": len(row.evidence_ids),
                "evidence_ids": list(row.evidence_ids),
                "availability_states": row.availability_states,
                "reasoning_paths": [
                    self._path_dict(path, root, nodes) for path in sorted(paths)
                ],
            })
        return sorted(result, key=lambda item: (item["rank"], item["company_key"]))

    def _packets(
        self,
        root: NodeKey,
        family: Any,
        graph_snapshot_id: int | None,
        controller_snapshot: Any,
        opportunity_snapshot: Any,
        controller_keys: set[str],
        opportunity_keys: set[str],
        nodes: dict[NodeKey, IndustrialGraphNode],
    ) -> dict[str, Any]:
        if (
            family is None
            or controller_snapshot is None
            or opportunity_snapshot is None
            or family.graph_snapshot_id != graph_snapshot_id
            or family.controller_snapshot_id != controller_snapshot.id
            or family.opportunity_snapshot_id != opportunity_snapshot.id
        ):
            return self._empty_packets()
        theme_packet = None
        matching = []
        for packet in self.graph_repository.get_decision_packets(
            family.packet_family_version
        ):
            theme_paths = [path for path in packet.paths if root in path.path]
            is_theme = (
                packet.packet_type == "ThemeDecisionPacket"
                and packet.subject_key == root[1]
            )
            company_key = packet.subject_key.removeprefix("opportunity:")
            is_company = company_key in controller_keys or company_key in opportunity_keys
            if not is_theme and (not is_company or not theme_paths):
                continue
            summary = {
                "packet_type": packet.packet_type,
                "subject_type": packet.subject_type,
                "subject_key": packet.subject_key,
                "coverage": packet.coverage,
                "evidence_coverage": packet.evidence_coverage,
                "path_count": len(theme_paths) if theme_paths else len(packet.paths),
                "evidence_count": len(packet.evidence),
                "risk_count": len(packet.risks),
                "paths": [
                    self._path_dict(path.path, root, nodes)
                    for path in theme_paths
                ],
            }
            if is_theme:
                theme_packet = summary
            matching.append(summary)
        matching.sort(key=lambda item: (item["packet_type"], item["subject_key"]))
        return {
            "family": {
                "packet_family_version": family.packet_family_version,
                "packet_family_revision": family.packet_family_revision,
                "packet_count": family.packet_count,
                "path_count": family.path_count,
                "evidence_count": family.evidence_count,
                "risk_count": family.risk_count,
            },
            "theme_packet": theme_packet,
            "matching_packets": matching,
        }

    @staticmethod
    def _empty_packets() -> dict[str, Any]:
        return {"family": None, "theme_packet": None, "matching_packets": []}

    def _constraints(
        self,
        node_keys: set[NodeKey],
        edges: list[IndustrialGraphEdge],
        evidence_by_edge: dict[int, list[Any]],
        nodes: dict[NodeKey, IndustrialGraphNode],
        theme_name: str,
    ) -> list[dict[str, Any]]:
        bottlenecks = self.repository.get_bottlenecks(theme_name=theme_name)
        persisted = {
            _slug(getattr(row, "bottleneck_name", "")): row for row in bottlenecks
        }
        result = []
        for key in sorted(item for item in node_keys if item[0] == "Constraint"):
            node = nodes[key]
            incident = [
                edge for edge in edges
                if key in {edge.source_key, edge.target_key}
            ]
            evidence_ids = {
                evidence.id
                for edge in incident
                for evidence in evidence_by_edge.get(int(edge.id or 0), ())
                if evidence.id is not None
            }
            resolvers = sorted({
                edge.target_key[1]
                for edge in incident
                if edge.source_key == key
                and edge.relationship_type in {
                    "CONSTRAINT_RESOLVED_BY_COMPANY",
                    "PROCESS_RESOLVED_BY_COMPANY",
                    "MATERIAL_RESOLVED_BY",
                    "EQUIPMENT_RESOLVED_BY",
                }
                and edge.target_key[0] == "Company"
            })
            exposed = sorted({
                edge.source_key[1]
                for edge in incident
                if edge.target_key == key
                and edge.relationship_type == "COMPANY_EXPOSED_TO_CONSTRAINT"
                and edge.source_key[0] == "Company"
            })
            aliases = {_slug(node.display_name), *(_slug(alias) for alias in node.aliases)}
            matched = next((persisted[name] for name in sorted(aliases) if name in persisted), None)
            severity = (
                float(getattr(matched, "severity_score", 0))
                if matched is not None
                else None
            )
            result.append({
                "canonical_key": node.canonical_key,
                "display_name": node.display_name,
                "constraint_type": node.external_ids.get("category"),
                "evidence_count": len(evidence_ids),
                "resolver_company_keys": resolvers,
                "exposed_company_keys": exposed,
                "resolution_state": "resolved_evidence" if resolvers else "unresolved",
                "severity": severity,
                "severity_source": "theme_bottlenecks" if matched is not None else None,
                "coverage": 100.0 if evidence_ids else 0.0,
            })
        return result

    @staticmethod
    def _coverage(
        candidate_nodes: set[NodeKey],
        candidate_edges: list[IndustrialGraphEdge],
        evidence_by_edge: dict[int, list[Any]],
    ) -> dict[str, Any]:
        evidenced_edges = {
            edge.base_identity_key
            for edge in candidate_edges
            if evidence_by_edge.get(int(edge.id or 0))
        }
        evidenced_nodes = {
            key
            for edge in candidate_edges
            if edge.base_identity_key in evidenced_edges
            for key in (edge.source_key, edge.target_key)
        }
        components: dict[str, dict[str, Any]] = {}
        for node_type in (
            "Technology", "Process", "Material", "Equipment", "Constraint", "Company"
        ):
            denominator = sum(1 for key in candidate_nodes if key[0] == node_type)
            numerator = sum(1 for key in evidenced_nodes if key[0] == node_type)
            components[node_type] = ThemeIndustrialProjectionService._coverage_component(
                numerator, denominator
            )
        components["Evidence"] = ThemeIndustrialProjectionService._coverage_component(
            len(evidenced_edges),
            len(candidate_edges),
        )
        available = [
            row["coverage"] for row in components.values()
            if row["coverage"] is not None
        ]
        return {
            "components": components,
            "overall_coverage": sum(available) / len(available) if available else None,
        }

    @staticmethod
    def _coverage_component(numerator: int, denominator: int) -> dict[str, Any]:
        return {
            "numerator": numerator,
            "denominator": denominator,
            "coverage": numerator / denominator * 100 if denominator else None,
            "availability_state": "available" if denominator else "not_applicable",
        }

    def _gaps(
        self,
        node_keys: set[NodeKey],
        paths: list[dict[str, Any]],
        constraints: list[dict[str, Any]],
        controllers: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
        packets: dict[str, Any],
        lineage_state: str,
    ) -> list[dict[str, Any]]:
        gaps = []
        if not paths:
            gaps.append(self._gap("NO_GRAPH_PATH", "graph", 0))
        for node_type in (
            "Technology", "Process", "Material", "Equipment", "Constraint", "Company"
        ):
            count = sum(1 for key in node_keys if key[0] == node_type)
            if count == 0:
                gaps.append(self._gap(f"NO_{node_type.upper()}_EVIDENCE", node_type, count))
        if not controllers:
            gaps.append(self._gap("NO_CONTROLLER_EVIDENCE", "Controller", 0))
        if not opportunities:
            gaps.append(self._gap("NO_OPPORTUNITY_EVIDENCE", "Opportunity", 0))
        if packets["theme_packet"] is None:
            gaps.append(self._gap("NO_DECISION_PACKET_EVIDENCE", "Decision Packet", 0))
        if lineage_state != "complete":
            gaps.append(self._gap("INCOMPLETE_LINEAGE", "Lineage", 0))
        if any(row["severity"] is None for row in constraints):
            gaps.append(self._gap(
                "UNMATCHED_CONSTRAINT_SEVERITY",
                "Constraint",
                sum(row["severity"] is None for row in constraints),
            ))
        return sorted(gaps, key=lambda row: (GAP_ORDER[row["code"]], row["layer"]))

    @staticmethod
    def _gap(code: str, layer: str, count: int) -> dict[str, Any]:
        return {
            "code": code,
            "layer": layer,
            "state": "missing",
            "observed_count": count,
            "label": GAP_LABELS[code],
        }

    @staticmethod
    def _node_dict(node: IndustrialGraphNode) -> dict[str, Any]:
        return {
            "node_type": node.node_type,
            "canonical_key": node.canonical_key,
            "display_name": node.display_name,
            "aliases": list(node.aliases),
            "external_ids": dict(node.external_ids),
        }

    @staticmethod
    def _edge_dict(
        edge: IndustrialGraphEdge,
        evidence_by_edge: dict[int, list[Any]],
    ) -> dict[str, Any]:
        evidence = evidence_by_edge.get(int(edge.id or 0), ())
        return {
            "source_type": edge.source_key[0],
            "source_key": edge.source_key[1],
            "relationship_type": edge.relationship_type,
            "target_type": edge.target_key[0],
            "target_key": edge.target_key[1],
            "confidence_score": edge.confidence_score,
            "dependency_strength": edge.dependency_strength,
            "evidence_count": len(evidence),
            "evidence_ids": sorted(
                row.id for row in evidence if row.id is not None
            ),
        }

    @staticmethod
    def _counts_by_type(node_keys: set[NodeKey]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for node_type, _ in node_keys:
            if node_type in DISPLAY_NODE_TYPES:
                counts[node_type] += 1
        return dict(sorted(counts.items()))
