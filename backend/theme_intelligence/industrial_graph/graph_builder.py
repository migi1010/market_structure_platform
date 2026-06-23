from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from theme_intelligence.discovery.discovery_models import theme_id
from theme_intelligence.industrial_graph.graph_models import (
    IndustrialGraphBuild,
    IndustrialGraphEdge,
    IndustrialGraphEdgeEvidence,
    IndustrialGraphEvidence,
    IndustrialGraphNode,
    content_hash,
)
from theme_intelligence.industrial_graph.supply_chain_taxonomy import (
    canonical_supply_chain_role,
    supply_chain_role_key,
)
from theme_intelligence.industrial_graph.technology_process_taxonomy import (
    process_key,
    technology_key,
)
from theme_intelligence.industrial_graph.material_taxonomy import material_key
from theme_intelligence.industrial_graph.equipment_taxonomy import equipment_key
from theme_intelligence.industrial_graph.constraint_taxonomy import (
    CONSTRAINT_CATEGORIES,
    constraint_key,
    persisted_constraint_name,
)
from theme_intelligence.industrial_graph.graph_validator import GraphValidator
from theme_intelligence.seeds.theme_seed_data import TARGET_SEED_THEMES
from theme_intelligence.seeds.theme_seed_models import ThemeSeed
from theme_intelligence.storage.theme_repository import ThemeRepository


def _theme_key(value: str) -> str:
    return "_".join(part for part in theme_id(value).split("_") if part)


def _record_id(*parts: object) -> str:
    return ":".join(_theme_key(str(part)) for part in parts if str(part or "").strip())


def _constraint_nodes(seed: ThemeSeed) -> dict[str, IndustrialGraphNode]:
    result: dict[str, IndustrialGraphNode] = {}
    for row in seed.seed_bottlenecks:
        if row.bottleneck_type not in CONSTRAINT_CATEGORIES:
            continue
        display_name = persisted_constraint_name(seed.name, row.name)
        node = IndustrialGraphNode(
            "Constraint",
            constraint_key(display_name),
            display_name,
            aliases=(row.name,),
            external_ids={"category": row.bottleneck_type},
        )
        result[row.name] = node
    for row in seed.constraints:
        node = IndustrialGraphNode(
            "Constraint",
            constraint_key(row.name),
            row.name,
            aliases=row.aliases,
            external_ids={"category": row.category},
        )
        result[row.key] = node
        result[row.name] = node
    return result


class IndustrialGraphBuilder:
    def __init__(
        self,
        repository: ThemeRepository | None = None,
        themes: Iterable[ThemeSeed] = TARGET_SEED_THEMES,
    ) -> None:
        self.repository = repository or ThemeRepository()
        self.themes = tuple(themes)

    def build(self) -> IndustrialGraphBuild:
        self.repository.initialize()
        GraphValidator().validate_supply_chain_roles(self.themes)
        GraphValidator().validate_technology_process_seeds(self.themes)
        GraphValidator().validate_material_seeds(self.themes)
        GraphValidator().validate_equipment_seeds(self.themes)
        GraphValidator().validate_constraint_seeds(self.themes)
        nodes: dict[tuple[str, str], IndustrialGraphNode] = {}
        evidence: dict[tuple[str, str, str], IndustrialGraphEvidence] = {}
        edges: dict[object, IndustrialGraphEdge] = {}
        links: dict[object, IndustrialGraphEdgeEvidence] = {}

        def add_node(node: IndustrialGraphNode) -> None:
            nodes[node.identity_key] = node

        def add_evidence(row: IndustrialGraphEvidence) -> IndustrialGraphEvidence:
            evidence[row.identity_key] = row
            return row

        def add_edge(edge: IndustrialGraphEdge, row: IndustrialGraphEvidence) -> None:
            prior = edges.get(edge.base_identity_key)
            if prior is None or (
                edge.confidence_score,
                edge.dependency_strength,
            ) > (
                prior.confidence_score,
                prior.dependency_strength,
            ):
                edges[edge.base_identity_key] = edge
            link = IndustrialGraphEdgeEvidence(edge.base_identity_key, row.identity_key)
            links[link.sort_key] = link

        seed_by_name = {_theme_key(seed.name): seed for seed in self.themes}
        for seed in self.themes:
            add_node(IndustrialGraphNode("Theme", seed.theme_id, seed.name, aliases=seed.aliases))

        entities = self.repository.get_entities()
        beneficiaries = self.repository.get_beneficiaries()
        beneficiary_scores = self.repository.get_beneficiary_scores()
        catalysts = self.repository.get_catalysts()
        bottlenecks = self.repository.get_bottlenecks()

        for entity in entities:
            theme_key = _theme_key(str(entity.theme_name))
            add_node(IndustrialGraphNode("Theme", theme_key, str(entity.theme_name)))
            ticker = str(entity.ticker or "").upper()
            if ticker:
                add_node(
                    IndustrialGraphNode(
                        "Company",
                        ticker,
                        str(entity.company or ticker),
                        external_ids={"ticker": ticker},
                    )
                )
            role = str(entity.entity_type or "")
            payload = {
                "theme": entity.theme_name,
                "entity_type": role,
                "company": entity.company,
                "ticker": ticker,
                "relationship_strength": entity.relationship_strength,
                "updated_at": entity.updated_at,
            }
            add_evidence(
                IndustrialGraphEvidence.from_payload(
                    "phase10:theme_entity",
                    _record_id(entity.theme_name, role, ticker),
                    f"Persisted Phase 10 theme entity: {entity.company} as {role} for {entity.theme_name}.",
                    payload,
                    observed_date=str(entity.updated_at),
                )
            )
        for beneficiary in beneficiaries:
            ticker = str(beneficiary.ticker or "").upper()
            add_node(IndustrialGraphNode("Theme", _theme_key(beneficiary.theme_name), beneficiary.theme_name))
            if ticker:
                add_node(
                    IndustrialGraphNode(
                        "Company",
                        ticker,
                        beneficiary.company_name or ticker,
                        external_ids={"ticker": ticker},
                    )
                )
            add_evidence(
                IndustrialGraphEvidence.from_payload(
                    "phase10:beneficiary",
                    _record_id(beneficiary.theme_name, ticker),
                    f"Persisted Phase 10 beneficiary: {beneficiary.company_name} for {beneficiary.theme_name}.",
                    vars(beneficiary),
                    observed_date=str(beneficiary.updated_at),
                )
            )

        for bottleneck in bottlenecks:
            category = str(bottleneck.bottleneck_type or "")
            if category not in CONSTRAINT_CATEGORIES:
                continue
            theme_key = _theme_key(str(bottleneck.theme_name))
            theme_node = IndustrialGraphNode("Theme", theme_key, str(bottleneck.theme_name))
            display_name = persisted_constraint_name(
                str(bottleneck.theme_name),
                str(bottleneck.bottleneck_name),
            )
            constraint_node = IndustrialGraphNode(
                "Constraint",
                constraint_key(display_name),
                display_name,
                aliases=(str(bottleneck.bottleneck_name),),
                external_ids={"category": category},
            )
            add_node(theme_node)
            add_node(constraint_node)
            payload = bottleneck.to_api() if hasattr(bottleneck, "to_api") else vars(bottleneck)
            bottleneck_evidence = add_evidence(
                IndustrialGraphEvidence.from_payload(
                    "phase10:bottleneck",
                    _record_id(bottleneck.theme_name, bottleneck.bottleneck_name, bottleneck.bottleneck_type),
                    str(bottleneck.description or f"Persisted bottleneck for {bottleneck.theme_name}."),
                    payload,
                    observed_date=str(bottleneck.updated_at),
                )
            )
            add_edge(
                IndustrialGraphEdge(
                    theme_node.identity_key,
                    "THEME_LIMITED_BY_CONSTRAINT",
                    constraint_node.identity_key,
                    confidence_score=float(getattr(bottleneck, "severity_score", 0) or 0),
                    dependency_strength=float(getattr(bottleneck, "bottleneck_strength", 0) or 0),
                ),
                bottleneck_evidence,
            )
            for controller in getattr(bottleneck, "controller_entities", []) or []:
                if not isinstance(controller, dict):
                    continue
                ticker = str(controller.get("ticker") or "").upper()
                if not ticker:
                    continue
                company = IndustrialGraphNode(
                    "Company",
                    ticker,
                    str(controller.get("company_name") or controller.get("company") or ticker),
                    external_ids={"ticker": ticker},
                )
                add_node(company)
                controller_evidence = add_evidence(
                    IndustrialGraphEvidence.from_payload(
                        "phase10:bottleneck",
                        _record_id(bottleneck.theme_name, bottleneck.bottleneck_name, "controller", ticker),
                        f"Persisted controller evidence: {company.display_name} controls {constraint_node.display_name}.",
                        {"bottleneck": payload, "controller": controller},
                        observed_date=str(bottleneck.updated_at),
                    )
                )
                add_edge(
                    IndustrialGraphEdge(
                        company.identity_key,
                        "CONTROLS",
                        constraint_node.identity_key,
                        confidence_score=float(controller.get("relationship_strength") or bottleneck.bottleneck_strength or 0),
                        dependency_strength=float(bottleneck.bottleneck_strength or 0),
                    ),
                    controller_evidence,
                )

        for score in beneficiary_scores:
            theme_key = _theme_key(str(score.theme_name))
            ticker = str(score.ticker or "").upper()
            theme_node = IndustrialGraphNode("Theme", theme_key, str(score.theme_name))
            company_node = IndustrialGraphNode(
                "Company",
                ticker,
                str(score.company_name or ticker),
                external_ids={"ticker": ticker},
            )
            add_node(theme_node)
            add_node(company_node)
            payload = {
                "theme_name": score.theme_name,
                "ticker": ticker,
                "company_name": score.company_name,
                "beneficiary_type": score.beneficiary_type,
                "dependency_score": score.dependency_score,
                "beneficiary_score": score.beneficiary_score,
                "allocation_score": score.allocation_score,
                "role": score.role,
                "updated_at": score.updated_at,
            }
            score_evidence = add_evidence(
                IndustrialGraphEvidence.from_payload(
                    "phase10:beneficiary_score",
                    _record_id(score.theme_name, ticker, score.beneficiary_type),
                    f"Persisted Phase 10 classification: {score.company_name} is {score.beneficiary_type} for {score.theme_name}.",
                    payload,
                    observed_date=str(score.updated_at),
                )
            )
            if str(score.beneficiary_type).lower() == "resolution enabler":
                add_edge(
                    IndustrialGraphEdge(
                        company_node.identity_key,
                        "ENABLES",
                        theme_node.identity_key,
                        confidence_score=float(score.beneficiary_score or 0),
                        dependency_strength=float(score.dependency_score or 0),
                    ),
                    score_evidence,
                )

        for catalyst in catalysts:
            add_evidence(
                IndustrialGraphEvidence.from_payload(
                    "phase10:catalyst",
                    _record_id(catalyst.theme_name, catalyst.cluster_key, catalyst.catalyst_type, catalyst.source),
                    str(catalyst.description or f"Persisted catalyst for {catalyst.theme_name}."),
                    catalyst.to_api() if hasattr(catalyst, "to_api") else vars(catalyst),
                    observed_date=str(catalyst.updated_at),
                )
            )

        self._add_supply_chain_seed_records(
            add_node=add_node,
            add_evidence=add_evidence,
            add_edge=add_edge,
        )
        self._add_technology_process_seed_records(
            add_node=add_node,
            add_evidence=add_evidence,
            add_edge=add_edge,
        )
        self._add_material_seed_records(
            add_node=add_node,
            add_evidence=add_evidence,
            add_edge=add_edge,
        )
        self._add_equipment_seed_records(
            add_node=add_node,
            add_evidence=add_evidence,
            add_edge=add_edge,
        )
        self._add_constraint_seed_records(
            add_node=add_node,
            add_evidence=add_evidence,
            add_edge=add_edge,
        )

        watermark = content_hash({
            "nodes": sorted(nodes),
            "evidence": sorted(evidence),
            "seed_themes": sorted(seed_by_name),
        })
        return IndustrialGraphBuild(
            nodes=tuple(nodes.values()),
            edges=tuple(edges.values()),
            evidence=tuple(evidence.values()),
            edge_evidence=tuple(links.values()),
            source_watermark=watermark,
        )

    def _add_supply_chain_seed_records(
        self,
        *,
        add_node: Any,
        add_evidence: Any,
        add_edge: Any,
    ) -> None:
        companies_by_theme: dict[str, dict[str, IndustrialGraphNode]] = {}
        for seed in self.themes:
            companies = companies_by_theme.setdefault(seed.theme_id, {})
            theme_node = IndustrialGraphNode("Theme", seed.theme_id, seed.name, aliases=seed.aliases)
            add_node(theme_node)
            for legacy_role, rows in sorted(seed.supply_chain_roles.items()):
                canonical_role = canonical_supply_chain_role(legacy_role)
                role_node = IndustrialGraphNode(
                    "Industry",
                    supply_chain_role_key(seed.theme_id, canonical_role),
                    canonical_role,
                    aliases=(legacy_role.replace("_", " "),),
                    external_ids={
                        "canonical_role": canonical_role,
                        "theme_id": seed.theme_id,
                    },
                )
                add_node(role_node)
                for row in sorted(rows, key=lambda item: item.ticker.upper()):
                    ticker = row.ticker.upper()
                    company_node = IndustrialGraphNode(
                        "Company",
                        ticker,
                        row.company_name,
                        external_ids={"ticker": ticker},
                    )
                    companies[ticker] = company_node
                    add_node(company_node)
                    payload = {
                        "theme_id": seed.theme_id,
                        "theme_name": seed.name,
                        "legacy_role": legacy_role,
                        "canonical_role": canonical_role,
                        "ticker": ticker,
                        "company_name": row.company_name,
                        "role": row.role,
                        "beneficiary_type": row.beneficiary_type,
                        "relationship_strength": row.relationship_strength,
                    }
                    role_evidence = add_evidence(
                        IndustrialGraphEvidence.from_payload(
                            "seed:curated",
                            _record_id(seed.theme_id, "supply_chain", legacy_role, ticker),
                            (
                                f"Curated supply-chain role: {row.company_name} is in the "
                                f"{canonical_role} layer for {seed.name}."
                            ),
                            payload,
                        )
                    )
                    add_edge(
                        IndustrialGraphEdge(
                            theme_node.identity_key,
                            "PART_OF_SUPPLY_CHAIN",
                            role_node.identity_key,
                            confidence_score=float(row.relationship_strength),
                            dependency_strength=float(row.relationship_strength),
                        ),
                        role_evidence,
                    )
                    add_edge(
                        IndustrialGraphEdge(
                            role_node.identity_key,
                            "SUPPLY_CHAIN_ROLE",
                            company_node.identity_key,
                            confidence_score=float(row.relationship_strength),
                            dependency_strength=float(row.relationship_strength),
                        ),
                        role_evidence,
                    )

        for seed in self.themes:
            companies = companies_by_theme[seed.theme_id]
            for connection in sorted(
                seed.supply_chain_connections,
                key=lambda row: (
                    row.source_ticker.upper(),
                    row.relationship_type,
                    row.target_ticker.upper(),
                ),
            ):
                source_ticker = connection.source_ticker.upper()
                target_ticker = connection.target_ticker.upper()
                if source_ticker not in companies or target_ticker not in companies:
                    raise ValueError(
                        "Curated supply-chain connection endpoint is not registered "
                        f"for {seed.theme_id}: {source_ticker}->{target_ticker}"
                    )
                evidence = add_evidence(
                    IndustrialGraphEvidence.from_payload(
                        "seed:curated_supply_chain",
                        _record_id(
                            seed.theme_id,
                            source_ticker,
                            connection.relationship_type,
                            target_ticker,
                        ),
                        connection.citation,
                        {
                            "theme_id": seed.theme_id,
                            "source_ticker": source_ticker,
                            "relationship_type": connection.relationship_type,
                            "target_ticker": target_ticker,
                            "citation": connection.citation,
                            "confidence_score": connection.confidence_score,
                            "dependency_strength": connection.dependency_strength,
                        },
                    )
                )
                add_edge(
                    IndustrialGraphEdge(
                        companies[source_ticker].identity_key,
                        connection.relationship_type,
                        companies[target_ticker].identity_key,
                        confidence_score=connection.confidence_score,
                        dependency_strength=connection.dependency_strength,
                    ),
                    evidence,
                )

    def _add_technology_process_seed_records(
        self,
        *,
        add_node: Any,
        add_evidence: Any,
        add_edge: Any,
    ) -> None:
        for seed in self.themes:
            theme_node = IndustrialGraphNode(
                "Theme",
                seed.theme_id,
                seed.name,
                aliases=seed.aliases,
            )
            add_node(theme_node)
            technologies = {
                row.key: IndustrialGraphNode(
                    "Technology",
                    technology_key(row.name),
                    row.name,
                    aliases=row.aliases,
                )
                for row in seed.technologies
            }
            processes = {
                row.key: IndustrialGraphNode(
                    "Process",
                    process_key(row.name),
                    row.name,
                    aliases=row.aliases,
                )
                for row in seed.processes
            }
            constraints = _constraint_nodes(seed)
            companies = {
                row.ticker.upper(): IndustrialGraphNode(
                    "Company",
                    row.ticker,
                    row.company_name,
                    external_ids={"ticker": row.ticker.upper()},
                )
                for rows in seed.supply_chain_roles.values()
                for row in rows
            }
            for row in (
                *seed.seed_beneficiaries,
                *seed.controllers,
                *seed.resolution_enablers,
            ):
                companies[row.ticker.upper()] = IndustrialGraphNode(
                    "Company",
                    row.ticker,
                    row.company_name,
                    external_ids={"ticker": row.ticker.upper()},
                )

            for row in seed.technologies:
                technology_node = technologies[row.key]
                add_node(technology_node)
                evidence = add_evidence(
                    IndustrialGraphEvidence.from_payload(
                        "seed:curated_technology",
                        _record_id(seed.theme_id, "technology", row.key),
                        row.citation,
                        {
                            "theme_id": seed.theme_id,
                            "technology_key": row.key,
                            "technology_name": row.name,
                            "aliases": row.aliases,
                        },
                    )
                )
                add_edge(
                    IndustrialGraphEdge(
                        theme_node.identity_key,
                        "USES_TECHNOLOGY",
                        technology_node.identity_key,
                    ),
                    evidence,
                )

            for row in seed.processes:
                process_node = processes[row.key]
                add_node(process_node)
                for link in row.constraint_links:
                    constraint_node = constraints.get(
                        link.constraint_key or link.constraint_name
                    )
                    if constraint_node is None:
                        continue
                    add_node(constraint_node)
                    evidence = add_evidence(
                        IndustrialGraphEvidence.from_payload(
                            "seed:curated_process_constraint",
                            _record_id(
                                seed.theme_id,
                                row.key,
                                "constraint",
                                link.constraint_name,
                            ),
                            link.citation,
                            {
                                "theme_id": seed.theme_id,
                                "process_key": row.key,
                                "constraint_name": link.constraint_name,
                            },
                        )
                    )
                    add_edge(
                        IndustrialGraphEdge(
                            process_node.identity_key,
                            link.relationship_type,
                            constraint_node.identity_key,
                        ),
                        evidence,
                    )
                for link in row.resolution_links:
                    ticker = link.ticker.upper()
                    company_node = companies[ticker]
                    add_node(company_node)
                    evidence = add_evidence(
                        IndustrialGraphEvidence.from_payload(
                            "seed:curated_process_resolution",
                            _record_id(seed.theme_id, row.key, "resolver", ticker),
                            link.citation,
                            {
                                "theme_id": seed.theme_id,
                                "process_key": row.key,
                                "ticker": ticker,
                            },
                        )
                    )
                    add_edge(
                        IndustrialGraphEdge(
                            process_node.identity_key,
                            "PROCESS_RESOLVED_BY_COMPANY",
                            company_node.identity_key,
                        ),
                        evidence,
                    )

            for link in sorted(
                seed.technology_process_links,
                key=lambda row: (
                    row.technology_key,
                    row.relationship_type,
                    row.process_key,
                ),
            ):
                technology_node = technologies[link.technology_key]
                process_node = processes[link.process_key]
                add_node(technology_node)
                add_node(process_node)
                evidence = add_evidence(
                    IndustrialGraphEvidence.from_payload(
                        "seed:curated_technology_process",
                        _record_id(
                            seed.theme_id,
                            link.technology_key,
                            link.relationship_type,
                            link.process_key,
                        ),
                        link.citation,
                        {
                            "theme_id": seed.theme_id,
                            "technology_key": link.technology_key,
                            "process_key": link.process_key,
                            "relationship_type": link.relationship_type,
                        },
                    )
                )
                add_edge(
                    IndustrialGraphEdge(
                        technology_node.identity_key,
                        link.relationship_type,
                        process_node.identity_key,
                    ),
                    evidence,
                )

            for link in sorted(
                seed.process_dependencies,
                key=lambda row: (
                    row.source_process_key,
                    row.relationship_type,
                    row.target_process_key,
                ),
            ):
                source = processes[link.source_process_key]
                target = processes[link.target_process_key]
                add_node(source)
                add_node(target)
                evidence = add_evidence(
                    IndustrialGraphEvidence.from_payload(
                        "seed:curated_process_dependency",
                        _record_id(
                            seed.theme_id,
                            link.source_process_key,
                            link.relationship_type,
                            link.target_process_key,
                        ),
                        link.citation,
                        {
                            "theme_id": seed.theme_id,
                            "source_process_key": link.source_process_key,
                            "target_process_key": link.target_process_key,
                            "relationship_type": link.relationship_type,
                        },
                    )
                )
                add_edge(
                    IndustrialGraphEdge(
                        source.identity_key,
                        link.relationship_type,
                        target.identity_key,
                    ),
                    evidence,
                )

    def _add_material_seed_records(
        self,
        *,
        add_node: Any,
        add_evidence: Any,
        add_edge: Any,
    ) -> None:
        for seed in self.themes:
            theme_node = IndustrialGraphNode(
                "Theme",
                seed.theme_id,
                seed.name,
                aliases=seed.aliases,
            )
            materials = {
                row.key: IndustrialGraphNode(
                    "Material",
                    material_key(row.name),
                    row.name,
                    aliases=row.aliases,
                    external_ids={"category": row.category},
                )
                for row in seed.materials
            }
            processes = {
                row.key: IndustrialGraphNode(
                    "Process",
                    process_key(row.name),
                    row.name,
                    aliases=row.aliases,
                )
                for row in seed.processes
            }
            constraints = _constraint_nodes(seed)
            companies = {
                row.ticker.upper(): IndustrialGraphNode(
                    "Company",
                    row.ticker,
                    row.company_name,
                    external_ids={"ticker": row.ticker.upper()},
                )
                for rows in seed.supply_chain_roles.values()
                for row in rows
            }
            for row in (
                *seed.seed_beneficiaries,
                *seed.controllers,
                *seed.resolution_enablers,
            ):
                companies[row.ticker.upper()] = IndustrialGraphNode(
                    "Company",
                    row.ticker,
                    row.company_name,
                    external_ids={"ticker": row.ticker.upper()},
                )

            add_node(theme_node)
            for row in seed.materials:
                add_node(materials[row.key])

            def evidence_for(
                source_record_id: str,
                citation: str,
                payload: dict[str, object],
            ) -> IndustrialGraphEvidence:
                return add_evidence(
                    IndustrialGraphEvidence.from_payload(
                        "seed:curated_material",
                        source_record_id,
                        citation,
                        payload,
                    )
                )

            for link in sorted(
                seed.process_material_links,
                key=lambda row: (
                    row.process_key,
                    row.relationship_type,
                    row.material_key,
                ),
            ):
                process_node = processes[link.process_key]
                material_node = materials[link.material_key]
                add_node(process_node)
                if link.relationship_type == "PROCESS_REQUIRES_MATERIAL":
                    source, target = process_node, material_node
                else:
                    source, target = material_node, process_node
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.process_key,
                        link.relationship_type,
                        link.material_key,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "process_key": link.process_key,
                        "material_key": link.material_key,
                        "relationship_type": link.relationship_type,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        source.identity_key,
                        link.relationship_type,
                        target.identity_key,
                    ),
                    evidence,
                )

            for link in seed.theme_material_links:
                material_node = materials[link.material_key]
                evidence = evidence_for(
                    _record_id(seed.theme_id, link.relationship_type, link.material_key),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "material_key": link.material_key,
                        "relationship_type": link.relationship_type,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        theme_node.identity_key,
                        link.relationship_type,
                        material_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.material_supplier_links:
                material_node = materials[link.material_key]
                company_node = companies[link.ticker.upper()]
                add_node(company_node)
                evidence = evidence_for(
                    _record_id(seed.theme_id, link.material_key, "supplier", link.ticker),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "material_key": link.material_key,
                        "ticker": link.ticker.upper(),
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        material_node.identity_key,
                        "MATERIAL_SUPPLIED_BY",
                        company_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.material_substitution_links:
                source = materials[link.source_material_key]
                target = materials[link.target_material_key]
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.source_material_key,
                        "substitutes",
                        link.target_material_key,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "source_material_key": link.source_material_key,
                        "target_material_key": link.target_material_key,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        source.identity_key,
                        "MATERIAL_SUBSTITUTES_FOR",
                        target.identity_key,
                    ),
                    evidence,
                )

            for link in seed.material_constraint_links:
                material_node = materials[link.material_key]
                constraint_node = constraints.get(
                    link.constraint_key or link.constraint_name
                )
                if constraint_node is None:
                    continue
                add_node(constraint_node)
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.material_key,
                        "constraint",
                        link.constraint_name,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "material_key": link.material_key,
                        "constraint_name": link.constraint_name,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        material_node.identity_key,
                        link.relationship_type,
                        constraint_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.material_resolution_links:
                material_node = materials[link.material_key]
                company_node = companies[link.ticker.upper()]
                add_node(company_node)
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.material_key,
                        "resolution",
                        link.ticker,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "material_key": link.material_key,
                        "ticker": link.ticker.upper(),
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        material_node.identity_key,
                        "MATERIAL_RESOLVED_BY",
                        company_node.identity_key,
                    ),
                    evidence,
                )

    def _add_equipment_seed_records(
        self,
        *,
        add_node: Any,
        add_evidence: Any,
        add_edge: Any,
    ) -> None:
        for seed in self.themes:
            theme_node = IndustrialGraphNode(
                "Theme",
                seed.theme_id,
                seed.name,
                aliases=seed.aliases,
            )
            equipment = {
                row.key: IndustrialGraphNode(
                    "Equipment",
                    equipment_key(row.name),
                    row.name,
                    aliases=row.aliases,
                    external_ids={"category": row.category},
                )
                for row in seed.equipment
            }
            processes = {
                row.key: IndustrialGraphNode(
                    "Process",
                    process_key(row.name),
                    row.name,
                    aliases=row.aliases,
                )
                for row in seed.processes
            }
            constraints = _constraint_nodes(seed)

            add_node(theme_node)
            for row in seed.equipment:
                add_node(equipment[row.key])

            def evidence_for(
                source_record_id: str,
                citation: str,
                payload: dict[str, object],
                source_type: str = "seed:curated_equipment",
            ) -> IndustrialGraphEvidence:
                return add_evidence(
                    IndustrialGraphEvidence.from_payload(
                        source_type,
                        source_record_id,
                        citation,
                        payload,
                    )
                )

            for link in sorted(
                seed.process_equipment_links,
                key=lambda row: (
                    row.process_key,
                    row.relationship_type,
                    row.equipment_key,
                ),
            ):
                process_node = processes[link.process_key]
                equipment_node = equipment[link.equipment_key]
                add_node(process_node)
                if link.relationship_type == "PROCESS_REQUIRES_EQUIPMENT":
                    source, target = process_node, equipment_node
                else:
                    source, target = equipment_node, process_node
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.process_key,
                        link.relationship_type,
                        link.equipment_key,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "process_key": link.process_key,
                        "equipment_key": link.equipment_key,
                        "relationship_type": link.relationship_type,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        source.identity_key,
                        link.relationship_type,
                        target.identity_key,
                    ),
                    evidence,
                )

            for link in seed.theme_equipment_links:
                equipment_node = equipment[link.equipment_key]
                evidence = evidence_for(
                    _record_id(seed.theme_id, link.relationship_type, link.equipment_key),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "equipment_key": link.equipment_key,
                        "relationship_type": link.relationship_type,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        theme_node.identity_key,
                        link.relationship_type,
                        equipment_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.equipment_producer_links:
                equipment_node = equipment[link.equipment_key]
                ticker = link.ticker.upper()
                company_node = IndustrialGraphNode(
                    "Company",
                    ticker,
                    link.company_name,
                    external_ids={"ticker": ticker},
                )
                add_node(company_node)
                evidence = evidence_for(
                    _record_id(seed.theme_id, link.equipment_key, "producer", ticker),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "equipment_key": link.equipment_key,
                        "ticker": ticker,
                        "company_name": link.company_name,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        equipment_node.identity_key,
                        "EQUIPMENT_PRODUCED_BY",
                        company_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.equipment_substitution_links:
                source = equipment[link.source_equipment_key]
                target = equipment[link.target_equipment_key]
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.source_equipment_key,
                        "substitutes",
                        link.target_equipment_key,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "source_equipment_key": link.source_equipment_key,
                        "target_equipment_key": link.target_equipment_key,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        source.identity_key,
                        "EQUIPMENT_SUBSTITUTES_FOR",
                        target.identity_key,
                    ),
                    evidence,
                )

            for link in seed.equipment_constraint_links:
                equipment_node = equipment[link.equipment_key]
                constraint_node = constraints.get(
                    link.constraint_key or link.constraint_name
                )
                if constraint_node is None:
                    continue
                add_node(constraint_node)
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.equipment_key,
                        "constraint",
                        link.constraint_name,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "equipment_key": link.equipment_key,
                        "constraint_name": link.constraint_name,
                    },
                    source_type="seed:curated_constraint",
                )
                add_edge(
                    IndustrialGraphEdge(
                        equipment_node.identity_key,
                        link.relationship_type,
                        constraint_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.equipment_resolution_links:
                equipment_node = equipment[link.equipment_key]
                ticker = link.ticker.upper()
                company_node = IndustrialGraphNode(
                    "Company",
                    ticker,
                    link.company_name,
                    external_ids={"ticker": ticker},
                )
                add_node(company_node)
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.equipment_key,
                        "resolution",
                        ticker,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "equipment_key": link.equipment_key,
                        "ticker": ticker,
                        "company_name": link.company_name,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        equipment_node.identity_key,
                        "EQUIPMENT_RESOLVED_BY",
                        company_node.identity_key,
                    ),
                    evidence,
                )

    def _add_constraint_seed_records(
        self,
        *,
        add_node: Any,
        add_evidence: Any,
        add_edge: Any,
    ) -> None:
        for seed in self.themes:
            theme_node = IndustrialGraphNode(
                "Theme",
                seed.theme_id,
                seed.name,
                aliases=seed.aliases,
            )
            constraints = _constraint_nodes(seed)
            technologies = {
                row.key: IndustrialGraphNode(
                    "Technology",
                    technology_key(row.name),
                    row.name,
                    aliases=row.aliases,
                )
                for row in seed.technologies
            }
            processes = {
                row.key: IndustrialGraphNode(
                    "Process",
                    process_key(row.name),
                    row.name,
                    aliases=row.aliases,
                )
                for row in seed.processes
            }
            materials = {
                row.key: IndustrialGraphNode(
                    "Material",
                    material_key(row.name),
                    row.name,
                    aliases=row.aliases,
                    external_ids={"category": row.category},
                )
                for row in seed.materials
            }
            equipment = {
                row.key: IndustrialGraphNode(
                    "Equipment",
                    equipment_key(row.name),
                    row.name,
                    aliases=row.aliases,
                    external_ids={"category": row.category},
                )
                for row in seed.equipment
            }

            add_node(theme_node)
            for row in seed.constraints:
                add_node(constraints[row.key])

            def evidence_for(
                source_record_id: str,
                citation: str,
                payload: dict[str, object],
            ) -> IndustrialGraphEvidence:
                return add_evidence(
                    IndustrialGraphEvidence.from_payload(
                        "seed:curated_constraint",
                        source_record_id,
                        citation,
                        payload,
                    )
                )

            for link in seed.theme_constraint_links:
                constraint_node = constraints[link.constraint_key]
                evidence = evidence_for(
                    _record_id(seed.theme_id, link.relationship_type, link.constraint_key),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "constraint_key": link.constraint_key,
                        "relationship_type": link.relationship_type,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        theme_node.identity_key,
                        link.relationship_type,
                        constraint_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.technology_constraint_links:
                technology_node = technologies[link.technology_key]
                constraint_node = constraints[link.constraint_key]
                add_node(technology_node)
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.technology_key,
                        link.relationship_type,
                        link.constraint_key,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "technology_key": link.technology_key,
                        "constraint_key": link.constraint_key,
                        "relationship_type": link.relationship_type,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        technology_node.identity_key,
                        link.relationship_type,
                        constraint_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.constraint_resolver_links:
                constraint_node = constraints[link.constraint_key]
                ticker = link.ticker.upper()
                company_node = IndustrialGraphNode(
                    "Company",
                    ticker,
                    link.company_name,
                    external_ids={"ticker": ticker},
                )
                add_node(company_node)
                evidence = evidence_for(
                    _record_id(seed.theme_id, link.constraint_key, "resolver", ticker),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "constraint_key": link.constraint_key,
                        "ticker": ticker,
                        "company_name": link.company_name,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        constraint_node.identity_key,
                        "CONSTRAINT_RESOLVED_BY_COMPANY",
                        company_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.company_constraint_exposure_links:
                constraint_node = constraints[link.constraint_key]
                ticker = link.ticker.upper()
                company_node = IndustrialGraphNode(
                    "Company",
                    ticker,
                    link.company_name,
                    external_ids={"ticker": ticker},
                )
                add_node(company_node)
                evidence = evidence_for(
                    _record_id(seed.theme_id, ticker, "exposure", link.constraint_key),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "constraint_key": link.constraint_key,
                        "ticker": ticker,
                        "company_name": link.company_name,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        company_node.identity_key,
                        "COMPANY_EXPOSED_TO_CONSTRAINT",
                        constraint_node.identity_key,
                    ),
                    evidence,
                )

            dependency_nodes = {
                "Process": processes,
                "Material": materials,
                "Equipment": equipment,
            }
            for link in seed.constraint_dependencies:
                constraint_node = constraints[link.constraint_key]
                target_node = dependency_nodes[link.target_type][link.target_key]
                add_node(target_node)
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.constraint_key,
                        link.relationship_type,
                        link.target_type,
                        link.target_key,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "constraint_key": link.constraint_key,
                        "target_type": link.target_type,
                        "target_key": link.target_key,
                        "relationship_type": link.relationship_type,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        constraint_node.identity_key,
                        link.relationship_type,
                        target_node.identity_key,
                    ),
                    evidence,
                )

            for link in seed.constraint_relations:
                source = constraints[link.source_constraint_key]
                target = constraints[link.target_constraint_key]
                evidence = evidence_for(
                    _record_id(
                        seed.theme_id,
                        link.source_constraint_key,
                        "related",
                        link.target_constraint_key,
                    ),
                    link.citation,
                    {
                        "theme_id": seed.theme_id,
                        "source_constraint_key": link.source_constraint_key,
                        "target_constraint_key": link.target_constraint_key,
                    },
                )
                add_edge(
                    IndustrialGraphEdge(
                        source.identity_key,
                        "CONSTRAINT_RELATED_TO_CONSTRAINT",
                        target.identity_key,
                    ),
                    evidence,
                )
