from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.supply_chain_taxonomy import (
    LEGACY_SUPPLY_CHAIN_ROLE_MAP,
    SUPPLY_CHAIN_ROLES,
    canonical_supply_chain_role,
)


def test_supply_chain_taxonomy_registers_all_approved_roles() -> None:
    assert SUPPLY_CHAIN_ROLES == frozenset({
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


def test_legacy_role_mapping_is_complete_and_deterministic() -> None:
    assert canonical_supply_chain_role("upstream_materials") == "Raw Material"
    assert canonical_supply_chain_role("memory_suppliers") == "Manufacturing"
    assert canonical_supply_chain_role("equipment") == "Equipment Supplier"
    assert canonical_supply_chain_role("osat") == "Packaging"
    assert canonical_supply_chain_role("power_cooling") == "Infrastructure Provider"
    assert canonical_supply_chain_role("downstream") == "End Customer"
    assert canonical_supply_chain_role("  POWER-COOLING  ") == "Infrastructure Provider"
    assert len(LEGACY_SUPPLY_CHAIN_ROLE_MAP) == 28


def test_unknown_legacy_role_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown supply-chain role"):
        canonical_supply_chain_role("invented_supplier_role")
