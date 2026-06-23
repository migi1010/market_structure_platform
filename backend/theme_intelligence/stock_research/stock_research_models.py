from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


FORBIDDEN_FIELD_TOKENS = (
    "buy",
    "sell",
    "hold",
    "target_price",
    "target price",
    "allocation",
    "portfolio_weight",
    "portfolio weight",
    "position_size",
    "position size",
    "price_prediction",
    "price prediction",
    "fair_value",
    "fair value",
    "intrinsic_value",
    "intrinsic value",
    "llm_conviction",
    "llm conviction",
    "generated_recommendation",
    "generated recommendation",
)


class StockResearchValidationError(ValueError):
    pass


def validate_no_forbidden_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            spaced = normalized.replace("_", " ")
            if normalized in FORBIDDEN_FIELD_TOKENS or spaced in FORBIDDEN_FIELD_TOKENS:
                raise StockResearchValidationError(f"Forbidden stock research field at {path}.{key}")
            validate_no_forbidden_fields(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            validate_no_forbidden_fields(item, f"{path}[{index}]")
    elif isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in FORBIDDEN_FIELD_TOKENS:
            raise StockResearchValidationError(f"Forbidden stock research value at {path}")


@dataclass(frozen=True)
class StockResearchRole:
    role_type: str
    role_description: str
    role_importance: float
    evidence_count: int
    evidence_ids: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_type": self.role_type,
            "role_description": self.role_description,
            "role_importance": round(float(self.role_importance), 4),
            "evidence_count": int(self.evidence_count),
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class StockResearchThemeExposure:
    theme_id: str
    theme_name: str
    rank: int | None
    lifecycle: str
    importance: float
    coverage: float
    evidence_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "theme_name": self.theme_name,
            "rank": self.rank,
            "lifecycle": self.lifecycle,
            "importance": round(float(self.importance), 4),
            "coverage": round(float(self.coverage), 4),
            "evidence_count": int(self.evidence_count),
        }


@dataclass(frozen=True)
class StockResearchEvidenceStep:
    step_type: str
    label: str
    source: str
    evidence_ids: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_type": self.step_type,
            "label": self.label,
            "source": self.source,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class StockResearchRelatedCompany:
    ticker: str
    company_name: str
    relationship: str
    evidence_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "relationship": self.relationship,
            "evidence_count": int(self.evidence_count),
        }


@dataclass(frozen=True)
class StockResearchMemo:
    available: bool
    ticker: str
    generated_at: str
    company_header: dict[str, Any]
    supply_chain_roles: tuple[StockResearchRole, ...] = ()
    theme_exposure: tuple[StockResearchThemeExposure, ...] = ()
    investment_thesis: dict[str, list[str]] = field(default_factory=dict)
    evidence_chain: tuple[StockResearchEvidenceStep, ...] = ()
    research_completeness: dict[str, Any] = field(default_factory=dict)
    decision_support: dict[str, Any] = field(default_factory=dict)
    related_companies: dict[str, tuple[StockResearchRelatedCompany, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "available": self.available,
            "ticker": self.ticker,
            "generated_at": self.generated_at,
            "company_header": dict(self.company_header),
            "supply_chain_roles": [row.to_dict() for row in self.supply_chain_roles],
            "theme_exposure": [row.to_dict() for row in self.theme_exposure],
            "investment_thesis": dict(self.investment_thesis),
            "evidence_chain": [row.to_dict() for row in self.evidence_chain],
            "research_completeness": dict(self.research_completeness),
            "decision_support": dict(self.decision_support),
            "related_companies": {
                key: [row.to_dict() for row in rows]
                for key, rows in self.related_companies.items()
            },
        }
        validate_no_forbidden_fields(payload)
        return payload
