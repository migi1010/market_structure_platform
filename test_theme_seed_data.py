from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.seeds import TARGET_SEED_THEMES, validate_theme_seeds


def test_target_seed_themes_cover_phase_10_10_list() -> None:
    names = {theme.name for theme in TARGET_SEED_THEMES}

    assert names == {
        "Glass Substrate",
        "HBM",
        "CoWoS",
        "AI Infrastructure",
        "Advanced Packaging",
        "Power Grid",
        "CPO Photonics",
        "Robotics",
        "Edge AI",
        "Data Center Cooling",
    }


def test_seed_themes_have_required_coverage_and_clean_labels() -> None:
    errors = validate_theme_seeds(TARGET_SEED_THEMES)

    assert errors == []
    for theme in TARGET_SEED_THEMES:
        assert theme.theme_id
        assert theme.name
        assert theme.name_zh
        assert len(theme.aliases) >= 4
        assert theme.supply_chain_roles
        assert theme.seed_catalysts
        assert theme.seed_bottlenecks
        assert theme.seed_beneficiaries
        assert theme.controllers
        assert theme.resolution_enablers
        assert theme.lifecycle_hint.stage
        assert theme.risk_notes
