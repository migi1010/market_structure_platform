from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.seeds import TARGET_SEED_THEMES, validate_theme_seeds
from theme_intelligence.seeds.theme_seed_models import SeedBeneficiary


def test_seed_validator_rejects_duplicate_aliases_after_normalization() -> None:
    bad = replace(TARGET_SEED_THEMES[0], aliases=["glass substrate", "Glass-Substrate"])

    errors = validate_theme_seeds([bad])

    assert any("duplicate alias" in error for error in errors)


def test_seed_validator_rejects_invalid_types_and_missing_company() -> None:
    bad_beneficiary = replace(TARGET_SEED_THEMES[0].seed_beneficiaries[0], company_name="")
    bad = replace(
        TARGET_SEED_THEMES[0],
        seed_catalysts=[replace(TARGET_SEED_THEMES[0].seed_catalysts[0], catalyst_type="Fake Catalyst")],
        seed_bottlenecks=[replace(TARGET_SEED_THEMES[0].seed_bottlenecks[0], bottleneck_type="Fake Constraint")],
        seed_beneficiaries=[bad_beneficiary],
    )

    errors = validate_theme_seeds([bad])

    assert any("invalid catalyst type" in error for error in errors)
    assert any("invalid bottleneck type" in error for error in errors)
    assert any("beneficiary missing ticker or company" in error for error in errors)


def test_seed_validator_rejects_controller_confused_with_direct_beneficiary_without_rationale() -> None:
    controller = TARGET_SEED_THEMES[0].controllers[0]
    bad = replace(
        TARGET_SEED_THEMES[0],
        seed_beneficiaries=[
            SeedBeneficiary(
                ticker=controller.ticker,
                company_name=controller.company_name,
                beneficiary_type="Direct Beneficiary",
                role="duplicate controller",
            )
        ],
    )

    errors = validate_theme_seeds([bad])

    assert any("controller also listed as direct beneficiary" in error for error in errors)


def test_seed_validator_rejects_mojibake_and_forbidden_score_fields() -> None:
    bad = replace(
        TARGET_SEED_THEMES[0],
        name_zh="嚙?嚙?壞字",
        metadata={"final_ai_score": 99, "portfolio_weight": 0.4},
    )

    errors = validate_theme_seeds([bad])

    assert any("mojibake" in error for error in errors)
    assert any("forbidden seed field" in error for error in errors)
