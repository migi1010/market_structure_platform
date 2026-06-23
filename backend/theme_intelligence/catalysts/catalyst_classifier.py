from __future__ import annotations

import re

from theme_intelligence.catalysts.catalyst_models import CatalystEvent
from theme_intelligence.models import clamp_score, utc_now_iso


TYPE_RULES: tuple[tuple[str, tuple[str, ...], int], ...] = (
    ("Product Launch", ("product launch", "launch", "blackwell", "hbm4", "hbm3e", "mi400", "new platform", "ramp"), 78),
    ("CapEx Expansion", ("capex", "capital expenditure", "investment", "expansion", "capacity increase", "capacity expansion"), 82),
    ("Earnings Call Signal", ("earnings call", "conference call", "management commentary", "guidance", "raises guidance"), 70),
    ("Supply Shortage", ("supply shortage", "shortage", "tight supply", "capacity constraint", "bottleneck", "power shortage"), 76),
    ("Technology Breakthrough", ("breakthrough", "yield improvement", "new packaging process", "glass substrate yield", "silicon photonics"), 80),
    ("Customer Adoption", ("customer adoption", "adoption", "design win", "deployment", "hyperscaler", "apple", "nvidia adoption", "customer demand"), 77),
    ("Policy / Regulation", ("policy", "regulation", "government", "subsidy", "tax credit", "infrastructure spending"), 72),
    ("Industry Demand", ("industry demand", "ai server demand", "robot demand", "datacenter demand", "data center demand", "transformer orders"), 74),
)

SOURCE_CONFIDENCE: dict[str, float] = {
    "sec_filings": 88.0,
    "sec": 86.0,
    "finnhub": 78.0,
    "fmp": 76.0,
    "etf_holdings": 70.0,
    "market": 64.0,
}


class CatalystClassifier:
    def classify(
        self,
        theme_name: str,
        headline: str,
        source: str,
        symbol: str | None = None,
        sentiment: float = 50.0,
        created_at: str | None = None,
    ) -> CatalystEvent:
        catalyst_type, base = self._type_for(headline)
        name = self._name_for(catalyst_type, headline, symbol)
        impact = clamp_score(base + self._specificity_bonus(headline) + abs(clamp_score(sentiment, 50.0) - 50.0) * 0.25)
        confidence = clamp_score(SOURCE_CONFIDENCE.get(source, 60.0) + self._specificity_bonus(headline) * 0.5)
        polarity = "risk" if catalyst_type == "Supply Shortage" or any(term in headline.lower() for term in ("risk", "delay", "blocker", "constraint")) else "positive"
        timestamp = created_at or utc_now_iso()
        return CatalystEvent(
            theme_name=theme_name,
            catalyst_name=name,
            catalyst_type=catalyst_type,
            source=source,
            description=self._description(catalyst_type, headline),
            impact_score=impact,
            confidence_score=confidence,
            created_at=timestamp,
            updated_at=timestamp,
            polarity=polarity,
        )

    @staticmethod
    def _type_for(headline: str) -> tuple[str, int]:
        lower = headline.lower()
        for catalyst_type, terms, base in TYPE_RULES:
            if any(term in lower for term in terms):
                return catalyst_type, base
        return "Industry Demand", 58

    @staticmethod
    def _specificity_bonus(headline: str) -> float:
        lower = headline.lower()
        bonus = 0.0
        for term in ("nvidia", "intel", "tsmc", "micron", "apple", "hyperscaler", "hbm4", "blackwell", "glass substrate"):
            if term in lower:
                bonus += 3.0
        return min(12.0, bonus)

    @staticmethod
    def _name_for(catalyst_type: str, headline: str, symbol: str | None) -> str:
        lower = headline.lower()
        entity = ""
        for key, label in (("nvidia", "NVIDIA"), ("intel", "Intel"), ("tsmc", "TSMC"), ("micron", "Micron"), ("apple", "Apple"), ("hyperscaler", "Hyperscaler")):
            if key in lower:
                entity = label
                break
        if not entity and symbol:
            entity = symbol.upper()
        suffix = {
            "Product Launch": "Product Launch",
            "CapEx Expansion": "Packaging Expansion" if any(term in lower for term in ("packaging", "substrate")) else "CapEx Expansion",
            "Earnings Call Signal": "Earnings Call Signal",
            "Supply Shortage": "Supply Shortage",
            "Technology Breakthrough": "Technology Breakthrough",
            "Customer Adoption": "Customer Adoption",
            "Policy / Regulation": "Policy Support",
            "Industry Demand": "Industry Demand",
        }[catalyst_type]
        return f"{entity} {suffix}".strip()

    @staticmethod
    def _description(catalyst_type: str, headline: str) -> str:
        compact = re.sub(r"\s+", " ", headline).strip()
        return f"{catalyst_type} evidence from mention: {compact[:180]}"
