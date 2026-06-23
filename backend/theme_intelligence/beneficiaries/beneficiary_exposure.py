from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from theme_intelligence.beneficiaries.beneficiary_classifier import BeneficiaryClassifier
from theme_intelligence.beneficiaries.beneficiary_models import BeneficiaryCandidate
from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeEntity, clamp_score


@dataclass
class _CandidateState:
    theme_name: str
    ticker: str
    company_name: str
    roles: set[str]
    relationship_strengths: list[float]
    base_beneficiary_score: float = 0.0
    is_controller: bool = False
    is_scarcity_beneficiary: bool = False
    catalyst_relevance: float = 0.0
    etf_support: float = 0.0


class BeneficiaryExposureBuilder:
    def __init__(self, classifier: BeneficiaryClassifier | None = None) -> None:
        self.classifier = classifier or BeneficiaryClassifier()

    def build(
        self,
        theme_name: str,
        entities: list[ThemeEntity],
        beneficiaries: list[ThemeBeneficiary],
        bottlenecks: list[BottleneckRecord],
        catalysts: list[CatalystRecord],
    ) -> list[BeneficiaryCandidate]:
        states: dict[str, _CandidateState] = {}
        company_by_ticker = {
            entity.ticker: entity.company
            for entity in entities
            if entity.theme_name == theme_name and entity.entity_type == "company"
        }
        for entity in entities:
            if entity.theme_name != theme_name or not entity.ticker:
                continue
            state = states.setdefault(
                entity.ticker,
                _CandidateState(theme_name, entity.ticker, company_by_ticker.get(entity.ticker, entity.company), set(), []),
            )
            if entity.entity_type == "supply_chain_role":
                state.roles.add(entity.company)
            elif entity.entity_type == "etf":
                state.etf_support = max(state.etf_support, entity.relationship_strength)
            state.relationship_strengths.append(entity.relationship_strength)

        for beneficiary in beneficiaries:
            if beneficiary.theme_name != theme_name:
                continue
            state = states.setdefault(
                beneficiary.ticker,
                _CandidateState(theme_name, beneficiary.ticker, beneficiary.company_name, {"theme_exposure"}, []),
            )
            state.base_beneficiary_score = max(state.base_beneficiary_score, beneficiary.beneficiary_score)
            state.relationship_strengths.append(beneficiary.relationship_strength)

        for bottleneck in bottlenecks:
            if bottleneck.theme_name != theme_name:
                continue
            for controller in bottleneck.controller_entities:
                ticker = str(controller.get("ticker", "")).upper()
                if ticker not in states:
                    continue
                states[ticker].is_controller = True
                states[ticker].roles.add(str(controller.get("role") or "controller"))
                states[ticker].relationship_strengths.append(float(controller.get("relationship_strength", 75.0)))
            for item in bottleneck.beneficiaries:
                ticker = str(item.get("ticker", "")).upper()
                if ticker not in states:
                    continue
                states[ticker].is_scarcity_beneficiary = True
                states[ticker].relationship_strengths.append(float(item.get("relationship_strength", 70.0)))

        catalyst_bonus = self._catalyst_bonus(catalysts, theme_name)
        return [self._candidate(state, catalyst_bonus) for state in states.values()]

    def _candidate(self, state: _CandidateState, catalyst_bonus: float) -> BeneficiaryCandidate:
        primary_role = self._primary_role(state)
        beneficiary_type = self.classifier.classify(state.theme_name, primary_role, state.is_controller)
        relationship = max(state.relationship_strengths or [0.0])
        role_match = self._role_match(primary_role, beneficiary_type)
        mention_presence = max(state.base_beneficiary_score, relationship * 0.75)
        bottleneck_control = 92.0 if state.is_controller else 0.0
        resolution_enablement = 88.0 if beneficiary_type == "Resolution Enabler" else 0.0
        scarcity_benefit = 80.0 if state.is_scarcity_beneficiary else (68.0 if state.is_controller else 35.0)
        operating_leverage = 72.0 if beneficiary_type in {"Direct Beneficiary", "Bottleneck Controller"} else 58.0
        role_purity = 86.0 if beneficiary_type in {"Direct Beneficiary", "Bottleneck Controller", "Resolution Enabler"} else 62.0
        sector_specificity = 78.0 if primary_role not in {"theme_exposure", "networking"} else 55.0
        repeated_linkage = min(100.0, len(state.relationship_strengths) * 22.0)
        return BeneficiaryCandidate(
            theme_name=state.theme_name,
            ticker=state.ticker,
            company_name=state.company_name,
            role=primary_role,
            beneficiary_type=beneficiary_type,
            entity_relationship_strength=clamp_score(relationship),
            mention_presence=clamp_score(mention_presence),
            supply_chain_role_match=role_match,
            catalyst_relevance=clamp_score(catalyst_bonus),
            bottleneck_control=bottleneck_control,
            resolution_enablement=resolution_enablement,
            scarcity_benefit=scarcity_benefit,
            operating_leverage_proxy=operating_leverage,
            theme_role_purity=role_purity,
            sector_specificity=sector_specificity,
            repeated_theme_linkage=clamp_score(repeated_linkage),
            etf_theme_holding_support=clamp_score(state.etf_support),
        )

    @staticmethod
    def _primary_role(state: _CandidateState) -> str:
        priority = (
            "controller",
            "capacity_owner",
            "resolution_enabler",
            "automation_equipment",
            "equipment_supplier",
            "memory",
            "foundry",
            "packaging",
            "substrate_materials",
            "power_generation",
            "data_center_power",
        )
        for role in priority:
            if role in state.roles:
                return role
        return sorted(state.roles)[0] if state.roles else "theme_exposure"

    @staticmethod
    def _role_match(role: str, beneficiary_type: str) -> float:
        if beneficiary_type == "Bottleneck Controller":
            return 92.0
        if beneficiary_type == "Resolution Enabler":
            return 88.0
        if beneficiary_type == "Direct Beneficiary":
            return 84.0
        if beneficiary_type == "Ecosystem Beneficiary":
            return 70.0
        return 58.0

    @staticmethod
    def _catalyst_bonus(catalysts: list[CatalystRecord], theme_name: str) -> float:
        relevant = [item for item in catalysts if item.theme_name == theme_name]
        if not relevant:
            return 0.0
        type_score = {
            "Product Launch": 74.0,
            "CapEx Expansion": 82.0,
            "Technology Breakthrough": 80.0,
            "Customer Adoption": 78.0,
            "Policy / Regulation": 68.0,
        }
        return clamp_score(max(type_score.get(item.catalyst_type, 50.0) for item in relevant))
