from __future__ import annotations

from dataclasses import replace

from .theme_seed_models import (
    SeedBeneficiary,
    SeedBottleneck,
    SeedCatalyst,
    SeedCompanyConstraintExposureLink,
    SeedConstraint,
    SeedConstraintDependencyLink,
    SeedConstraintRelationLink,
    SeedConstraintResolverLink,
    SeedEquipment,
    SeedEquipmentConstraintLink,
    SeedEquipmentProducerLink,
    SeedEquipmentResolutionLink,
    SeedEquipmentSubstitutionLink,
    SeedLifecycleHint,
    SeedMaterial,
    SeedMaterialConstraintLink,
    SeedMaterialResolutionLink,
    SeedMaterialSubstitutionLink,
    SeedMaterialSupplierLink,
    SeedProcess,
    SeedProcessConstraintLink,
    SeedProcessDependency,
    SeedProcessEquipmentLink,
    SeedProcessMaterialLink,
    SeedProcessResolutionLink,
    SeedThemeMaterialLink,
    SeedThemeEquipmentLink,
    SeedThemeConstraintLink,
    SeedTechnology,
    SeedTechnologyConstraintLink,
    SeedTechnologyProcessLink,
    ThemeSeed,
)


def b(ticker: str, company: str, beneficiary_type: str, role: str, strength: float = 62.0, rationale: str = "") -> SeedBeneficiary:
    return SeedBeneficiary(ticker, company, beneficiary_type, role, strength, rationale)


TARGET_SEED_THEMES: tuple[ThemeSeed, ...] = (
    ThemeSeed(
        theme_id="glass_substrate",
        name="Glass Substrate",
        name_zh="玻璃基板",
        aliases=("glass substrate", "glass core substrate", "advanced packaging substrate", "panel level packaging", "glass interposer"),
        supply_chain_roles={
            "upstream_materials": (b("GLW", "Corning Incorporated", "Direct Beneficiary", "glass materials", 72), b("APH", "Amphenol Corporation", "Indirect Beneficiary", "interconnect materials", 58)),
            "equipment": (b("AMAT", "Applied Materials", "Resolution Enabler", "packaging equipment", 67), b("KLAC", "KLA Corporation", "Resolution Enabler", "inspection and process control", 66)),
            "manufacturing": (b("GLW", "Corning Incorporated", "Direct Beneficiary", "substrate manufacturing", 74, "Corning can be both materials supplier and direct beneficiary."), b("IBIDEN", "Ibiden Co Ltd", "Direct Beneficiary", "substrate manufacturing", 63)),
            "packaging": (b("TSM", "Taiwan Semiconductor Manufacturing", "Bottleneck Controller", "advanced packaging capacity owner", 70), b("ASX", "ASE Technology Holding", "Resolution Enabler", "OSAT packaging", 62)),
            "downstream": (b("NVDA", "NVIDIA Corporation", "Indirect Beneficiary", "AI accelerator demand", 68), b("AVGO", "Broadcom Inc.", "Indirect Beneficiary", "custom silicon demand", 65)),
        },
        seed_catalysts=(
            SeedCatalyst("Advanced Packaging Substrate Demand", "Industry Demand", "AI accelerators increase demand for higher-density substrate technology.", 66, 72, 58, 70, 66),
            SeedCatalyst("Panel Level Packaging Qualification", "Technology Breakthrough", "Panel-level process learning can improve substrate cost and scale.", 61, 64, 68, 62, 65),
        ),
        seed_bottlenecks=(
            SeedBottleneck("Yield", "Yield Constraint", "Yield maturity limits scalable adoption of glass substrate processes.", 78, 70, 48, 76),
            SeedBottleneck("Inspection Tooling", "Equipment Constraint", "Inspection and metrology readiness can constrain panel-level packaging ramps.", 64, 58, 55, 61),
        ),
        seed_beneficiaries=(b("GLW", "Corning Incorporated", "Direct Beneficiary", "glass substrate material and process leader", 74, "Corning can be both materials supplier and direct beneficiary."), b("IBIDEN", "Ibiden Co Ltd", "Direct Beneficiary", "substrate manufacturing", 63), b("ASX", "ASE Technology Holding", "Resolution Enabler", "advanced packaging enablement", 62)),
        controllers=(b("TSM", "Taiwan Semiconductor Manufacturing", "Bottleneck Controller", "advanced packaging capacity owner", 70),),
        resolution_enablers=(b("AMAT", "Applied Materials", "Resolution Enabler", "packaging equipment", 67), b("KLAC", "KLA Corporation", "Resolution Enabler", "inspection tooling", 66)),
        lifecycle_hint=SeedLifecycleHint("Early", 58, "Growth", "Commercial evidence exists but yield and qualification remain gating items."),
        risk_notes=("Yield ramp can lag demand signals.", "Material qualification cycles can be slow.", "Adoption can concentrate around a small group of packaging customers."),
    ),
    ThemeSeed(
        theme_id="hbm",
        name="HBM",
        name_zh="高頻寬記憶體",
        aliases=("hbm", "high bandwidth memory", "hbm3e", "hbm4", "memory stack", "advanced dram"),
        supply_chain_roles={
            "memory_suppliers": (b("MU", "Micron Technology", "Direct Beneficiary", "HBM supplier", 72), b("005930.KS", "Samsung Electronics", "Direct Beneficiary", "HBM supplier", 70), b("000660.KS", "SK hynix", "Direct Beneficiary", "HBM supplier", 76)),
            "equipment": (b("AMAT", "Applied Materials", "Resolution Enabler", "memory process equipment", 64), b("LRCX", "Lam Research", "Resolution Enabler", "memory etch/deposition", 63)),
            "downstream": (b("NVDA", "NVIDIA Corporation", "Indirect Beneficiary", "accelerator attach demand", 70), b("AMD", "Advanced Micro Devices", "Indirect Beneficiary", "accelerator attach demand", 63)),
        },
        seed_catalysts=(SeedCatalyst("AI Accelerator Memory Attach", "Industry Demand", "AI accelerators require high-bandwidth stacked memory.", 72, 75, 55, 76, 70), SeedCatalyst("Next Generation HBM Qualification", "Product Launch", "HBM3E and HBM4 qualification cycles shape supplier share.", 66, 68, 62, 66, 67)),
        seed_bottlenecks=(SeedBottleneck("Advanced DRAM Capacity", "Capacity Constraint", "HBM output depends on advanced DRAM wafer starts and packaging capacity.", 72, 66, 54, 71), SeedBottleneck("Stacking Yield", "Yield Constraint", "Stacking and thermal performance can constrain HBM qualification.", 68, 62, 56, 66)),
        seed_beneficiaries=(b("MU", "Micron Technology", "Direct Beneficiary", "HBM supplier", 72), b("000660.KS", "SK hynix", "Direct Beneficiary", "HBM supplier", 76), b("005930.KS", "Samsung Electronics", "Direct Beneficiary", "HBM supplier", 70)),
        controllers=(b("000660.KS", "SK hynix", "Bottleneck Controller", "leading HBM capacity owner", 74, "Supplier can be both direct beneficiary and capacity controller."), b("MU", "Micron Technology", "Bottleneck Controller", "HBM capacity owner", 68, "Supplier can be both direct beneficiary and capacity controller.")),
        resolution_enablers=(b("AMAT", "Applied Materials", "Resolution Enabler", "memory process equipment", 64), b("LRCX", "Lam Research", "Resolution Enabler", "memory tooling", 63)),
        lifecycle_hint=SeedLifecycleHint("Growth", 70, "Expansion", "Demand is broadening across accelerator programs."),
        risk_notes=("Supplier concentration can amplify pricing swings.", "Qualification delays can shift share.", "Memory cycles can reverse quickly."),
    ),
    ThemeSeed(
        theme_id="cowos",
        name="CoWoS",
        name_zh="CoWoS先進封裝",
        aliases=("cowos", "chip on wafer on substrate", "co-wos", "2.5d packaging", "tsmc advanced packaging"),
        supply_chain_roles={"capacity_owner": (b("TSM", "Taiwan Semiconductor Manufacturing", "Bottleneck Controller", "CoWoS capacity owner", 78),), "osat": (b("ASX", "ASE Technology Holding", "Resolution Enabler", "advanced packaging support", 64),), "equipment": (b("AMAT", "Applied Materials", "Resolution Enabler", "packaging tools", 65), b("KLAC", "KLA Corporation", "Resolution Enabler", "inspection tools", 63)), "downstream": (b("NVDA", "NVIDIA Corporation", "Indirect Beneficiary", "AI accelerator demand", 70), b("AVGO", "Broadcom Inc.", "Indirect Beneficiary", "custom AI silicon", 66))},
        seed_catalysts=(SeedCatalyst("AI Accelerator Packaging Demand", "Industry Demand", "AI accelerators increase demand for 2.5D advanced packaging.", 75, 75, 54, 76, 72), SeedCatalyst("Packaging Capacity Expansion", "CapEx Expansion", "Capacity additions can ease advanced packaging allocation.", 70, 68, 57, 72, 68)),
        seed_bottlenecks=(SeedBottleneck("CoWoS Capacity", "Capacity Constraint", "CoWoS capacity availability gates accelerator shipments.", 80, 74, 56, 78),),
        seed_beneficiaries=(b("TSM", "Taiwan Semiconductor Manufacturing", "Direct Beneficiary", "advanced packaging leader", 76, "TSMC can be both direct beneficiary and capacity controller."), b("ASX", "ASE Technology Holding", "Resolution Enabler", "advanced packaging support", 64)),
        controllers=(b("TSM", "Taiwan Semiconductor Manufacturing", "Bottleneck Controller", "CoWoS capacity owner", 78, "TSMC can be both direct beneficiary and capacity controller."),),
        resolution_enablers=(b("AMAT", "Applied Materials", "Resolution Enabler", "packaging equipment", 65), b("KLAC", "KLA Corporation", "Resolution Enabler", "inspection tools", 63)),
        lifecycle_hint=SeedLifecycleHint("Growth", 72, "Expansion", "Capacity expansion is the main next-stage evidence."),
        risk_notes=("Capacity concentration is high.", "Downstream demand can pull forward orders.", "Packaging allocation can change quickly."),
    ),
    ThemeSeed(
        theme_id="ai_infrastructure",
        name="AI Infrastructure",
        name_zh="AI基礎設施",
        aliases=("ai infrastructure", "ai infra", "ai data center", "ai datacenter", "accelerated compute", "gpu cluster"),
        supply_chain_roles={"compute": (b("NVDA", "NVIDIA Corporation", "Direct Beneficiary", "AI accelerator platform", 78), b("AMD", "Advanced Micro Devices", "Direct Beneficiary", "AI accelerator platform", 66)), "networking": (b("AVGO", "Broadcom Inc.", "Direct Beneficiary", "networking and custom silicon", 70), b("ANET", "Arista Networks", "Direct Beneficiary", "AI networking", 70)), "power_cooling": (b("VRT", "Vertiv Holdings", "Resolution Enabler", "power and cooling", 72), b("ETN", "Eaton Corporation", "Resolution Enabler", "electrical infrastructure", 68)), "cloud": (b("MSFT", "Microsoft Corporation", "Indirect Beneficiary", "cloud AI capacity", 65), b("AMZN", "Amazon.com", "Indirect Beneficiary", "cloud AI capacity", 63))},
        seed_catalysts=(SeedCatalyst("AI Datacenter Expansion", "CapEx Expansion", "Hyperscale AI capacity drives compute, networking, power, and cooling demand.", 78, 74, 54, 78, 72), SeedCatalyst("Customer Adoption of Generative AI", "Customer Adoption", "Enterprise AI adoption supports infrastructure utilization.", 68, 64, 56, 64, 64)),
        seed_bottlenecks=(SeedBottleneck("Power Availability", "Infrastructure Constraint", "Power delivery can limit AI datacenter expansion.", 76, 72, 50, 76), SeedBottleneck("GPU Cluster Networking", "Supply Chain Constraint", "Cluster scale depends on networking and integration availability.", 64, 58, 56, 62)),
        seed_beneficiaries=(b("NVDA", "NVIDIA Corporation", "Direct Beneficiary", "AI accelerator platform", 78), b("AVGO", "Broadcom Inc.", "Direct Beneficiary", "networking and custom silicon", 70), b("ANET", "Arista Networks", "Direct Beneficiary", "AI networking", 70), b("VRT", "Vertiv Holdings", "Resolution Enabler", "power and cooling", 72)),
        controllers=(b("MSFT", "Microsoft Corporation", "Bottleneck Controller", "cloud capacity owner", 65), b("AMZN", "Amazon.com", "Bottleneck Controller", "cloud capacity owner", 63)),
        resolution_enablers=(b("VRT", "Vertiv Holdings", "Resolution Enabler", "thermal and power infrastructure", 72), b("ETN", "Eaton Corporation", "Resolution Enabler", "electrical equipment", 68)),
        lifecycle_hint=SeedLifecycleHint("Growth", 74, "Expansion", "Capex and customer adoption evidence are broad but infrastructure constraints matter."),
        risk_notes=("Capex digestion can pressure multiples.", "Power and cooling constraints may delay deployment.", "Customer adoption may not match capacity buildout timing."),
    ),
    ThemeSeed(
        theme_id="advanced_packaging",
        name="Advanced Packaging",
        name_zh="先進封裝",
        aliases=("advanced packaging", "chip packaging", "2.5d packaging", "3d packaging", "heterogeneous integration", "fan out packaging"),
        supply_chain_roles={"foundry": (b("TSM", "Taiwan Semiconductor Manufacturing", "Bottleneck Controller", "advanced packaging capacity", 76),), "osat": (b("ASX", "ASE Technology Holding", "Direct Beneficiary", "OSAT packaging", 68), b("AMKR", "Amkor Technology", "Direct Beneficiary", "OSAT packaging", 62)), "equipment": (b("AMAT", "Applied Materials", "Resolution Enabler", "packaging equipment", 66), b("KLAC", "KLA Corporation", "Resolution Enabler", "inspection tools", 64)), "substrates": (b("IBIDEN", "Ibiden Co Ltd", "Direct Beneficiary", "substrates", 62), b("GLW", "Corning Incorporated", "Indirect Beneficiary", "substrate materials", 58))},
        seed_catalysts=(SeedCatalyst("Heterogeneous Integration Demand", "Industry Demand", "Chiplet architectures increase packaging complexity and value.", 70, 70, 58, 72, 68), SeedCatalyst("Packaging Tool Investment", "CapEx Expansion", "Packaging equipment investment can expand available capacity.", 64, 64, 55, 64, 63)),
        seed_bottlenecks=(SeedBottleneck("Packaging Capacity", "Capacity Constraint", "Advanced packaging capacity can gate high-end semiconductor shipments.", 76, 70, 56, 74),),
        seed_beneficiaries=(b("ASX", "ASE Technology Holding", "Direct Beneficiary", "OSAT packaging", 68), b("AMKR", "Amkor Technology", "Direct Beneficiary", "OSAT packaging", 62), b("AMAT", "Applied Materials", "Resolution Enabler", "packaging tools", 66)),
        controllers=(b("TSM", "Taiwan Semiconductor Manufacturing", "Bottleneck Controller", "advanced packaging capacity owner", 76),),
        resolution_enablers=(b("AMAT", "Applied Materials", "Resolution Enabler", "packaging equipment", 66), b("KLAC", "KLA Corporation", "Resolution Enabler", "inspection tools", 64)),
        lifecycle_hint=SeedLifecycleHint("Growth", 70, "Expansion", "The theme is supported by chiplet adoption and packaging capex."),
        risk_notes=("Capacity additions may lag demand.", "Customer concentration can be high.", "Technology transitions can shift winners."),
    ),
    ThemeSeed(
        theme_id="power_grid",
        name="Power Grid",
        name_zh="電力電網",
        aliases=("power grid", "electric grid", "grid infrastructure", "grid modernization", "transmission equipment", "electrification"),
        supply_chain_roles={"electrical_equipment": (b("ETN", "Eaton Corporation", "Direct Beneficiary", "electrical equipment", 72), b("PWR", "Quanta Services", "Direct Beneficiary", "grid services", 68)), "utilities": (b("NEE", "NextEra Energy", "Indirect Beneficiary", "power generation and grid", 62), b("CEG", "Constellation Energy", "Indirect Beneficiary", "power supply", 64)), "datacenter_power": (b("VRT", "Vertiv Holdings", "Resolution Enabler", "datacenter power infrastructure", 70),)},
        seed_catalysts=(SeedCatalyst("AI Datacenter Power Demand", "Industry Demand", "AI datacenter growth increases grid interconnection and power equipment demand.", 76, 72, 54, 78, 72), SeedCatalyst("Grid Modernization Investment", "Policy / Regulation", "Policy and utility investment can support grid upgrades.", 64, 62, 52, 70, 61)),
        seed_bottlenecks=(SeedBottleneck("Transmission Capacity", "Infrastructure Constraint", "Transmission and interconnection capacity can limit power availability.", 78, 76, 44, 76),),
        seed_beneficiaries=(b("ETN", "Eaton Corporation", "Direct Beneficiary", "electrical equipment", 72), b("PWR", "Quanta Services", "Direct Beneficiary", "grid services", 68), b("VRT", "Vertiv Holdings", "Resolution Enabler", "datacenter power", 70)),
        controllers=(b("NEE", "NextEra Energy", "Bottleneck Controller", "power and grid asset owner", 62),),
        resolution_enablers=(b("ETN", "Eaton Corporation", "Resolution Enabler", "electrical equipment", 72, "Equipment supplier can also directly benefit from grid capex."), b("PWR", "Quanta Services", "Resolution Enabler", "grid services", 68, "Service provider can also directly benefit from grid capex.")),
        lifecycle_hint=SeedLifecycleHint("Early", 66, "Growth", "Demand is visible but grid buildout has long permitting and construction cycles."),
        risk_notes=("Permitting timelines can delay projects.", "Utility capex cycles are regulated.", "Power availability may constrain AI infrastructure growth."),
    ),
    ThemeSeed(
        theme_id="cpo_photonics",
        name="CPO Photonics",
        name_zh="CPO光子互連",
        aliases=("cpo photonics", "co-packaged optics", "silicon photonics", "optical interconnect", "cpo"),
        supply_chain_roles={"optical_components": (b("LITE", "Lumentum Holdings", "Direct Beneficiary", "optical components", 62), b("COHR", "Coherent Corp", "Direct Beneficiary", "optical components", 64)), "switching": (b("AVGO", "Broadcom Inc.", "Bottleneck Controller", "switch silicon and CPO integration", 70), b("MRVL", "Marvell Technology", "Direct Beneficiary", "optical DSP and connectivity", 64)), "networking": (b("ANET", "Arista Networks", "Indirect Beneficiary", "AI networking systems", 66),)},
        seed_catalysts=(SeedCatalyst("AI Cluster Optical Bandwidth Demand", "Industry Demand", "Large AI clusters increase bandwidth and power pressure on interconnects.", 70, 66, 62, 70, 66), SeedCatalyst("Co-Packaged Optics Qualification", "Technology Breakthrough", "CPO qualification would improve optical interconnect relevance.", 64, 58, 72, 60, 62)),
        seed_bottlenecks=(SeedBottleneck("CPO Qualification", "Yield Constraint", "Reliability and manufacturability remain gating items for broad CPO adoption.", 70, 68, 42, 68),),
        seed_beneficiaries=(b("COHR", "Coherent Corp", "Direct Beneficiary", "optical components", 64), b("LITE", "Lumentum Holdings", "Direct Beneficiary", "optical components", 62), b("MRVL", "Marvell Technology", "Direct Beneficiary", "optical connectivity", 64)),
        controllers=(b("AVGO", "Broadcom Inc.", "Bottleneck Controller", "switch silicon and CPO integration", 70),),
        resolution_enablers=(b("COHR", "Coherent Corp", "Resolution Enabler", "optical manufacturing", 64, "Component supplier can benefit while enabling CPO qualification."),),
        lifecycle_hint=SeedLifecycleHint("Seed", 60, "Early", "Technical qualification remains the key next-stage evidence."),
        risk_notes=("CPO adoption timing is uncertain.", "Reliability requirements are demanding.", "Alternative optical architectures may compete."),
    ),
    ThemeSeed(
        theme_id="robotics",
        name="Robotics",
        name_zh="機器人",
        aliases=("robotics", "industrial robotics", "warehouse automation", "factory automation", "autonomous robots", "robot automation"),
        supply_chain_roles={"automation": (b("ROK", "Rockwell Automation", "Direct Beneficiary", "factory automation", 64), b("TER", "Teradyne", "Direct Beneficiary", "collaborative robotics exposure", 60)), "components": (b("NVDA", "NVIDIA Corporation", "Indirect Beneficiary", "robotics compute", 58), b("KEYS", "Keysight Technologies", "Resolution Enabler", "test and sensing", 55)), "integrators": (b("SYM", "Symbotic", "Direct Beneficiary", "warehouse automation", 62),)},
        seed_catalysts=(SeedCatalyst("Industrial Automation Demand", "Industry Demand", "Labor scarcity and productivity needs support automation investment.", 64, 66, 50, 66, 62), SeedCatalyst("Robotics AI Model Improvement", "Technology Breakthrough", "Improved perception and planning models can expand robot use cases.", 62, 58, 68, 58, 60)),
        seed_bottlenecks=(SeedBottleneck("Deployment Complexity", "Talent Constraint", "Integration talent and site-specific deployment complexity can slow adoption.", 62, 62, 52, 60),),
        seed_beneficiaries=(b("ROK", "Rockwell Automation", "Direct Beneficiary", "factory automation", 64), b("SYM", "Symbotic", "Direct Beneficiary", "warehouse automation", 62), b("TER", "Teradyne", "Direct Beneficiary", "collaborative robotics exposure", 60)),
        controllers=(b("ROK", "Rockwell Automation", "Bottleneck Controller", "factory automation channel", 62, "Automation vendor can benefit while controlling deployment channels."),),
        resolution_enablers=(b("NVDA", "NVIDIA Corporation", "Resolution Enabler", "robotics compute", 58),),
        lifecycle_hint=SeedLifecycleHint("Early", 62, "Growth", "Use cases are broadening but integration remains uneven."),
        risk_notes=("Deployment cycles can be long.", "ROI can vary by site.", "Hardware margins may be cyclical."),
    ),
    ThemeSeed(
        theme_id="edge_ai",
        name="Edge AI",
        name_zh="邊緣AI",
        aliases=("edge ai", "on-device ai", "ai pc", "edge inference", "embedded ai"),
        supply_chain_roles={"processors": (b("QCOM", "Qualcomm Incorporated", "Direct Beneficiary", "edge AI processors", 68), b("AMD", "Advanced Micro Devices", "Direct Beneficiary", "AI PC processors", 62), b("INTC", "Intel Corporation", "Direct Beneficiary", "AI PC processors", 58)), "devices": (b("AAPL", "Apple Inc.", "Indirect Beneficiary", "on-device AI ecosystem", 62), b("MSFT", "Microsoft Corporation", "Indirect Beneficiary", "AI PC ecosystem", 60)), "memory": (b("MU", "Micron Technology", "Resolution Enabler", "edge memory demand", 58),)},
        seed_catalysts=(SeedCatalyst("On-Device AI Adoption", "Customer Adoption", "AI features moving onto PCs and devices increase local inference demand.", 66, 64, 58, 64, 63), SeedCatalyst("AI PC Product Cycle", "Product Launch", "AI PC and edge processor launches can expand device-level AI adoption.", 64, 62, 56, 62, 62)),
        seed_bottlenecks=(SeedBottleneck("Software Use Case Maturity", "Talent Constraint", "Edge AI depends on useful software experiences and developer adoption.", 58, 56, 58, 56),),
        seed_beneficiaries=(b("QCOM", "Qualcomm Incorporated", "Direct Beneficiary", "edge AI processors", 68), b("AMD", "Advanced Micro Devices", "Direct Beneficiary", "AI PC processors", 62), b("INTC", "Intel Corporation", "Direct Beneficiary", "AI PC processors", 58)),
        controllers=(b("MSFT", "Microsoft Corporation", "Bottleneck Controller", "AI PC software ecosystem", 60),),
        resolution_enablers=(b("AAPL", "Apple Inc.", "Resolution Enabler", "on-device AI ecosystem", 62, "Device ecosystem can benefit while enabling adoption."),),
        lifecycle_hint=SeedLifecycleHint("Seed", 58, "Early", "Product cycles are emerging but killer applications remain uncertain."),
        risk_notes=("User willingness to pay is uncertain.", "Software experiences can lag hardware capability.", "Device refresh cycles can slow adoption."),
    ),
    ThemeSeed(
        theme_id="data_center_cooling",
        name="Data Center Cooling",
        name_zh="資料中心冷卻",
        aliases=("data center cooling", "datacenter cooling", "liquid cooling", "immersion cooling", "thermal management", "ai cooling"),
        supply_chain_roles={"thermal": (b("VRT", "Vertiv Holdings", "Direct Beneficiary", "thermal management", 76), b("MOD", "Modine Manufacturing", "Direct Beneficiary", "thermal systems", 62)), "electrical": (b("ETN", "Eaton Corporation", "Resolution Enabler", "power infrastructure", 66),), "operators": (b("EQIX", "Equinix", "Bottleneck Controller", "datacenter operator", 58), b("DLR", "Digital Realty", "Bottleneck Controller", "datacenter operator", 58))},
        seed_catalysts=(SeedCatalyst("AI Rack Density Growth", "Industry Demand", "Higher rack density increases demand for liquid and advanced cooling.", 74, 72, 58, 76, 72), SeedCatalyst("Liquid Cooling Adoption", "Customer Adoption", "AI infrastructure operators are evaluating advanced cooling architectures.", 68, 66, 62, 68, 66)),
        seed_bottlenecks=(SeedBottleneck("Cooling Capacity", "Infrastructure Constraint", "Thermal capacity can limit AI datacenter deployment density.", 76, 70, 52, 74),),
        seed_beneficiaries=(b("VRT", "Vertiv Holdings", "Direct Beneficiary", "thermal management", 76), b("MOD", "Modine Manufacturing", "Direct Beneficiary", "thermal systems", 62), b("ETN", "Eaton Corporation", "Resolution Enabler", "power infrastructure", 66)),
        controllers=(b("EQIX", "Equinix", "Bottleneck Controller", "datacenter operator", 58), b("DLR", "Digital Realty", "Bottleneck Controller", "datacenter operator", 58)),
        resolution_enablers=(b("VRT", "Vertiv Holdings", "Resolution Enabler", "cooling systems", 76, "Thermal vendor can directly benefit while enabling cooling capacity."), b("MOD", "Modine Manufacturing", "Resolution Enabler", "thermal systems", 62, "Thermal vendor can directly benefit while enabling cooling capacity.")),
        lifecycle_hint=SeedLifecycleHint("Early", 66, "Growth", "AI rack density is making cooling a visible infrastructure constraint."),
        risk_notes=("Customer architecture choices can shift quickly.", "Thermal retrofits can be site-specific.", "Capacity expansion can trail GPU deployment."),
    ),
)


def _technology(key: str, name: str, citation: str) -> SeedTechnology:
    return SeedTechnology(key=key, name=name, citation=citation)


def _process(
    key: str,
    name: str,
    citation: str,
    *,
    constraints: tuple[tuple[str, str], ...] = (),
    resolvers: tuple[tuple[str, str], ...] = (),
) -> SeedProcess:
    return SeedProcess(
        key=key,
        name=name,
        citation=citation,
        constraint_links=tuple(
            SeedProcessConstraintLink(constraint_name, evidence)
            for constraint_name, evidence in constraints
        ),
        resolution_links=tuple(
            SeedProcessResolutionLink(ticker, evidence)
            for ticker, evidence in resolvers
        ),
    )


def _technology_process(
    technology: str,
    process: str,
    relationship: str,
    citation: str,
) -> SeedTechnologyProcessLink:
    return SeedTechnologyProcessLink(technology, process, relationship, citation)


def _process_dependency(
    source: str,
    target: str,
    relationship: str,
    citation: str,
) -> SeedProcessDependency:
    return SeedProcessDependency(source, target, relationship, citation)


_TECHNOLOGY_PROCESS_SEEDS: dict[str, dict[str, tuple[object, ...]]] = {
    "glass_substrate": {
        "technologies": (
            _technology("glass_core", "Glass Core Technology", "Approved seed: glass substrates use glass-core technology."),
            _technology("panel_level_packaging", "Panel Level Packaging", "Approved seed catalyst identifies panel-level packaging qualification."),
        ),
        "processes": (
            _process(
                "glass_processing",
                "Glass Processing",
                "Approved seed: glass-core substrates require glass processing.",
                constraints=(("Yield", "Approved seed: glass-processing yield limits scalable glass-substrate adoption."),),
                resolvers=(("KLAC", "Approved seed: KLA inspection and process control supports glass-processing yield resolution."),),
            ),
            _process("yield_inspection", "Yield Inspection", "Approved seed: inspection feedback is required for glass process yield."),
            _process("qualification", "Qualification", "Approved seed catalyst explicitly identifies panel-level packaging qualification."),
        ),
        "technology_process_links": (
            _technology_process("glass_core", "glass_processing", "REQUIRES_PROCESS", "Glass-core technology requires glass processing."),
            _technology_process("panel_level_packaging", "yield_inspection", "REQUIRES_PROCESS", "Panel-level packaging qualification requires yield inspection."),
        ),
        "process_dependencies": (
            _process_dependency("glass_processing", "qualification", "PROCESS_DEPENDS_ON_PROCESS", "Glass processing must reach qualification for commercial adoption."),
            _process_dependency("yield_inspection", "qualification", "PROCESS_PRECEDES_PROCESS", "Yield inspection precedes panel-level qualification."),
        ),
    },
    "hbm": {
        "technologies": (
            _technology("tsv", "TSV", "Approved seed: HBM uses through-silicon-via integration."),
            _technology("3d_memory_stacking", "3D Memory Stacking", "Approved seed: HBM uses stacked-memory integration."),
        ),
        "processes": (
            _process("tsv_etching", "TSV Etching", "Approved seed: TSV formation requires TSV etching."),
            _process(
                "wafer_bonding",
                "Wafer Bonding",
                "Approved seed: HBM stacking requires wafer bonding.",
                constraints=(("Stacking Yield", "Approved seed: stacking yield explicitly limits HBM wafer bonding."),),
                resolvers=(("LRCX", "Approved seed: Lam Research memory etch and deposition tooling supports wafer-bonding process resolution."),),
            ),
            _process("yield_inspection", "Yield Inspection", "Approved seed: stacked-memory yield requires inspection."),
            _process("qualification", "Qualification", "Approved seed catalyst identifies next-generation HBM qualification."),
        ),
        "technology_process_links": (
            _technology_process("tsv", "tsv_etching", "REQUIRES_PROCESS", "TSV technology requires TSV etching."),
            _technology_process("tsv", "wafer_bonding", "REQUIRES_PROCESS", "TSV-integrated HBM requires wafer bonding."),
            _technology_process("3d_memory_stacking", "wafer_bonding", "REQUIRES_PROCESS", "3D memory stacking requires wafer bonding."),
        ),
        "process_dependencies": (
            _process_dependency("wafer_bonding", "yield_inspection", "PROCESS_PRECEDES_PROCESS", "Wafer bonding precedes stacked-memory yield inspection."),
            _process_dependency("yield_inspection", "qualification", "PROCESS_PRECEDES_PROCESS", "Yield inspection precedes HBM qualification."),
        ),
    },
    "advanced_packaging": {
        "technologies": (
            _technology("advanced_packaging", "Advanced Packaging", "Approved seed identifies advanced packaging technology."),
            _technology("panel_level_packaging", "Panel Level Packaging", "Approved seed references panel-level packaging development."),
        ),
        "processes": (
            _process(
                "packaging",
                "Packaging",
                "Approved seed: advanced packaging requires packaging operations.",
                constraints=(("Packaging Capacity", "Approved seed: packaging capacity limits advanced-packaging shipments."),),
                resolvers=(("AMAT", "Approved seed: Applied Materials packaging equipment supports packaging process resolution."),),
            ),
            _process("assembly", "Assembly", "Approved seed: heterogeneous integration requires assembly."),
            _process("qualification", "Qualification", "Approved seed: packaging transitions require qualification."),
        ),
        "technology_process_links": (
            _technology_process("advanced_packaging", "packaging", "REQUIRES_PROCESS", "Advanced packaging requires packaging operations."),
            _technology_process("panel_level_packaging", "assembly", "TECHNOLOGY_ENABLES_PROCESS", "Panel-level packaging enables higher-scale assembly."),
        ),
        "process_dependencies": (
            _process_dependency("assembly", "qualification", "PROCESS_PRECEDES_PROCESS", "Assembly precedes packaging qualification."),
        ),
    },
    "cpo_photonics": {
        "technologies": (
            _technology("co_packaged_optics", "Co-Packaged Optics", "Approved seed catalyst identifies co-packaged optics qualification."),
            _technology("optical_interconnect", "Optical Interconnect", "Approved seed identifies optical interconnect demand."),
        ),
        "processes": (
            _process(
                "optical_testing",
                "Optical Testing",
                "Approved seed: CPO qualification requires optical testing.",
                constraints=(("CPO Qualification", "Approved seed: CPO qualification limits broad adoption."),),
                resolvers=(("COHR", "Approved seed: Coherent optical manufacturing supports CPO process resolution."),),
            ),
            _process("validation", "Validation", "Approved seed: CPO reliability requires validation."),
        ),
        "technology_process_links": (
            _technology_process("co_packaged_optics", "optical_testing", "REQUIRES_PROCESS", "Co-packaged optics requires optical testing."),
            _technology_process("optical_interconnect", "optical_testing", "REQUIRES_PROCESS", "Optical interconnect technology requires optical testing."),
        ),
        "process_dependencies": (
            _process_dependency("optical_testing", "validation", "PROCESS_PRECEDES_PROCESS", "Optical testing precedes CPO validation."),
        ),
    },
    "data_center_cooling": {
        "technologies": (
            _technology("direct_liquid_cooling", "Direct Liquid Cooling", "Approved seed identifies liquid cooling adoption."),
            _technology("immersion_cooling", "Immersion Cooling", "Approved theme aliases include immersion cooling."),
        ),
        "processes": (
            _process(
                "thermal_management",
                "Thermal Management",
                "Approved seed: advanced cooling requires thermal management.",
                constraints=(("Cooling Capacity", "Approved seed: cooling capacity limits AI datacenter density."),),
                resolvers=(("VRT", "Approved seed: Vertiv cooling systems support thermal-management resolution."),),
            ),
            _process("qualification", "Qualification", "Approved seed: cooling architectures require site qualification."),
        ),
        "technology_process_links": (
            _technology_process("direct_liquid_cooling", "thermal_management", "TECHNOLOGY_ENABLES_PROCESS", "Direct liquid cooling enables high-density thermal management."),
            _technology_process("immersion_cooling", "thermal_management", "TECHNOLOGY_ENABLES_PROCESS", "Immersion cooling enables high-density thermal management."),
        ),
        "process_dependencies": (
            _process_dependency("thermal_management", "qualification", "PROCESS_PRECEDES_PROCESS", "Thermal-management design precedes site qualification."),
        ),
    },
    "robotics": {
        "technologies": (
            _technology("machine_vision", "Machine Vision", "Approved seed: robotics model improvement supports machine vision."),
            _technology("motion_control", "Motion Control", "Approved seed: industrial robotics requires motion control."),
        ),
        "processes": (
            _process("assembly", "Assembly", "Approved seed: robotics systems require assembly."),
            _process(
                "calibration",
                "Calibration",
                "Approved seed: robotics deployment requires calibration.",
                constraints=(("Deployment Complexity", "Approved seed: deployment complexity limits robotics calibration and rollout."),),
                resolvers=(("ROK", "Approved seed: Rockwell Automation supports deployment and calibration resolution."),),
            ),
            _process("validation", "Validation", "Approved seed: robotics deployments require site validation."),
        ),
        "technology_process_links": (
            _technology_process("machine_vision", "calibration", "REQUIRES_PROCESS", "Machine vision requires calibration."),
            _technology_process("motion_control", "assembly", "TECHNOLOGY_ENABLES_PROCESS", "Motion control enables robotic assembly."),
        ),
        "process_dependencies": (
            _process_dependency("assembly", "calibration", "PROCESS_PRECEDES_PROCESS", "Assembly precedes robotics calibration."),
            _process_dependency("calibration", "validation", "PROCESS_PRECEDES_PROCESS", "Calibration precedes site validation."),
        ),
    },
    "edge_ai": {
        "technologies": (
            _technology("on_device_inference", "On-Device Inference", "Approved seed identifies on-device AI adoption."),
            _technology("model_compression", "Model Compression", "Approved seed: edge inference depends on compact deployable models."),
        ),
        "processes": (
            _process(
                "validation",
                "Validation",
                "Approved seed: edge-AI software use cases require validation.",
                constraints=(("Software Use Case Maturity", "Approved seed: software use-case maturity limits edge-AI validation."),),
                resolvers=(("AAPL", "Approved seed: Apple's on-device AI ecosystem supports use-case validation."),),
            ),
            _process("qualification", "Qualification", "Approved seed: device AI features require product qualification."),
        ),
        "technology_process_links": (
            _technology_process("on_device_inference", "validation", "REQUIRES_PROCESS", "On-device inference requires use-case validation."),
            _technology_process("model_compression", "qualification", "TECHNOLOGY_ENABLES_PROCESS", "Model compression enables device qualification within resource limits."),
        ),
        "process_dependencies": (
            _process_dependency("validation", "qualification", "PROCESS_PRECEDES_PROCESS", "Use-case validation precedes device qualification."),
        ),
    },
}


TARGET_SEED_THEMES = tuple(
    replace(theme, **_TECHNOLOGY_PROCESS_SEEDS.get(theme.theme_id, {}))
    for theme in TARGET_SEED_THEMES
)


_MATERIAL_CITATION = "Approved curated seed: Phase 12.5 material graph"


def _material(key: str, name: str, category: str) -> SeedMaterial:
    return SeedMaterial(key, name, category, _MATERIAL_CITATION)


def _process_material(
    process: str,
    material: str,
    relationship: str = "PROCESS_REQUIRES_MATERIAL",
) -> SeedProcessMaterialLink:
    return SeedProcessMaterialLink(
        process,
        material,
        relationship,
        _MATERIAL_CITATION,
    )


def _theme_material(material: str) -> SeedThemeMaterialLink:
    return SeedThemeMaterialLink(
        material,
        "THEME_DEPENDS_ON_MATERIAL",
        _MATERIAL_CITATION,
    )


_MATERIAL_SEEDS: dict[str, dict[str, tuple[object, ...]]] = {
    "glass_substrate": {
        "materials": (
            _material("ultra_thin_glass", "Ultra Thin Glass", "Substrate"),
        ),
        "process_material_links": (
            _process_material("glass_processing", "ultra_thin_glass"),
        ),
        "theme_material_links": (
            _theme_material("ultra_thin_glass"),
        ),
        "material_supplier_links": (
            SeedMaterialSupplierLink(
                "ultra_thin_glass",
                "GLW",
                _MATERIAL_CITATION,
            ),
        ),
    },
    "hbm": {
        "materials": (
            _material("photoresist", "Photoresist", "Specialty Chemical"),
            _material("underfill", "Underfill", "Encapsulation Material"),
        ),
        "processes": (
            *_TECHNOLOGY_PROCESS_SEEDS["hbm"]["processes"],
            _process("packaging", "Packaging", _MATERIAL_CITATION),
        ),
        "process_material_links": (
            _process_material("tsv_etching", "photoresist"),
            _process_material("packaging", "underfill"),
        ),
        "theme_material_links": (
            _theme_material("photoresist"),
            _theme_material("underfill"),
        ),
    },
    "data_center_cooling": {
        "materials": (
            _material("coolant", "Coolant", "Thermal Material"),
        ),
        "process_material_links": (
            _process_material("thermal_management", "coolant"),
        ),
        "theme_material_links": (
            _theme_material("coolant"),
        ),
    },
    "cpo_photonics": {
        "materials": (
            _material("optical_polymer", "Optical Polymer", "Optical Material"),
            _material("optical_adhesive", "Optical Adhesive", "Adhesive"),
        ),
        "process_material_links": (
            _process_material("optical_testing", "optical_polymer"),
            _process_material("optical_testing", "optical_adhesive"),
        ),
        "theme_material_links": (
            _theme_material("optical_polymer"),
            _theme_material("optical_adhesive"),
        ),
    },
}


TARGET_SEED_THEMES = tuple(
    replace(theme, **_MATERIAL_SEEDS.get(theme.theme_id, {}))
    for theme in TARGET_SEED_THEMES
)


_EQUIPMENT_CITATION = "Approved curated seed: Phase 12.6 equipment graph"


def _equipment(key: str, name: str, category: str) -> SeedEquipment:
    return SeedEquipment(key, name, category, _EQUIPMENT_CITATION)


def _process_equipment(
    process: str,
    equipment: str,
    relationship: str = "PROCESS_REQUIRES_EQUIPMENT",
) -> SeedProcessEquipmentLink:
    return SeedProcessEquipmentLink(
        process,
        equipment,
        relationship,
        _EQUIPMENT_CITATION,
    )


def _theme_equipment(equipment: str) -> SeedThemeEquipmentLink:
    return SeedThemeEquipmentLink(
        equipment,
        "THEME_DEPENDS_ON_EQUIPMENT",
        _EQUIPMENT_CITATION,
    )


_EQUIPMENT_SEEDS: dict[str, dict[str, tuple[object, ...]]] = {
    "hbm": {
        "equipment": (
            _equipment("advanced_etch", "Advanced Etch", "Etch"),
        ),
        "process_equipment_links": (
            _process_equipment("tsv_etching", "advanced_etch"),
        ),
        "theme_equipment_links": (
            _theme_equipment("advanced_etch"),
        ),
        "equipment_producer_links": (
            SeedEquipmentProducerLink(
                "advanced_etch",
                "AMAT",
                "Applied Materials",
                _EQUIPMENT_CITATION,
            ),
        ),
    },
    "glass_substrate": {
        "equipment": (
            _equipment("yield_inspection", "Yield Inspection", "Inspection"),
        ),
        "process_equipment_links": (
            _process_equipment("glass_processing", "yield_inspection"),
        ),
        "theme_equipment_links": (
            _theme_equipment("yield_inspection"),
        ),
        "equipment_producer_links": (
            SeedEquipmentProducerLink(
                "yield_inspection",
                "KLAC",
                "KLA Corporation",
                _EQUIPMENT_CITATION,
            ),
        ),
    },
    "cpo_photonics": {
        "equipment": (
            _equipment(
                "optical_testing_equipment",
                "Optical Testing Equipment",
                "Optical Equipment",
            ),
        ),
        "process_equipment_links": (
            _process_equipment("optical_testing", "optical_testing_equipment"),
        ),
        "theme_equipment_links": (
            _theme_equipment("optical_testing_equipment"),
        ),
        "equipment_producer_links": (
            SeedEquipmentProducerLink(
                "optical_testing_equipment",
                "TER",
                "Teradyne",
                _EQUIPMENT_CITATION,
            ),
        ),
    },
    "data_center_cooling": {
        "equipment": (
            _equipment(
                "thermal_management_equipment",
                "Thermal Management Equipment",
                "Thermal Equipment",
            ),
        ),
        "process_equipment_links": (
            _process_equipment(
                "thermal_management",
                "thermal_management_equipment",
            ),
        ),
        "theme_equipment_links": (
            _theme_equipment("thermal_management_equipment"),
        ),
    },
    "advanced_packaging": {
        "equipment": (
            _equipment(
                "advanced_packaging_equipment",
                "Advanced Packaging Equipment",
                "Packaging",
            ),
        ),
        "process_equipment_links": (
            _process_equipment("packaging", "advanced_packaging_equipment"),
        ),
        "theme_equipment_links": (
            _theme_equipment("advanced_packaging_equipment"),
        ),
    },
}


TARGET_SEED_THEMES = tuple(
    replace(theme, **_EQUIPMENT_SEEDS.get(theme.theme_id, {}))
    for theme in TARGET_SEED_THEMES
)


_CONSTRAINT_CITATION = "Approved curated seed: Phase 12.7 bottleneck graph"


def _constraint(key: str, name: str, category: str) -> SeedConstraint:
    return SeedConstraint(key, name, category, _CONSTRAINT_CITATION)


def _theme_constraint(key: str) -> SeedThemeConstraintLink:
    return SeedThemeConstraintLink(
        key,
        "THEME_LIMITED_BY_CONSTRAINT",
        _CONSTRAINT_CITATION,
    )


_CONSTRAINT_SEEDS: dict[str, dict[str, tuple[object, ...]]] = {
    "hbm": {
        "constraints": (
            _constraint(
                "hbm_capacity",
                "HBM Capacity Constraint",
                "Capacity Constraint",
            ),
        ),
        "theme_constraint_links": (
            _theme_constraint("hbm_capacity"),
        ),
        "company_constraint_exposure_links": (
            SeedCompanyConstraintExposureLink(
                "000660.KS",
                "SK hynix",
                "hbm_capacity",
                _CONSTRAINT_CITATION,
            ),
            SeedCompanyConstraintExposureLink(
                "MU",
                "Micron Technology",
                "hbm_capacity",
                _CONSTRAINT_CITATION,
            ),
            SeedCompanyConstraintExposureLink(
                "005930.KS",
                "Samsung Electronics",
                "hbm_capacity",
                _CONSTRAINT_CITATION,
            ),
        ),
    },
    "cowos": {
        "constraints": (
            _constraint(
                "cowos_capacity",
                "CoWoS Capacity Constraint",
                "Capacity Constraint",
            ),
        ),
        "theme_constraint_links": (
            _theme_constraint("cowos_capacity"),
        ),
        "constraint_resolver_links": (
            SeedConstraintResolverLink(
                "cowos_capacity",
                "TSM",
                "Taiwan Semiconductor Manufacturing",
                _CONSTRAINT_CITATION,
            ),
        ),
    },
    "glass_substrate": {
        "constraints": (
            _constraint(
                "glass_substrate_yield",
                "Glass Substrate Yield Constraint",
                "Yield Constraint",
            ),
        ),
        "theme_constraint_links": (
            _theme_constraint("glass_substrate_yield"),
        ),
        "constraint_dependencies": (
            SeedConstraintDependencyLink(
                "glass_substrate_yield",
                "Process",
                "glass_processing",
                "CONSTRAINT_DEPENDS_ON_PROCESS",
                _CONSTRAINT_CITATION,
            ),
            SeedConstraintDependencyLink(
                "glass_substrate_yield",
                "Equipment",
                "yield_inspection",
                "CONSTRAINT_DEPENDS_ON_EQUIPMENT",
                _CONSTRAINT_CITATION,
            ),
        ),
    },
    "cpo_photonics": {
        "constraints": (
            _constraint(
                "optical_testing",
                "Optical Testing Bottleneck",
                "Testing Constraint",
            ),
        ),
        "theme_constraint_links": (
            _theme_constraint("optical_testing"),
        ),
        "constraint_dependencies": (
            SeedConstraintDependencyLink(
                "optical_testing",
                "Process",
                "optical_testing",
                "CONSTRAINT_DEPENDS_ON_PROCESS",
                _CONSTRAINT_CITATION,
            ),
            SeedConstraintDependencyLink(
                "optical_testing",
                "Equipment",
                "optical_testing_equipment",
                "CONSTRAINT_DEPENDS_ON_EQUIPMENT",
                _CONSTRAINT_CITATION,
            ),
        ),
    },
    "ai_infrastructure": {
        "constraints": (
            _constraint(
                "data_center_power_availability",
                "Data Center Power Availability Constraint",
                "Power Constraint",
            ),
        ),
        "theme_constraint_links": (
            _theme_constraint("data_center_power_availability"),
        ),
    },
    "data_center_cooling": {
        "constraints": (
            _constraint(
                "thermal_management_capacity",
                "Thermal Management Capacity Constraint",
                "Thermal Constraint",
            ),
        ),
        "theme_constraint_links": (
            _theme_constraint("thermal_management_capacity"),
        ),
        "constraint_dependencies": (
            SeedConstraintDependencyLink(
                "thermal_management_capacity",
                "Process",
                "thermal_management",
                "CONSTRAINT_DEPENDS_ON_PROCESS",
                _CONSTRAINT_CITATION,
            ),
            SeedConstraintDependencyLink(
                "thermal_management_capacity",
                "Equipment",
                "thermal_management_equipment",
                "CONSTRAINT_DEPENDS_ON_EQUIPMENT",
                _CONSTRAINT_CITATION,
            ),
        ),
    },
}


_PROCESS_CONSTRAINT_SEEDS = {
    "glass_substrate": (
        "glass_processing",
        SeedProcessConstraintLink(
            "Glass Substrate Yield Constraint",
            _CONSTRAINT_CITATION,
            constraint_key="glass_substrate_yield",
        ),
    ),
    "cpo_photonics": (
        "optical_testing",
        SeedProcessConstraintLink(
            "Optical Testing Bottleneck",
            _CONSTRAINT_CITATION,
            constraint_key="optical_testing",
        ),
    ),
    "data_center_cooling": (
        "thermal_management",
        SeedProcessConstraintLink(
            "Thermal Management Capacity Constraint",
            _CONSTRAINT_CITATION,
            constraint_key="thermal_management_capacity",
        ),
    ),
}


_EQUIPMENT_CONSTRAINT_SEEDS = {
    "glass_substrate": SeedEquipmentConstraintLink(
        "yield_inspection",
        "Glass Substrate Yield Constraint",
        _CONSTRAINT_CITATION,
        constraint_key="glass_substrate_yield",
    ),
    "cpo_photonics": SeedEquipmentConstraintLink(
        "optical_testing_equipment",
        "Optical Testing Bottleneck",
        _CONSTRAINT_CITATION,
        constraint_key="optical_testing",
    ),
    "data_center_cooling": SeedEquipmentConstraintLink(
        "thermal_management_equipment",
        "Thermal Management Capacity Constraint",
        _CONSTRAINT_CITATION,
        constraint_key="thermal_management_capacity",
    ),
}


def _add_constraint_seeds(theme: ThemeSeed) -> ThemeSeed:
    updates = dict(_CONSTRAINT_SEEDS.get(theme.theme_id, {}))
    process_seed = _PROCESS_CONSTRAINT_SEEDS.get(theme.theme_id)
    if process_seed:
        process_key_value, link = process_seed
        updates["processes"] = tuple(
            replace(
                process,
                constraint_links=(*process.constraint_links, link),
            )
            if process.key == process_key_value
            else process
            for process in theme.processes
        )
    equipment_link = _EQUIPMENT_CONSTRAINT_SEEDS.get(theme.theme_id)
    if equipment_link:
        updates["equipment_constraint_links"] = (
            *theme.equipment_constraint_links,
            equipment_link,
        )
    return replace(theme, **updates) if updates else theme


TARGET_SEED_THEMES = tuple(_add_constraint_seeds(theme) for theme in TARGET_SEED_THEMES)
