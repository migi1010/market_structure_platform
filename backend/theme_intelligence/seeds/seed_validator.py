from __future__ import annotations

import re
from typing import Iterable

from theme_intelligence.beneficiaries.beneficiary_models import BENEFICIARY_TYPES
from theme_intelligence.bottlenecks.bottleneck_models import BOTTLENECK_TYPES
from theme_intelligence.catalysts.catalyst_models import CATALYST_TYPES, TIMELINE_STATUSES
from theme_intelligence.models import LIFECYCLE_STAGES
from theme_intelligence.industrial_graph.technology_process_taxonomy import (
    PROCESS_DEPENDENCY_RELATIONSHIPS,
    TECHNOLOGY_PROCESS_RELATIONSHIPS,
    validate_process,
    validate_technology,
)
from theme_intelligence.industrial_graph.material_taxonomy import (
    PROCESS_MATERIAL_RELATIONSHIPS,
    material_key,
    validate_material_category,
)
from theme_intelligence.industrial_graph.equipment_taxonomy import (
    PROCESS_EQUIPMENT_RELATIONSHIPS,
    equipment_key,
    validate_equipment_category,
)
from theme_intelligence.industrial_graph.constraint_taxonomy import (
    constraint_key,
    persisted_constraint_name,
    validate_constraint_category,
)

from .theme_seed_models import SeedBeneficiary, ThemeSeed


FORBIDDEN_SEED_FIELDS = {
    "ai_score",
    "final_ai_score",
    "discovery_score",
    "ai_potential_score",
    "risk_adjusted_score",
    "portfolio_weight",
    "weight",
}


def compact_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def contains_mojibake(value: str) -> bool:
    if "\ufffd" in value or "嚙" in value:
        return True
    if "??" in value or value.count("?") >= 2:
        return True
    if re.search(r"[\u0080-\u009f]", value):
        return True
    return False


def validate_theme_seeds(themes: Iterable[ThemeSeed]) -> list[str]:
    themes = tuple(themes)
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for theme in themes:
        prefix = theme.theme_id or theme.name or "<missing theme>"
        if not theme.theme_id:
            errors.append(f"{prefix}: missing theme_id")
        if not theme.name:
            errors.append(f"{prefix}: missing name")
        if not theme.name_zh:
            errors.append(f"{prefix}: missing name_zh")
        if theme.name_zh and contains_mojibake(theme.name_zh):
            errors.append(f"{prefix}: name_zh contains mojibake")
        if theme.theme_id in seen_ids:
            errors.append(f"{prefix}: duplicate theme_id")
        seen_ids.add(theme.theme_id)
        normalized_name = compact_token(theme.name)
        if normalized_name in seen_names:
            errors.append(f"{prefix}: duplicate name")
        seen_names.add(normalized_name)
        errors.extend(_validate_aliases(theme))
        errors.extend(_validate_roles(theme))
        errors.extend(_validate_supply_chain_connections(theme))
        errors.extend(_validate_technology_process(theme))
        errors.extend(_validate_materials(theme))
        errors.extend(_validate_catalysts(theme))
        errors.extend(_validate_bottlenecks(theme))
        errors.extend(_validate_beneficiaries(theme))
        errors.extend(_validate_lifecycle(theme))
        errors.extend(_validate_display_fields(theme))
        errors.extend(_validate_forbidden_fields(theme.metadata, prefix))
    errors.extend(_validate_equipment(themes))
    errors.extend(_validate_constraints(themes))
    return errors


def _seed_company_names(themes: Iterable[ThemeSeed]) -> tuple[dict[str, str], list[str]]:
    names: dict[str, str] = {}
    errors: list[str] = []
    for theme in themes:
        rows = [
            *(row for group in theme.supply_chain_roles.values() for row in group),
            *theme.seed_beneficiaries,
            *theme.controllers,
            *theme.resolution_enablers,
        ]
        for row in rows:
            ticker = row.ticker.upper()
            prior = names.get(ticker)
            if prior is not None and prior != row.company_name:
                errors.append(
                    f"conflicting company identity {ticker}: {prior} != {row.company_name}"
                )
            names[ticker] = row.company_name
        for link in (*theme.equipment_producer_links, *theme.equipment_resolution_links):
            ticker = link.ticker.upper()
            if not ticker:
                continue
            prior = names.get(ticker)
            if prior is not None and prior != link.company_name:
                errors.append(
                    f"conflicting company identity {ticker}: {prior} != {link.company_name}"
                )
            names[ticker] = link.company_name
    return names, errors


def _validate_constraints(themes: Iterable[ThemeSeed]) -> list[str]:
    themes = tuple(themes)
    errors: list[str] = []
    company_names, company_errors = _seed_company_names(themes)
    errors.extend(company_errors)
    seen_global_identities: dict[str, str] = {}

    for theme in themes:
        constraint_keys: set[str] = set()
        constraint_names: set[str] = set()
        canonical_keys: set[str] = set()
        persisted_by_name = {
            row.name: constraint_key(persisted_constraint_name(theme.name, row.name))
            for row in theme.seed_bottlenecks
            if row.bottleneck_type in {
                "Yield Constraint",
                "Capacity Constraint",
                "Material Constraint",
                "Equipment Constraint",
                "Regulatory Constraint",
                "Infrastructure Constraint",
                "Supply Chain Constraint",
            }
        }
        unsupported_persisted_names = {
            row.name
            for row in theme.seed_bottlenecks
            if row.bottleneck_type not in {
                "Yield Constraint",
                "Capacity Constraint",
                "Material Constraint",
                "Equipment Constraint",
                "Regulatory Constraint",
                "Infrastructure Constraint",
                "Supply Chain Constraint",
            }
        }

        for row in theme.constraints:
            canonical = constraint_key(row.name)
            if row.key in constraint_keys or canonical in canonical_keys:
                errors.append(
                    f"{theme.theme_id}: duplicate constraint identity {row.key}"
                )
            prior_name = seen_global_identities.get(canonical)
            if prior_name is not None and prior_name != row.name:
                errors.append(
                    f"conflicting constraint identity {canonical}: "
                    f"{prior_name} != {row.name}"
                )
            seen_global_identities[canonical] = row.name
            constraint_keys.add(row.key)
            constraint_names.add(row.name)
            canonical_keys.add(canonical)
            try:
                validate_constraint_category(row.category)
            except ValueError:
                errors.append(
                    f"{theme.theme_id}: unknown constraint category {row.category}"
                )
            if not row.citation.strip():
                errors.append(
                    f"{theme.theme_id}: constraint missing citation {row.key}"
                )

        process_keys = {row.key for row in theme.processes}
        technology_keys = {row.key for row in theme.technologies}
        material_keys = {row.key for row in theme.materials}
        equipment_keys = {row.key for row in theme.equipment}
        seen_edges: set[tuple[str, str, str]] = set()

        def known_constraint(key: str, name: str = "") -> bool:
            if key:
                return key in constraint_keys
            return name in constraint_names or name in persisted_by_name

        def require_constraint(key: str, name: str, context: str) -> None:
            if not known_constraint(key, name):
                errors.append(
                    f"{theme.theme_id}: unknown constraint endpoint {context}:"
                    f"{key or name}"
                )

        def require_citation(citation: str, context: str) -> None:
            if not citation.strip():
                errors.append(
                    f"{theme.theme_id}: constraint relationship missing citation {context}"
                )

        def register_edge(source: str, relationship: str, target: str) -> None:
            edge = (source, relationship, target)
            if edge in seen_edges:
                errors.append(f"{theme.theme_id}: duplicate constraint edge {edge}")
            seen_edges.add(edge)

        def register_company(ticker: str, company_name: str, context: str) -> str:
            canonical_ticker = ticker.upper()
            if not canonical_ticker:
                errors.append(f"{theme.theme_id}: constraint {context} missing ticker")
                return canonical_ticker
            if not company_name.strip():
                errors.append(
                    f"{theme.theme_id}: constraint {context} missing company name"
                )
                return canonical_ticker
            prior = company_names.get(canonical_ticker)
            if prior is not None and prior != company_name:
                errors.append(
                    f"conflicting company identity {canonical_ticker}: "
                    f"{prior} != {company_name}"
                )
            company_names[canonical_ticker] = company_name
            return canonical_ticker

        for link in theme.theme_constraint_links:
            require_constraint(link.constraint_key, "", "theme")
            if link.relationship_type != "THEME_LIMITED_BY_CONSTRAINT":
                errors.append(
                    f"{theme.theme_id}: invalid theme-constraint relationship "
                    f"{link.relationship_type}"
                )
            require_citation(link.citation, f"theme:{link.constraint_key}")
            register_edge(theme.theme_id, link.relationship_type, link.constraint_key)

        for link in theme.technology_constraint_links:
            require_constraint(link.constraint_key, "", link.technology_key)
            if link.technology_key not in technology_keys:
                errors.append(
                    f"{theme.theme_id}: unknown technology constraint endpoint "
                    f"{link.technology_key}"
                )
            if link.relationship_type != "TECHNOLOGY_LIMITED_BY_CONSTRAINT":
                errors.append(
                    f"{theme.theme_id}: invalid technology-constraint relationship "
                    f"{link.relationship_type}"
                )
            require_citation(
                link.citation,
                f"{link.technology_key}:{link.constraint_key}",
            )
            register_edge(
                link.technology_key,
                link.relationship_type,
                link.constraint_key,
            )

        for process in theme.processes:
            for link in process.constraint_links:
                if (
                    not link.constraint_key
                    and link.constraint_name in unsupported_persisted_names
                ):
                    continue
                require_constraint(link.constraint_key, link.constraint_name, process.key)
                require_citation(
                    link.citation,
                    f"{process.key}:{link.constraint_key or link.constraint_name}",
                )
                if link.relationship_type != "PROCESS_LIMITED_BY_CONSTRAINT":
                    errors.append(
                        f"{theme.theme_id}: invalid process-constraint relationship "
                        f"{link.relationship_type}"
                    )

        for link in theme.material_constraint_links:
            require_constraint(link.constraint_key, link.constraint_name, link.material_key)
            if link.material_key not in material_keys:
                errors.append(
                    f"{theme.theme_id}: unknown material constraint endpoint "
                    f"{link.material_key}"
                )
            require_citation(link.citation, f"{link.material_key}:constraint")

        for link in theme.equipment_constraint_links:
            require_constraint(link.constraint_key, link.constraint_name, link.equipment_key)
            if link.equipment_key not in equipment_keys:
                errors.append(
                    f"{theme.theme_id}: unknown equipment constraint endpoint "
                    f"{link.equipment_key}"
                )
            require_citation(link.citation, f"{link.equipment_key}:constraint")

        for link in theme.constraint_resolver_links:
            require_constraint(link.constraint_key, "", "resolver")
            ticker = register_company(link.ticker, link.company_name, "resolver")
            require_citation(link.citation, f"{link.constraint_key}:resolver:{ticker}")
            register_edge(link.constraint_key, "CONSTRAINT_RESOLVED_BY_COMPANY", ticker)

        for link in theme.company_constraint_exposure_links:
            require_constraint(link.constraint_key, "", "exposure")
            ticker = register_company(link.ticker, link.company_name, "exposure")
            require_citation(link.citation, f"{ticker}:exposure:{link.constraint_key}")
            register_edge(ticker, "COMPANY_EXPOSED_TO_CONSTRAINT", link.constraint_key)

        dependency_relationships = {
            "Material": "CONSTRAINT_DEPENDS_ON_MATERIAL",
            "Equipment": "CONSTRAINT_DEPENDS_ON_EQUIPMENT",
            "Process": "CONSTRAINT_DEPENDS_ON_PROCESS",
        }
        target_sets = {
            "Material": material_keys,
            "Equipment": equipment_keys,
            "Process": process_keys,
        }
        for link in theme.constraint_dependencies:
            require_constraint(link.constraint_key, "", "dependency")
            expected = dependency_relationships.get(link.target_type)
            if expected is None or link.relationship_type != expected:
                errors.append(
                    f"{theme.theme_id}: invalid constraint dependency "
                    f"{link.relationship_type}"
                )
            if link.target_key not in target_sets.get(link.target_type, set()):
                errors.append(
                    f"{theme.theme_id}: invalid constraint dependency endpoint "
                    f"{link.target_type}:{link.target_key}"
                )
            require_citation(
                link.citation,
                f"{link.constraint_key}:{link.target_type}:{link.target_key}",
            )
            register_edge(
                link.constraint_key,
                link.relationship_type,
                link.target_key,
            )

        for link in theme.constraint_relations:
            require_constraint(link.source_constraint_key, "", "relation")
            require_constraint(link.target_constraint_key, "", "relation")
            if link.source_constraint_key == link.target_constraint_key:
                errors.append(f"{theme.theme_id}: constraint relation self-link")
            require_citation(
                link.citation,
                f"{link.source_constraint_key}:related:{link.target_constraint_key}",
            )
            register_edge(
                link.source_constraint_key,
                "CONSTRAINT_RELATED_TO_CONSTRAINT",
                link.target_constraint_key,
            )

    return errors


def _validate_equipment(themes: Iterable[ThemeSeed]) -> list[str]:
    themes = tuple(themes)
    errors: list[str] = []
    company_names, company_errors = _seed_company_names(themes)
    errors.extend(company_errors)

    for theme in themes:
        equipment_keys: set[str] = set()
        equipment_identities: set[str] = set()
        process_keys = {row.key for row in theme.processes}
        constraint_names = {
            *(row.name for row in theme.seed_bottlenecks),
            *(row.name for row in theme.constraints),
        }
        constraint_keys = {row.key for row in theme.constraints}
        seen_edges: set[tuple[str, str, str]] = set()

        for row in theme.equipment:
            identity = equipment_key(row.name)
            if row.key in equipment_keys or identity in equipment_identities:
                errors.append(
                    f"{theme.theme_id}: duplicate equipment identity {row.key}"
                )
            equipment_keys.add(row.key)
            equipment_identities.add(identity)
            try:
                validate_equipment_category(row.category)
            except ValueError:
                errors.append(
                    f"{theme.theme_id}: unknown equipment category {row.category}"
                )
            if not row.citation.strip():
                errors.append(f"{theme.theme_id}: equipment missing citation {row.key}")

        def require_equipment(key: str, context: str) -> None:
            if key not in equipment_keys:
                errors.append(
                    f"{theme.theme_id}: unknown equipment endpoint {context}:{key}"
                )

        def require_citation(citation: str, context: str) -> None:
            if not citation.strip():
                errors.append(
                    f"{theme.theme_id}: equipment relationship missing citation {context}"
                )

        def register_edge(source: str, relationship: str, target: str) -> None:
            edge = (source, relationship, target)
            if edge in seen_edges:
                errors.append(f"{theme.theme_id}: duplicate equipment edge {edge}")
            seen_edges.add(edge)

        def register_company(ticker: str, company_name: str, context: str) -> str:
            canonical_ticker = ticker.upper()
            if not canonical_ticker:
                errors.append(
                    f"{theme.theme_id}: equipment {context} missing ticker"
                )
                return canonical_ticker
            if not company_name.strip():
                errors.append(
                    f"{theme.theme_id}: equipment {context} missing company name"
                )
                return canonical_ticker
            prior = company_names.get(canonical_ticker)
            if prior is not None and prior != company_name:
                errors.append(
                    f"conflicting company identity {canonical_ticker}: "
                    f"{prior} != {company_name}"
                )
            company_names[canonical_ticker] = company_name
            return canonical_ticker

        for link in theme.process_equipment_links:
            require_equipment(link.equipment_key, link.process_key)
            if link.process_key not in process_keys:
                errors.append(
                    f"{theme.theme_id}: unknown process equipment endpoint "
                    f"{link.process_key}"
                )
            if link.relationship_type not in PROCESS_EQUIPMENT_RELATIONSHIPS:
                errors.append(
                    f"{theme.theme_id}: invalid process-equipment relationship "
                    f"{link.relationship_type}"
                )
            require_citation(
                link.citation,
                f"{link.process_key}:{link.relationship_type}:{link.equipment_key}",
            )
            if link.relationship_type == "PROCESS_REQUIRES_EQUIPMENT":
                register_edge(
                    link.process_key,
                    link.relationship_type,
                    link.equipment_key,
                )
            else:
                register_edge(
                    link.equipment_key,
                    link.relationship_type,
                    link.process_key,
                )

        for link in theme.theme_equipment_links:
            require_equipment(link.equipment_key, "theme")
            if link.relationship_type != "THEME_DEPENDS_ON_EQUIPMENT":
                errors.append(
                    f"{theme.theme_id}: invalid theme-equipment relationship "
                    f"{link.relationship_type}"
                )
            require_citation(link.citation, f"theme:{link.equipment_key}")
            register_edge(theme.theme_id, link.relationship_type, link.equipment_key)

        for link in theme.equipment_producer_links:
            require_equipment(link.equipment_key, "producer")
            ticker = register_company(link.ticker, link.company_name, "producer")
            require_citation(link.citation, f"{link.equipment_key}:producer:{ticker}")
            register_edge(link.equipment_key, "EQUIPMENT_PRODUCED_BY", ticker)

        for link in theme.equipment_substitution_links:
            require_equipment(link.source_equipment_key, "substitution")
            require_equipment(link.target_equipment_key, "substitution")
            if link.source_equipment_key == link.target_equipment_key:
                errors.append(f"{theme.theme_id}: equipment substitution self-link")
            require_citation(
                link.citation,
                f"{link.source_equipment_key}:substitutes:{link.target_equipment_key}",
            )
            register_edge(
                link.source_equipment_key,
                "EQUIPMENT_SUBSTITUTES_FOR",
                link.target_equipment_key,
            )

        for link in theme.equipment_constraint_links:
            require_equipment(link.equipment_key, "constraint")
            if (
                link.constraint_key not in constraint_keys
                if link.constraint_key
                else link.constraint_name not in constraint_names
            ):
                errors.append(
                    f"{theme.theme_id}: unknown equipment constraint "
                    f"{link.constraint_name}"
                )
            require_citation(
                link.citation,
                f"{link.equipment_key}:constraint:{link.constraint_name}",
            )
            register_edge(
                link.equipment_key,
                "EQUIPMENT_LIMITED_BY",
                link.constraint_name,
            )

        for link in theme.equipment_resolution_links:
            require_equipment(link.equipment_key, "resolution")
            ticker = register_company(link.ticker, link.company_name, "resolution")
            require_citation(link.citation, f"{link.equipment_key}:resolution:{ticker}")
            register_edge(link.equipment_key, "EQUIPMENT_RESOLVED_BY", ticker)

    return errors


def _validate_aliases(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for alias in theme.aliases:
        if not alias.strip():
            errors.append(f"{theme.theme_id}: empty alias")
            continue
        compact = compact_token(alias)
        if compact in seen:
            errors.append(f"{theme.theme_id}: duplicate alias {alias}")
        seen.add(compact)
    return errors


def _validate_roles(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    for role, rows in theme.supply_chain_roles.items():
        if not role.strip():
            errors.append(f"{theme.theme_id}: empty supply-chain role")
        seen: set[str] = set()
        for row in rows:
            ticker = row.ticker.upper()
            if ticker in seen:
                errors.append(f"{theme.theme_id}: duplicate ticker {ticker} in role {role}")
            seen.add(ticker)
            errors.extend(_validate_seed_beneficiary(theme.theme_id, row))
    return errors


def _validate_supply_chain_connections(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    supported = {"SUPPLIES", "CUSTOMER_OF", "DEPENDS_ON", "USES_SUPPLIER"}
    known_tickers = {
        row.ticker.upper()
        for rows in theme.supply_chain_roles.values()
        for row in rows
    }
    seen: set[tuple[str, str, str]] = set()
    for row in theme.supply_chain_connections:
        key = (
            row.source_ticker.upper(),
            row.relationship_type,
            row.target_ticker.upper(),
        )
        if key in seen:
            errors.append(f"{theme.theme_id}: duplicate supply-chain connection {key}")
        seen.add(key)
        if row.relationship_type not in supported:
            errors.append(
                f"{theme.theme_id}: invalid supply-chain relationship {row.relationship_type}"
            )
        if key[0] not in known_tickers or key[2] not in known_tickers:
            errors.append(f"{theme.theme_id}: unknown supply-chain connection endpoint {key}")
        if not row.citation.strip():
            errors.append(f"{theme.theme_id}: supply-chain connection missing evidence {key}")
    return errors


def _validate_technology_process(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    technology_keys: set[str] = set()
    process_keys: set[str] = set()
    constraint_names = {
        *(row.name for row in theme.seed_bottlenecks),
        *(row.name for row in theme.constraints),
    }
    constraint_keys = {row.key for row in theme.constraints}
    company_tickers = {
        row.ticker.upper()
        for rows in theme.supply_chain_roles.values()
        for row in rows
    }
    company_tickers.update(
        row.ticker.upper()
        for row in (
            *theme.seed_beneficiaries,
            *theme.controllers,
            *theme.resolution_enablers,
        )
    )

    for row in theme.technologies:
        if row.key in technology_keys:
            errors.append(f"{theme.theme_id}: duplicate technology {row.key}")
        technology_keys.add(row.key)
        try:
            validate_technology(row.name)
        except ValueError:
            errors.append(f"{theme.theme_id}: unknown technology {row.name}")
        if not row.citation.strip():
            errors.append(f"{theme.theme_id}: technology missing citation {row.key}")

    for row in theme.processes:
        if row.key in process_keys:
            errors.append(f"{theme.theme_id}: duplicate process {row.key}")
        process_keys.add(row.key)
        try:
            validate_process(row.name)
        except ValueError:
            errors.append(f"{theme.theme_id}: unknown process {row.name}")
        if not row.citation.strip():
            errors.append(f"{theme.theme_id}: process missing citation {row.key}")
        for link in row.constraint_links:
            if not link.citation.strip():
                errors.append(
                    f"{theme.theme_id}: process constraint missing citation {row.key}:{link.constraint_name}"
                )
            if (
                link.constraint_key not in constraint_keys
                if link.constraint_key
                else link.constraint_name not in constraint_names
            ):
                errors.append(
                    f"{theme.theme_id}: unknown constraint {row.key}:{link.constraint_name}"
                )
        for link in row.resolution_links:
            ticker = link.ticker.upper()
            if not link.citation.strip():
                errors.append(
                    f"{theme.theme_id}: process resolution missing citation {row.key}:{ticker}"
                )
            if ticker not in company_tickers:
                errors.append(f"{theme.theme_id}: unknown ticker {row.key}:{ticker}")

    for link in theme.technology_process_links:
        if link.technology_key not in technology_keys:
            errors.append(
                f"{theme.theme_id}: unknown technology link endpoint {link.technology_key}"
            )
        if link.process_key not in process_keys:
            errors.append(f"{theme.theme_id}: unknown process link endpoint {link.process_key}")
        if link.relationship_type not in TECHNOLOGY_PROCESS_RELATIONSHIPS:
            errors.append(
                f"{theme.theme_id}: invalid technology-process relationship {link.relationship_type}"
            )
        if not link.citation.strip():
            errors.append(
                f"{theme.theme_id}: technology-process link missing citation "
                f"{link.technology_key}:{link.process_key}"
            )

    for link in theme.process_dependencies:
        if link.source_process_key not in process_keys or link.target_process_key not in process_keys:
            errors.append(
                f"{theme.theme_id}: unknown process dependency endpoint "
                f"{link.source_process_key}:{link.target_process_key}"
            )
        if link.source_process_key == link.target_process_key:
            errors.append(f"{theme.theme_id}: invalid process dependency self-link")
        if link.relationship_type not in PROCESS_DEPENDENCY_RELATIONSHIPS:
            errors.append(
                f"{theme.theme_id}: invalid process dependency {link.relationship_type}"
            )
        if not link.citation.strip():
            errors.append(
                f"{theme.theme_id}: process dependency missing citation "
                f"{link.source_process_key}:{link.target_process_key}"
            )
    return errors


def _validate_materials(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    material_keys: set[str] = set()
    material_identities: set[str] = set()
    process_keys = {row.key for row in theme.processes}
    constraint_names = {
        *(row.name for row in theme.seed_bottlenecks),
        *(row.name for row in theme.constraints),
    }
    constraint_keys = {row.key for row in theme.constraints}
    company_tickers = {
        row.ticker.upper()
        for rows in theme.supply_chain_roles.values()
        for row in rows
    }
    company_tickers.update(
        row.ticker.upper()
        for row in (
            *theme.seed_beneficiaries,
            *theme.controllers,
            *theme.resolution_enablers,
        )
    )

    for row in theme.materials:
        identity = material_key(row.name)
        if row.key in material_keys or identity in material_identities:
            errors.append(f"{theme.theme_id}: duplicate material identity {row.key}")
        material_keys.add(row.key)
        material_identities.add(identity)
        try:
            validate_material_category(row.category)
        except ValueError:
            errors.append(f"{theme.theme_id}: unknown material category {row.category}")
        if not row.citation.strip():
            errors.append(f"{theme.theme_id}: material missing citation {row.key}")

    seen_edges: set[tuple[str, str, str]] = set()

    def require_material(key: str, context: str) -> None:
        if key not in material_keys:
            errors.append(f"{theme.theme_id}: unknown material endpoint {context}:{key}")

    def require_citation(citation: str, context: str) -> None:
        if not citation.strip():
            errors.append(f"{theme.theme_id}: material relationship missing citation {context}")

    def register_edge(source: str, relationship: str, target: str) -> None:
        edge = (source, relationship, target)
        if edge in seen_edges:
            errors.append(f"{theme.theme_id}: duplicate material edge {edge}")
        seen_edges.add(edge)

    for link in theme.process_material_links:
        require_material(link.material_key, link.process_key)
        if link.process_key not in process_keys:
            errors.append(
                f"{theme.theme_id}: unknown process material endpoint {link.process_key}"
            )
        if link.relationship_type not in PROCESS_MATERIAL_RELATIONSHIPS:
            errors.append(
                f"{theme.theme_id}: invalid process-material relationship "
                f"{link.relationship_type}"
            )
        require_citation(
            link.citation,
            f"{link.process_key}:{link.relationship_type}:{link.material_key}",
        )
        if link.relationship_type == "PROCESS_REQUIRES_MATERIAL":
            register_edge(link.process_key, link.relationship_type, link.material_key)
        else:
            register_edge(link.material_key, link.relationship_type, link.process_key)

    for link in theme.theme_material_links:
        require_material(link.material_key, "theme")
        if link.relationship_type != "THEME_DEPENDS_ON_MATERIAL":
            errors.append(
                f"{theme.theme_id}: invalid theme-material relationship "
                f"{link.relationship_type}"
            )
        require_citation(link.citation, f"theme:{link.material_key}")
        register_edge(theme.theme_id, link.relationship_type, link.material_key)

    for link in theme.material_supplier_links:
        require_material(link.material_key, "supplier")
        ticker = link.ticker.upper()
        if ticker not in company_tickers:
            errors.append(
                f"{theme.theme_id}: unknown material supplier ticker {ticker}"
            )
        require_citation(link.citation, f"{link.material_key}:supplier:{ticker}")
        register_edge(link.material_key, "MATERIAL_SUPPLIED_BY", ticker)

    for link in theme.material_substitution_links:
        require_material(link.source_material_key, "substitution")
        require_material(link.target_material_key, "substitution")
        if link.source_material_key == link.target_material_key:
            errors.append(f"{theme.theme_id}: material substitution self-link")
        require_citation(
            link.citation,
            f"{link.source_material_key}:substitutes:{link.target_material_key}",
        )
        register_edge(
            link.source_material_key,
            "MATERIAL_SUBSTITUTES_FOR",
            link.target_material_key,
        )

    for link in theme.material_constraint_links:
        require_material(link.material_key, "constraint")
        if (
            link.constraint_key not in constraint_keys
            if link.constraint_key
            else link.constraint_name not in constraint_names
        ):
            errors.append(
                f"{theme.theme_id}: unknown material constraint {link.constraint_name}"
            )
        require_citation(
            link.citation,
            f"{link.material_key}:constraint:{link.constraint_name}",
        )
        register_edge(link.material_key, "MATERIAL_LIMITED_BY", link.constraint_name)

    for link in theme.material_resolution_links:
        require_material(link.material_key, "resolution")
        ticker = link.ticker.upper()
        if ticker not in company_tickers:
            errors.append(
                f"{theme.theme_id}: unknown material resolution ticker {ticker}"
            )
        require_citation(link.citation, f"{link.material_key}:resolution:{ticker}")
        register_edge(link.material_key, "MATERIAL_RESOLVED_BY", ticker)

    return errors


def _validate_catalysts(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    for catalyst in theme.seed_catalysts:
        if not catalyst.name.strip() or not catalyst.description.strip():
            errors.append(f"{theme.theme_id}: empty catalyst display field")
        if catalyst.catalyst_type not in CATALYST_TYPES:
            errors.append(f"{theme.theme_id}: invalid catalyst type {catalyst.catalyst_type}")
        if catalyst.timeline_status not in TIMELINE_STATUSES:
            errors.append(f"{theme.theme_id}: invalid catalyst timeline {catalyst.timeline_status}")
        if contains_mojibake(catalyst.name) or contains_mojibake(catalyst.description):
            errors.append(f"{theme.theme_id}: catalyst contains mojibake")
    return errors


def _validate_bottlenecks(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    for bottleneck in theme.seed_bottlenecks:
        if not bottleneck.name.strip() or not bottleneck.description.strip():
            errors.append(f"{theme.theme_id}: empty bottleneck display field")
        if bottleneck.bottleneck_type not in BOTTLENECK_TYPES:
            errors.append(f"{theme.theme_id}: invalid bottleneck type {bottleneck.bottleneck_type}")
        if contains_mojibake(bottleneck.name) or contains_mojibake(bottleneck.description):
            errors.append(f"{theme.theme_id}: bottleneck contains mojibake")
    return errors


def _validate_beneficiaries(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    controller_rationales = {row.ticker.upper(): row.dual_role_rationale.strip() for row in theme.controllers}
    for row in [*theme.seed_beneficiaries, *theme.controllers, *theme.resolution_enablers]:
        errors.extend(_validate_seed_beneficiary(theme.theme_id, row))
        if (
            row.ticker.upper() in controller_rationales
            and row.beneficiary_type == "Direct Beneficiary"
            and not (row.dual_role_rationale.strip() or controller_rationales[row.ticker.upper()])
        ):
            errors.append(f"{theme.theme_id}: controller also listed as direct beneficiary without dual-role rationale {row.ticker.upper()}")
    return errors


def _validate_seed_beneficiary(theme_id: str, row: SeedBeneficiary) -> list[str]:
    errors: list[str] = []
    if not row.ticker.strip() or not row.company_name.strip():
        errors.append(f"{theme_id}: beneficiary missing ticker or company")
    if not row.role.strip():
        errors.append(f"{theme_id}: beneficiary missing role")
    if row.beneficiary_type not in BENEFICIARY_TYPES:
        errors.append(f"{theme_id}: invalid beneficiary type {row.beneficiary_type}")
    if contains_mojibake(row.company_name) or contains_mojibake(row.role):
        errors.append(f"{theme_id}: beneficiary contains mojibake")
    return errors


def _validate_lifecycle(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    if theme.lifecycle_hint.stage not in LIFECYCLE_STAGES:
        errors.append(f"{theme.theme_id}: unsupported lifecycle stage {theme.lifecycle_hint.stage}")
    if theme.lifecycle_hint.expected_next_stage not in LIFECYCLE_STAGES:
        errors.append(f"{theme.theme_id}: unsupported expected next stage {theme.lifecycle_hint.expected_next_stage}")
    if not theme.lifecycle_hint.rationale.strip():
        errors.append(f"{theme.theme_id}: empty lifecycle rationale")
    return errors


def _validate_display_fields(theme: ThemeSeed) -> list[str]:
    errors: list[str] = []
    if any(not note.strip() for note in theme.risk_notes):
        errors.append(f"{theme.theme_id}: empty risk note")
    for value in [theme.name, theme.name_zh, *theme.aliases, *theme.risk_notes]:
        if contains_mojibake(value):
            errors.append(f"{theme.theme_id}: display field contains mojibake")
            break
    return errors


def _validate_forbidden_fields(metadata: dict[str, object], prefix: str) -> list[str]:
    errors: list[str] = []
    for key in metadata:
        if key in FORBIDDEN_SEED_FIELDS:
            errors.append(f"{prefix}: forbidden seed field {key}")
    return errors
