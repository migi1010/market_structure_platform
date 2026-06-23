from __future__ import annotations

import re

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.models import clamp_score, utc_now_iso


TYPE_RULES: tuple[tuple[str, tuple[str, ...], str, float], ...] = (
    ("Yield Constraint", ("yield", "scrap", "qualification", "defect", "process maturity"), "Yield", 84),
    ("Material Constraint", ("material", "chemicals", "glass materials", "rare earth", "substrate material"), "Material Availability", 74),
    ("Equipment Constraint", ("equipment", "tool", "euv", "inspection", "packaging equipment"), "Equipment Availability", 76),
    ("Talent Constraint", ("talent", "engineer", "engineers", "hiring", "labor", "skilled"), "Talent Availability", 68),
    ("Infrastructure Constraint", ("power grid", "cooling", "datacenter availability", "data center availability", "power shortage", "infrastructure"), "Infrastructure Availability", 82),
    ("Supply Chain Constraint", ("single supplier", "supplier dependency", "geographic concentration", "concentration risk", "second source"), "Supply Chain Concentration", 72),
    ("Regulatory Constraint", ("export control", "policy restriction", "regulation", "license", "restriction"), "Regulatory Restriction", 70),
    ("Capacity Constraint", ("capacity", "tight supply", "lead time", "shortage", "utilization", "availability"), "Capacity", 78),
)

SOURCE_CONFIDENCE: dict[str, float] = {
    "sec_filings": 86.0,
    "sec": 84.0,
    "finnhub": 74.0,
    "fmp": 72.0,
    "etf_holdings": 64.0,
    "market": 58.0,
}


class BottleneckClassifier:
    def classify(
        self,
        theme_name: str,
        text: str,
        source: str,
        symbol: str | None = None,
        updated_at: str | None = None,
    ) -> BottleneckRecord:
        bottleneck_type, base_name, base_severity = self._type_for(text)
        name = self._name_for(theme_name, bottleneck_type, base_name, text, symbol)
        keyword_severity = clamp_score(base_severity + self._specificity_bonus(text))
        source_confidence = SOURCE_CONFIDENCE.get(source, 60.0)
        severity = clamp_score(keyword_severity * 0.70 + source_confidence * 0.30)
        timestamp = updated_at or utc_now_iso()
        return BottleneckRecord(
            theme_name=theme_name,
            bottleneck_name=name,
            bottleneck_type=bottleneck_type,
            severity_score=severity,
            duration_score=0.0,
            resolution_probability=0.0,
            impact_score=0.0,
            bottleneck_strength=0.0,
            timeline_status="current",
            description=self._description(bottleneck_type, text),
            evidence=[{"source": source, "symbol": symbol, "text": re.sub(r"\s+", " ", text).strip()[:240]}],
            updated_at=timestamp,
        )

    @staticmethod
    def _type_for(text: str) -> tuple[str, str, float]:
        lower = text.lower()
        for bottleneck_type, terms, base_name, severity in TYPE_RULES:
            if any(term in lower for term in terms):
                return bottleneck_type, base_name, severity
        return "Supply Chain Constraint", "Supply Chain Constraint", 55.0

    @staticmethod
    def _specificity_bonus(text: str) -> float:
        lower = text.lower()
        bonus = 0.0
        for term in ("hbm", "cowos", "glass substrate", "power grid", "cooling", "euv", "rare earth", "single supplier"):
            if term in lower:
                bonus += 3.0
        return min(12.0, bonus)

    @staticmethod
    def _name_for(theme_name: str, bottleneck_type: str, base_name: str, text: str, symbol: str | None) -> str:
        lower = text.lower()
        if bottleneck_type == "Capacity Constraint":
            if "hbm" in lower:
                return "HBM Capacity"
            if "cowos" in lower:
                return "CoWoS Capacity"
            if symbol:
                return f"{symbol.upper()} Capacity"
        if bottleneck_type == "Yield Constraint":
            return "Yield"
        if bottleneck_type == "Infrastructure Constraint":
            if "power" in lower:
                return "Power Grid"
            if "cooling" in lower:
                return "Cooling"
        if bottleneck_type == "Equipment Constraint" and "packaging" in lower:
            return "Packaging Equipment"
        if bottleneck_type == "Material Constraint" and "glass" in lower:
            return "Glass Materials"
        if theme_name == "Glass Substrate" and bottleneck_type == "Capacity Constraint":
            return "Production Capacity"
        return base_name

    @staticmethod
    def _description(bottleneck_type: str, text: str) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        return f"{bottleneck_type} evidence from mention: {compact[:180]}"
