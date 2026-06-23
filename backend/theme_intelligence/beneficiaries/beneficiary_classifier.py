from __future__ import annotations


DIRECT_ROLES = {"memory", "foundry", "packaging", "accelerator", "substrate_materials", "power_generation", "data_center_power"}
RESOLUTION_ROLES = {"automation_equipment", "equipment_supplier", "resolution_enabler", "eda_tools"}
ECOSYSTEM_ROLES = {"material_supplier", "substrate_materials", "power_equipment", "reactor_technology"}
INDIRECT_ROLES = {"networking", "theme_exposure", "robotics_platform"}
CONTROLLER_ROLES = {"memory", "foundry", "packaging", "power_generation", "data_center_power", "capacity_owner"}


class BeneficiaryClassifier:
    def classify(self, theme_name: str, role: str, is_controller: bool = False) -> str:
        normalized = role.strip().lower()
        if is_controller:
            return "Bottleneck Controller"
        if normalized in RESOLUTION_ROLES or "equipment" in normalized:
            return "Resolution Enabler"
        if normalized in INDIRECT_ROLES:
            return "Indirect Beneficiary"
        if normalized in ECOSYSTEM_ROLES or "material" in normalized:
            return "Ecosystem Beneficiary"
        if normalized in DIRECT_ROLES:
            return "Direct Beneficiary"
        return "Indirect Beneficiary"
