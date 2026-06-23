from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SeedCatalyst:
    name: str
    catalyst_type: str
    description: str
    impact_score: float = 55.0
    confidence_score: float = 60.0
    novelty_score: float = 50.0
    duration_score: float = 50.0
    stage_relevance: float = 55.0
    timeline_status: str = "current"
    polarity: str = "positive"


@dataclass(frozen=True)
class SeedBottleneck:
    name: str
    bottleneck_type: str
    description: str
    severity_score: float = 60.0
    duration_score: float = 55.0
    resolution_probability: float = 45.0
    impact_score: float = 60.0
    timeline_status: str = "current"


@dataclass(frozen=True)
class SeedBeneficiary:
    ticker: str
    company_name: str
    beneficiary_type: str
    role: str
    relationship_strength: float = 60.0
    dual_role_rationale: str = ""


@dataclass(frozen=True)
class SeedLifecycleHint:
    stage: str
    confidence: float
    expected_next_stage: str
    rationale: str


@dataclass(frozen=True)
class SeedSupplyChainConnection:
    source_ticker: str
    relationship_type: str
    target_ticker: str
    citation: str
    confidence_score: float = 100.0
    dependency_strength: float = 0.0


@dataclass(frozen=True)
class SeedTechnology:
    key: str
    name: str
    citation: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedProcessConstraintLink:
    constraint_name: str
    citation: str
    constraint_key: str = ""
    relationship_type: str = "PROCESS_LIMITED_BY_CONSTRAINT"


@dataclass(frozen=True)
class SeedProcessResolutionLink:
    ticker: str
    citation: str


@dataclass(frozen=True)
class SeedProcess:
    key: str
    name: str
    citation: str
    aliases: tuple[str, ...] = ()
    constraint_links: tuple[SeedProcessConstraintLink, ...] = ()
    resolution_links: tuple[SeedProcessResolutionLink, ...] = ()


@dataclass(frozen=True)
class SeedTechnologyProcessLink:
    technology_key: str
    process_key: str
    relationship_type: str
    citation: str


@dataclass(frozen=True)
class SeedProcessDependency:
    source_process_key: str
    target_process_key: str
    relationship_type: str
    citation: str


@dataclass(frozen=True)
class SeedMaterial:
    key: str
    name: str
    category: str
    citation: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedProcessMaterialLink:
    process_key: str
    material_key: str
    relationship_type: str
    citation: str


@dataclass(frozen=True)
class SeedThemeMaterialLink:
    material_key: str
    relationship_type: str
    citation: str


@dataclass(frozen=True)
class SeedMaterialSupplierLink:
    material_key: str
    ticker: str
    citation: str


@dataclass(frozen=True)
class SeedMaterialSubstitutionLink:
    source_material_key: str
    target_material_key: str
    citation: str


@dataclass(frozen=True)
class SeedMaterialConstraintLink:
    material_key: str
    constraint_name: str
    citation: str
    constraint_key: str = ""
    relationship_type: str = "MATERIAL_LIMITED_BY_CONSTRAINT"


@dataclass(frozen=True)
class SeedMaterialResolutionLink:
    material_key: str
    ticker: str
    citation: str


@dataclass(frozen=True)
class SeedEquipment:
    key: str
    name: str
    category: str
    citation: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedProcessEquipmentLink:
    process_key: str
    equipment_key: str
    relationship_type: str
    citation: str


@dataclass(frozen=True)
class SeedThemeEquipmentLink:
    equipment_key: str
    relationship_type: str
    citation: str


@dataclass(frozen=True)
class SeedEquipmentProducerLink:
    equipment_key: str
    ticker: str
    company_name: str
    citation: str


@dataclass(frozen=True)
class SeedEquipmentSubstitutionLink:
    source_equipment_key: str
    target_equipment_key: str
    citation: str


@dataclass(frozen=True)
class SeedEquipmentConstraintLink:
    equipment_key: str
    constraint_name: str
    citation: str
    constraint_key: str = ""
    relationship_type: str = "EQUIPMENT_LIMITED_BY_CONSTRAINT"


@dataclass(frozen=True)
class SeedEquipmentResolutionLink:
    equipment_key: str
    ticker: str
    company_name: str
    citation: str


@dataclass(frozen=True)
class SeedConstraint:
    key: str
    name: str
    category: str
    citation: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedThemeConstraintLink:
    constraint_key: str
    relationship_type: str
    citation: str


@dataclass(frozen=True)
class SeedTechnologyConstraintLink:
    technology_key: str
    constraint_key: str
    relationship_type: str
    citation: str


@dataclass(frozen=True)
class SeedConstraintResolverLink:
    constraint_key: str
    ticker: str
    company_name: str
    citation: str


@dataclass(frozen=True)
class SeedCompanyConstraintExposureLink:
    ticker: str
    company_name: str
    constraint_key: str
    citation: str


@dataclass(frozen=True)
class SeedConstraintDependencyLink:
    constraint_key: str
    target_type: str
    target_key: str
    relationship_type: str
    citation: str


@dataclass(frozen=True)
class SeedConstraintRelationLink:
    source_constraint_key: str
    target_constraint_key: str
    citation: str


@dataclass(frozen=True)
class ThemeSeed:
    theme_id: str
    name: str
    name_zh: str
    aliases: tuple[str, ...]
    supply_chain_roles: dict[str, tuple[SeedBeneficiary, ...]]
    seed_catalysts: tuple[SeedCatalyst, ...]
    seed_bottlenecks: tuple[SeedBottleneck, ...]
    seed_beneficiaries: tuple[SeedBeneficiary, ...]
    controllers: tuple[SeedBeneficiary, ...]
    resolution_enablers: tuple[SeedBeneficiary, ...]
    lifecycle_hint: SeedLifecycleHint
    risk_notes: tuple[str, ...]
    metadata: dict[str, object] = field(default_factory=dict)
    supply_chain_connections: tuple[SeedSupplyChainConnection, ...] = ()
    technologies: tuple[SeedTechnology, ...] = ()
    processes: tuple[SeedProcess, ...] = ()
    technology_process_links: tuple[SeedTechnologyProcessLink, ...] = ()
    process_dependencies: tuple[SeedProcessDependency, ...] = ()
    materials: tuple[SeedMaterial, ...] = ()
    process_material_links: tuple[SeedProcessMaterialLink, ...] = ()
    theme_material_links: tuple[SeedThemeMaterialLink, ...] = ()
    material_supplier_links: tuple[SeedMaterialSupplierLink, ...] = ()
    material_substitution_links: tuple[SeedMaterialSubstitutionLink, ...] = ()
    material_constraint_links: tuple[SeedMaterialConstraintLink, ...] = ()
    material_resolution_links: tuple[SeedMaterialResolutionLink, ...] = ()
    equipment: tuple[SeedEquipment, ...] = ()
    process_equipment_links: tuple[SeedProcessEquipmentLink, ...] = ()
    theme_equipment_links: tuple[SeedThemeEquipmentLink, ...] = ()
    equipment_producer_links: tuple[SeedEquipmentProducerLink, ...] = ()
    equipment_substitution_links: tuple[SeedEquipmentSubstitutionLink, ...] = ()
    equipment_constraint_links: tuple[SeedEquipmentConstraintLink, ...] = ()
    equipment_resolution_links: tuple[SeedEquipmentResolutionLink, ...] = ()
    constraints: tuple[SeedConstraint, ...] = ()
    theme_constraint_links: tuple[SeedThemeConstraintLink, ...] = ()
    technology_constraint_links: tuple[SeedTechnologyConstraintLink, ...] = ()
    constraint_resolver_links: tuple[SeedConstraintResolverLink, ...] = ()
    company_constraint_exposure_links: tuple[SeedCompanyConstraintExposureLink, ...] = ()
    constraint_dependencies: tuple[SeedConstraintDependencyLink, ...] = ()
    constraint_relations: tuple[SeedConstraintRelationLink, ...] = ()
