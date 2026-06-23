from __future__ import annotations

from theme_intelligence.industrial_graph.graph_models import (
    NODE_TYPES,
    RELATIONSHIP_TYPES,
    IndustrialGraphBuild,
)
from theme_intelligence.industrial_graph.supply_chain_taxonomy import canonical_supply_chain_role
from theme_intelligence.industrial_graph.supply_chain_taxonomy import SUPPLY_CHAIN_ROLES
from theme_intelligence.industrial_graph.technology_process_taxonomy import (
    PROCESSES,
    TECHNOLOGIES,
)
from theme_intelligence.industrial_graph.material_taxonomy import MATERIAL_CATEGORIES
from theme_intelligence.industrial_graph.equipment_taxonomy import EQUIPMENT_CATEGORIES
from theme_intelligence.industrial_graph.constraint_taxonomy import CONSTRAINT_CATEGORIES
from theme_intelligence.seeds.seed_validator import (
    _validate_constraints,
    _validate_equipment,
    _validate_materials,
    _validate_technology_process,
)


FORBIDDEN_SOURCE_MARKERS = (
    "quote",
    "yfinance",
    "frontend",
    "runtime_llm",
    "endpoint_cache",
    "portfolio",
)


class GraphValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = sorted(set(errors))
        super().__init__("; ".join(self.errors))


class GraphValidator:
    def validate_supply_chain_roles(self, themes: object) -> None:
        errors: list[str] = []
        for theme in themes:
            for role in getattr(theme, "supply_chain_roles", {}):
                try:
                    canonical_supply_chain_role(role)
                except ValueError:
                    errors.append(
                        f"unknown supply-chain role: {getattr(theme, 'theme_id', '<unknown>')}:{role}"
                    )
        if errors:
            raise GraphValidationError(errors)

    def validate_technology_process_seeds(self, themes: object) -> None:
        errors: list[str] = []
        for theme in themes:
            errors.extend(_validate_technology_process(theme))
        if errors:
            raise GraphValidationError(errors)

    def validate_material_seeds(self, themes: object) -> None:
        errors: list[str] = []
        for theme in themes:
            errors.extend(_validate_materials(theme))
        if errors:
            raise GraphValidationError(errors)

    def validate_equipment_seeds(self, themes: object) -> None:
        errors = _validate_equipment(themes)
        if errors:
            raise GraphValidationError(errors)

    def validate_constraint_seeds(self, themes: object) -> None:
        errors = _validate_constraints(themes)
        if errors:
            raise GraphValidationError(errors)

    def validate(self, build: IndustrialGraphBuild) -> None:
        errors: list[str] = []
        if not build.nodes:
            errors.append("build has no nodes")

        node_keys = [node.identity_key for node in build.nodes]
        if len(node_keys) != len(set(node_keys)):
            errors.append("duplicate canonical node")
        for node in build.nodes:
            if node.node_type not in NODE_TYPES:
                errors.append(f"missing node type or invalid node type: {node.node_type}")
            if not node.canonical_key:
                errors.append("missing canonical key")

        evidence_keys = [row.identity_key for row in build.evidence]
        if len(evidence_keys) != len(set(evidence_keys)):
            errors.append("duplicate evidence")
        evidence_key_set = set(evidence_keys)
        for row in build.evidence:
            lowered = row.source_type.lower()
            if any(marker in lowered for marker in FORBIDDEN_SOURCE_MARKERS):
                errors.append(f"forbidden source: {row.source_type}")
            if not row.citation.strip():
                errors.append(f"missing provenance citation: {row.source_record_id}")

        edge_keys = [edge.base_identity_key for edge in build.edges]
        if len(edge_keys) != len(set(edge_keys)):
            errors.append("duplicate edge")
        node_key_set = set(node_keys)
        supply_chain_role_keys = {
            node.identity_key
            for node in build.nodes
            if node.node_type == "Industry"
            and node.canonical_key.startswith("supply_chain:")
        }
        connected_supply_chain_roles: set[object] = set()
        technology_keys = {node.identity_key for node in build.nodes if node.node_type == "Technology"}
        process_keys = {node.identity_key for node in build.nodes if node.node_type == "Process"}
        connected_technologies: set[object] = set()
        connected_processes: set[object] = set()
        material_keys = {node.identity_key for node in build.nodes if node.node_type == "Material"}
        connected_materials: set[object] = set()
        equipment_keys = {node.identity_key for node in build.nodes if node.node_type == "Equipment"}
        connected_equipment: set[object] = set()
        constraint_keys = {node.identity_key for node in build.nodes if node.node_type == "Constraint"}
        connected_constraints: set[object] = set()
        for node in build.nodes:
            if node.identity_key in supply_chain_role_keys and node.display_name not in SUPPLY_CHAIN_ROLES:
                errors.append(f"missing supply-chain role: {node.identity_key}")
            if node.node_type == "Technology" and node.display_name not in TECHNOLOGIES:
                errors.append(f"unknown technology: {node.identity_key}")
            if node.node_type == "Process" and node.display_name not in PROCESSES:
                errors.append(f"unknown process: {node.identity_key}")
            if node.node_type == "Material":
                category = str(node.external_ids.get("category") or "")
                if category not in MATERIAL_CATEGORIES:
                    errors.append(f"unknown material category: {node.identity_key}")
            if node.node_type == "Equipment":
                category = str(node.external_ids.get("category") or "")
                if category not in EQUIPMENT_CATEGORIES:
                    errors.append(f"unknown equipment category: {node.identity_key}")
            if node.node_type == "Constraint":
                category = str(node.external_ids.get("category") or "")
                if category not in CONSTRAINT_CATEGORIES:
                    errors.append(f"unknown constraint category: {node.identity_key}")
        for edge in build.edges:
            if edge.relationship_type not in RELATIONSHIP_TYPES:
                errors.append(f"invalid relationship type: {edge.relationship_type}")
            if edge.source_key not in node_key_set or edge.target_key not in node_key_set:
                errors.append(f"orphan edge: {edge.base_identity_key}")
            if edge.relationship_type == "PART_OF_SUPPLY_CHAIN":
                if edge.source_key[0] != "Theme" or edge.target_key not in supply_chain_role_keys:
                    errors.append(f"invalid supply-chain role edge: {edge.base_identity_key}")
                connected_supply_chain_roles.add(edge.target_key)
            if edge.relationship_type == "SUPPLY_CHAIN_ROLE":
                if edge.source_key not in supply_chain_role_keys or edge.target_key[0] not in {
                    "Company",
                    "Supplier",
                    "Customer",
                }:
                    errors.append(f"invalid supply-chain company edge: {edge.base_identity_key}")
                connected_supply_chain_roles.add(edge.source_key)
            if edge.relationship_type == "USES_TECHNOLOGY":
                if edge.source_key[0] != "Theme" or edge.target_key not in technology_keys:
                    errors.append(f"invalid technology edge: {edge.base_identity_key}")
                connected_technologies.add(edge.target_key)
            if edge.relationship_type in {"REQUIRES_PROCESS", "TECHNOLOGY_ENABLES_PROCESS"}:
                if edge.source_key not in technology_keys or edge.target_key not in process_keys:
                    errors.append(f"invalid technology-process edge: {edge.base_identity_key}")
                connected_technologies.add(edge.source_key)
                connected_processes.add(edge.target_key)
            if edge.relationship_type in {
                "PROCESS_PRECEDES_PROCESS",
                "PROCESS_DEPENDS_ON_PROCESS",
            }:
                if (
                    edge.source_key not in process_keys
                    or edge.target_key not in process_keys
                    or edge.source_key == edge.target_key
                ):
                    errors.append(f"invalid process dependency: {edge.base_identity_key}")
                connected_processes.update((edge.source_key, edge.target_key))
            if edge.relationship_type == "PROCESS_LIMITED_BY_CONSTRAINT":
                if edge.source_key not in process_keys or edge.target_key[0] != "Constraint":
                    errors.append(f"invalid process constraint edge: {edge.base_identity_key}")
                connected_processes.add(edge.source_key)
            if edge.relationship_type == "PROCESS_RESOLVED_BY_COMPANY":
                if edge.source_key not in process_keys or edge.target_key[0] != "Company":
                    errors.append(f"invalid process company edge: {edge.base_identity_key}")
                connected_processes.add(edge.source_key)
            if edge.relationship_type == "PROCESS_REQUIRES_MATERIAL":
                if edge.source_key not in process_keys or edge.target_key not in material_keys:
                    errors.append(f"invalid process-material edge: {edge.base_identity_key}")
                connected_processes.add(edge.source_key)
                connected_materials.add(edge.target_key)
            if edge.relationship_type == "MATERIAL_ENABLES_PROCESS":
                if edge.source_key not in material_keys or edge.target_key not in process_keys:
                    errors.append(f"invalid material-process edge: {edge.base_identity_key}")
                connected_materials.add(edge.source_key)
                connected_processes.add(edge.target_key)
            if edge.relationship_type == "THEME_DEPENDS_ON_MATERIAL":
                if edge.source_key[0] != "Theme" or edge.target_key not in material_keys:
                    errors.append(f"invalid theme-material edge: {edge.base_identity_key}")
                connected_materials.add(edge.target_key)
            if edge.relationship_type == "MATERIAL_SUPPLIED_BY":
                if edge.source_key not in material_keys or edge.target_key[0] not in {
                    "Company",
                    "Supplier",
                }:
                    errors.append(f"invalid material supplier edge: {edge.base_identity_key}")
                connected_materials.add(edge.source_key)
            if edge.relationship_type == "MATERIAL_SUBSTITUTES_FOR":
                if (
                    edge.source_key not in material_keys
                    or edge.target_key not in material_keys
                    or edge.source_key == edge.target_key
                ):
                    errors.append(f"invalid material substitution: {edge.base_identity_key}")
                connected_materials.update((edge.source_key, edge.target_key))
            if edge.relationship_type == "MATERIAL_LIMITED_BY":
                if edge.source_key not in material_keys or edge.target_key[0] != "Constraint":
                    errors.append(f"invalid material constraint edge: {edge.base_identity_key}")
                connected_materials.add(edge.source_key)
            if edge.relationship_type == "MATERIAL_RESOLVED_BY":
                if edge.source_key not in material_keys or edge.target_key[0] != "Company":
                    errors.append(f"invalid material resolution edge: {edge.base_identity_key}")
                connected_materials.add(edge.source_key)
            if edge.relationship_type == "PROCESS_REQUIRES_EQUIPMENT":
                if edge.source_key not in process_keys or edge.target_key not in equipment_keys:
                    errors.append(f"invalid process-equipment edge: {edge.base_identity_key}")
                connected_processes.add(edge.source_key)
                connected_equipment.add(edge.target_key)
            if edge.relationship_type == "EQUIPMENT_ENABLES_PROCESS":
                if edge.source_key not in equipment_keys or edge.target_key not in process_keys:
                    errors.append(f"invalid equipment-process edge: {edge.base_identity_key}")
                connected_equipment.add(edge.source_key)
                connected_processes.add(edge.target_key)
            if edge.relationship_type == "THEME_DEPENDS_ON_EQUIPMENT":
                if edge.source_key[0] != "Theme" or edge.target_key not in equipment_keys:
                    errors.append(f"invalid theme-equipment edge: {edge.base_identity_key}")
                connected_equipment.add(edge.target_key)
            if edge.relationship_type == "EQUIPMENT_PRODUCED_BY":
                if edge.source_key not in equipment_keys or edge.target_key[0] != "Company":
                    errors.append(f"invalid equipment producer edge: {edge.base_identity_key}")
                connected_equipment.add(edge.source_key)
            if edge.relationship_type == "EQUIPMENT_SUBSTITUTES_FOR":
                if (
                    edge.source_key not in equipment_keys
                    or edge.target_key not in equipment_keys
                    or edge.source_key == edge.target_key
                ):
                    errors.append(f"invalid equipment substitution: {edge.base_identity_key}")
                connected_equipment.update((edge.source_key, edge.target_key))
            if edge.relationship_type == "EQUIPMENT_LIMITED_BY":
                if edge.source_key not in equipment_keys or edge.target_key[0] != "Constraint":
                    errors.append(f"invalid equipment constraint edge: {edge.base_identity_key}")
                connected_equipment.add(edge.source_key)
            if edge.relationship_type == "EQUIPMENT_RESOLVED_BY":
                if edge.source_key not in equipment_keys or edge.target_key[0] != "Company":
                    errors.append(f"invalid equipment resolution edge: {edge.base_identity_key}")
                connected_equipment.add(edge.source_key)
            if edge.relationship_type == "THEME_LIMITED_BY_CONSTRAINT":
                if edge.source_key[0] != "Theme" or edge.target_key not in constraint_keys:
                    errors.append(f"invalid theme constraint edge: {edge.base_identity_key}")
                connected_constraints.add(edge.target_key)
            if edge.relationship_type == "TECHNOLOGY_LIMITED_BY_CONSTRAINT":
                if edge.source_key not in technology_keys or edge.target_key not in constraint_keys:
                    errors.append(f"invalid technology constraint edge: {edge.base_identity_key}")
                connected_technologies.add(edge.source_key)
                connected_constraints.add(edge.target_key)
            if edge.relationship_type == "PROCESS_LIMITED_BY_CONSTRAINT":
                if edge.source_key not in process_keys or edge.target_key not in constraint_keys:
                    errors.append(f"invalid process constraint edge: {edge.base_identity_key}")
                connected_processes.add(edge.source_key)
                connected_constraints.add(edge.target_key)
            if edge.relationship_type == "MATERIAL_LIMITED_BY_CONSTRAINT":
                if edge.source_key not in material_keys or edge.target_key not in constraint_keys:
                    errors.append(f"invalid material constraint edge: {edge.base_identity_key}")
                connected_materials.add(edge.source_key)
                connected_constraints.add(edge.target_key)
            if edge.relationship_type == "EQUIPMENT_LIMITED_BY_CONSTRAINT":
                if edge.source_key not in equipment_keys or edge.target_key not in constraint_keys:
                    errors.append(f"invalid equipment constraint edge: {edge.base_identity_key}")
                connected_equipment.add(edge.source_key)
                connected_constraints.add(edge.target_key)
            if edge.relationship_type == "CONSTRAINT_RESOLVED_BY_COMPANY":
                if edge.source_key not in constraint_keys or edge.target_key[0] != "Company":
                    errors.append(f"invalid constraint resolver edge: {edge.base_identity_key}")
                connected_constraints.add(edge.source_key)
            if edge.relationship_type == "COMPANY_EXPOSED_TO_CONSTRAINT":
                if edge.source_key[0] != "Company" or edge.target_key not in constraint_keys:
                    errors.append(f"invalid company exposure edge: {edge.base_identity_key}")
                connected_constraints.add(edge.target_key)
            dependency_targets = {
                "CONSTRAINT_DEPENDS_ON_MATERIAL": material_keys,
                "CONSTRAINT_DEPENDS_ON_EQUIPMENT": equipment_keys,
                "CONSTRAINT_DEPENDS_ON_PROCESS": process_keys,
            }
            if edge.relationship_type in dependency_targets:
                if (
                    edge.source_key not in constraint_keys
                    or edge.target_key not in dependency_targets[edge.relationship_type]
                ):
                    errors.append(f"invalid constraint dependency edge: {edge.base_identity_key}")
                connected_constraints.add(edge.source_key)
                if edge.relationship_type == "CONSTRAINT_DEPENDS_ON_MATERIAL":
                    connected_materials.add(edge.target_key)
                elif edge.relationship_type == "CONSTRAINT_DEPENDS_ON_EQUIPMENT":
                    connected_equipment.add(edge.target_key)
                else:
                    connected_processes.add(edge.target_key)
            if edge.relationship_type == "CONSTRAINT_RELATED_TO_CONSTRAINT":
                if (
                    edge.source_key not in constraint_keys
                    or edge.target_key not in constraint_keys
                    or edge.source_key == edge.target_key
                ):
                    errors.append(f"invalid constraint relation: {edge.base_identity_key}")
                connected_constraints.update((edge.source_key, edge.target_key))
            if edge.relationship_type in {"LIMITS", "CONTROLS", "RESOLVES"}:
                if edge.source_key in constraint_keys:
                    connected_constraints.add(edge.source_key)
                if edge.target_key in constraint_keys:
                    connected_constraints.add(edge.target_key)
        for role_key in sorted(supply_chain_role_keys - connected_supply_chain_roles):
            errors.append(f"orphan supply-chain node: {role_key}")
        for technology_key in sorted(technology_keys - connected_technologies):
            errors.append(f"orphan technology: {technology_key}")
        for process_key in sorted(process_keys - connected_processes):
            errors.append(f"orphan process: {process_key}")
        for material_key in sorted(material_keys - connected_materials):
            errors.append(f"orphan material: {material_key}")
        for equipment_key in sorted(equipment_keys - connected_equipment):
            errors.append(f"orphan equipment: {equipment_key}")
        for constraint_key in sorted(constraint_keys - connected_constraints):
            errors.append(f"orphan constraint: {constraint_key}")

        links_by_edge: dict[object, int] = {}
        for link in build.edge_evidence:
            if link.edge_key not in set(edge_keys):
                errors.append(f"orphan evidence link edge: {link.edge_key}")
            if link.evidence_key not in evidence_key_set:
                errors.append(f"orphan evidence link evidence: {link.evidence_key}")
            links_by_edge[link.edge_key] = links_by_edge.get(link.edge_key, 0) + 1
        for edge in build.edges:
            if not links_by_edge.get(edge.base_identity_key):
                errors.append(f"missing evidence for edge: {edge.base_identity_key}")

        if errors:
            raise GraphValidationError(errors)
