from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.beneficiaries.beneficiary_classifier import BeneficiaryClassifier


def test_beneficiary_classifier_maps_supply_chain_roles() -> None:
    classifier = BeneficiaryClassifier()

    assert classifier.classify("HBM", "memory", is_controller=False) == "Direct Beneficiary"
    assert classifier.classify("CoWoS", "foundry", is_controller=True) == "Bottleneck Controller"
    assert classifier.classify("Glass Substrate", "automation_equipment", is_controller=False) == "Resolution Enabler"
    assert classifier.classify("Glass Substrate", "substrate_materials", is_controller=False) == "Ecosystem Beneficiary"
    assert classifier.classify("Power Grid", "power_generation", is_controller=True) == "Bottleneck Controller"
    assert classifier.classify("AI Infrastructure", "networking", is_controller=False) == "Indirect Beneficiary"


def test_controller_is_not_classified_as_ordinary_beneficiary() -> None:
    classifier = BeneficiaryClassifier()

    result = classifier.classify("HBM", "memory", is_controller=True)

    assert result == "Bottleneck Controller"
    assert result != "Direct Beneficiary"

