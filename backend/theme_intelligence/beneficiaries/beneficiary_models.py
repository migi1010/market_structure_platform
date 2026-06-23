from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from theme_intelligence.models import clamp_score, utc_now_iso


BENEFICIARY_TYPES: tuple[str, ...] = (
    "Direct Beneficiary",
    "Indirect Beneficiary",
    "Bottleneck Controller",
    "Resolution Enabler",
    "Ecosystem Beneficiary",
)


@dataclass(frozen=True)
class BeneficiaryCandidate:
    theme_name: str
    ticker: str
    company_name: str
    role: str
    beneficiary_type: str
    entity_relationship_strength: float = 0.0
    mention_presence: float = 0.0
    supply_chain_role_match: float = 0.0
    catalyst_relevance: float = 0.0
    bottleneck_control: float = 0.0
    resolution_enablement: float = 0.0
    scarcity_benefit: float = 0.0
    operating_leverage_proxy: float = 0.0
    theme_role_purity: float = 0.0
    sector_specificity: float = 0.0
    repeated_theme_linkage: float = 0.0
    etf_theme_holding_support: float = 0.0

    @property
    def exposure_score(self) -> float:
        return clamp_score(
            self.entity_relationship_strength * 0.35
            + self.mention_presence * 0.20
            + self.supply_chain_role_match * 0.25
            + self.catalyst_relevance * 0.20
        )

    @property
    def leverage_score(self) -> float:
        return clamp_score(
            self.bottleneck_control * 0.30
            + self.resolution_enablement * 0.25
            + self.scarcity_benefit * 0.20
            + self.operating_leverage_proxy * 0.25
        )

    @property
    def dependency_score(self) -> float:
        return clamp_score(
            self.theme_role_purity * 0.40
            + self.sector_specificity * 0.25
            + self.repeated_theme_linkage * 0.20
            + self.etf_theme_holding_support * 0.15
        )


@dataclass(frozen=True)
class BeneficiaryScoreRecord:
    theme_name: str
    ticker: str
    company_name: str
    beneficiary_type: str
    exposure_score: float
    leverage_score: float
    dependency_score: float
    valuation_penalty: float
    bubble_penalty: float
    beneficiary_score: float
    allocation_score: float
    role: str
    updated_at: str = field(default_factory=utc_now_iso)
    allocation_bucket: str = "Watchlist"
    why_benefits: str = ""
    risk_factors: list[str] = field(default_factory=list)
    valuation_notes: list[str] = field(default_factory=list)
    bubble_risk: float = 0.0
    allocation_reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", self.ticker.upper())
        object.__setattr__(self, "exposure_score", clamp_score(self.exposure_score))
        object.__setattr__(self, "leverage_score", clamp_score(self.leverage_score))
        object.__setattr__(self, "dependency_score", clamp_score(self.dependency_score))
        object.__setattr__(self, "valuation_penalty", clamp_score(self.valuation_penalty))
        object.__setattr__(self, "bubble_penalty", clamp_score(self.bubble_penalty))
        object.__setattr__(self, "beneficiary_score", clamp_score(self.beneficiary_score))
        object.__setattr__(self, "allocation_score", clamp_score(self.allocation_score))
        object.__setattr__(self, "bubble_risk", clamp_score(self.bubble_risk))
        object.__setattr__(self, "updated_at", self.updated_at or utc_now_iso())

    def with_updates(self, **updates: Any) -> "BeneficiaryScoreRecord":
        return replace(self, **updates)

    def to_api(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company": self.company_name,
            "company_name": self.company_name,
            "beneficiary_type": self.beneficiary_type,
            "exposure_score": self.exposure_score,
            "leverage_score": self.leverage_score,
            "dependency_score": self.dependency_score,
            "valuation_penalty": self.valuation_penalty,
            "bubble_penalty": self.bubble_penalty,
            "beneficiary_score": self.beneficiary_score,
            "allocation_score": self.allocation_score,
            "allocation_bucket": self.allocation_bucket,
            "role": self.role,
            "why_benefits": self.why_benefits,
            "risk_factors": self.risk_factors,
            "valuation_notes": self.valuation_notes,
            "bubble_risk": self.bubble_risk,
            "allocation_reason": self.allocation_reason,
        }
