from __future__ import annotations

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.models import ThemeBeneficiary, ThemeEntity, clamp_score


CONTROLLER_ROLE_BY_TYPE: dict[str, set[str]] = {
    "Capacity Constraint": {"memory", "foundry", "packaging", "capacity_owner", "power_generation", "data_center_power"},
    "Yield Constraint": {"packaging", "substrate_materials", "automation_equipment", "resolution_enabler"},
    "Material Constraint": {"substrate_materials", "material_supplier"},
    "Equipment Constraint": {"automation_equipment", "equipment_supplier"},
    "Talent Constraint": {"engineering", "resolution_enabler"},
    "Infrastructure Constraint": {"power_equipment", "data_center_power", "power_generation", "capacity_owner"},
    "Supply Chain Constraint": {"memory", "foundry", "packaging", "material_supplier", "capacity_owner"},
    "Regulatory Constraint": {"power_generation", "foundry", "memory", "resolution_enabler"},
}


class BottleneckResolver:
    def resolve(
        self,
        record: BottleneckRecord,
        entities: list[ThemeEntity],
        beneficiaries: list[ThemeBeneficiary],
    ) -> BottleneckRecord:
        theme_entities = [item for item in entities if item.theme_name == record.theme_name]
        company_by_ticker = {
            item.ticker: item.company
            for item in theme_entities
            if item.entity_type == "company" and item.ticker
        }
        controller_roles = CONTROLLER_ROLE_BY_TYPE.get(record.bottleneck_type, set())
        controllers: list[dict] = []
        seen_controller_tickers: set[str] = set()
        for item in theme_entities:
            role = item.company
            if item.entity_type != "supply_chain_role" or role not in controller_roles or item.ticker in seen_controller_tickers:
                continue
            seen_controller_tickers.add(item.ticker)
            controllers.append(
                {
                    "ticker": item.ticker,
                    "company_name": company_by_ticker.get(item.ticker, item.ticker),
                    "role": self._controller_role(record.bottleneck_type, role),
                    "relationship_strength": clamp_score(item.relationship_strength),
                }
            )

        beneficiary_rows = [
            {
                "ticker": item.ticker,
                "company_name": item.company_name,
                "role": "beneficiary",
                "beneficiary_score": clamp_score(item.beneficiary_score),
                "relationship_strength": clamp_score(item.relationship_strength),
            }
            for item in beneficiaries
            if item.theme_name == record.theme_name and item.ticker not in seen_controller_tickers
        ]
        return record.with_updates(controller_entities=controllers[:8], beneficiaries=beneficiary_rows[:8])

    @staticmethod
    def _controller_role(bottleneck_type: str, role: str) -> str:
        if bottleneck_type == "Equipment Constraint":
            return "equipment_supplier"
        if bottleneck_type == "Material Constraint":
            return "material_supplier"
        if bottleneck_type in {"Capacity Constraint", "Infrastructure Constraint"}:
            return "capacity_owner"
        if bottleneck_type in {"Yield Constraint", "Regulatory Constraint"}:
            return "resolution_enabler"
        return "controller"
