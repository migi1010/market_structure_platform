from __future__ import annotations

import re


SUPPLY_CHAIN_ROLES = frozenset({
    "Raw Material",
    "Material Supplier",
    "Component Supplier",
    "Equipment Supplier",
    "Technology Provider",
    "Manufacturing",
    "Assembly",
    "Packaging",
    "Testing",
    "Integrator",
    "Infrastructure Provider",
    "Distributor",
    "OEM",
    "End Customer",
})

LEGACY_SUPPLY_CHAIN_ROLE_MAP = {
    "automation": "Technology Provider",
    "capacity_owner": "Manufacturing",
    "cloud": "Infrastructure Provider",
    "components": "Component Supplier",
    "compute": "Technology Provider",
    "datacenter_power": "Infrastructure Provider",
    "devices": "OEM",
    "downstream": "End Customer",
    "electrical": "Infrastructure Provider",
    "electrical_equipment": "Equipment Supplier",
    "equipment": "Equipment Supplier",
    "foundry": "Manufacturing",
    "integrators": "Integrator",
    "manufacturing": "Manufacturing",
    "memory": "Component Supplier",
    "memory_suppliers": "Manufacturing",
    "networking": "Infrastructure Provider",
    "operators": "Infrastructure Provider",
    "optical_components": "Component Supplier",
    "osat": "Packaging",
    "packaging": "Packaging",
    "power_cooling": "Infrastructure Provider",
    "processors": "Component Supplier",
    "substrates": "Material Supplier",
    "switching": "Component Supplier",
    "thermal": "Infrastructure Provider",
    "upstream_materials": "Raw Material",
    "utilities": "Infrastructure Provider",
}


def normalize_legacy_role(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def canonical_supply_chain_role(value: str) -> str:
    normalized = normalize_legacy_role(value)
    try:
        return LEGACY_SUPPLY_CHAIN_ROLE_MAP[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown supply-chain role: {value}") from exc


def supply_chain_role_key(theme_key: str, canonical_role: str) -> str:
    role_key = normalize_legacy_role(canonical_role)
    return f"supply_chain:{normalize_legacy_role(theme_key)}:{role_key}"
