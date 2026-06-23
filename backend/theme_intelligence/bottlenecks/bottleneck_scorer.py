from __future__ import annotations

from statistics import mean

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.models import clamp_score


DURATION_PRIORS: dict[str, float] = {
    "Capacity Constraint": 82.0,
    "Yield Constraint": 88.0,
    "Material Constraint": 76.0,
    "Equipment Constraint": 80.0,
    "Talent Constraint": 72.0,
    "Infrastructure Constraint": 86.0,
    "Supply Chain Constraint": 78.0,
    "Regulatory Constraint": 68.0,
}

TECHNICAL_DIFFICULTY: dict[str, float] = {
    "Capacity Constraint": 52.0,
    "Yield Constraint": 76.0,
    "Material Constraint": 55.0,
    "Equipment Constraint": 58.0,
    "Talent Constraint": 45.0,
    "Infrastructure Constraint": 70.0,
    "Supply Chain Constraint": 60.0,
    "Regulatory Constraint": 64.0,
}

THEME_DEPENDENCY: dict[str, dict[str, float]] = {
    "AI Infrastructure": {"Capacity Constraint": 86, "Infrastructure Constraint": 92, "Equipment Constraint": 72},
    "Glass Substrate": {"Yield Constraint": 95, "Equipment Constraint": 84, "Material Constraint": 78, "Capacity Constraint": 80},
    "HBM": {"Capacity Constraint": 94, "Equipment Constraint": 76, "Supply Chain Constraint": 74},
    "CoWoS": {"Capacity Constraint": 90, "Yield Constraint": 82, "Equipment Constraint": 80},
    "Humanoid Robot": {"Equipment Constraint": 82, "Material Constraint": 72, "Talent Constraint": 66},
    "Robotics": {"Equipment Constraint": 76, "Material Constraint": 68, "Talent Constraint": 62},
}


class BottleneckScorer:
    def score(self, record: BottleneckRecord) -> BottleneckRecord:
        severity = clamp_score(record.severity_score)
        duration = clamp_score(record.duration_score or self._duration(record))
        resolution = clamp_score(record.resolution_probability or self._resolution_probability(record))
        impact = clamp_score(record.impact_score or self._impact(record))
        strength = clamp_score(severity * 0.35 + duration * 0.25 + impact * 0.25 + (100.0 - resolution) * 0.15)
        return record.with_updates(
            severity_score=severity,
            duration_score=duration,
            resolution_probability=resolution,
            impact_score=impact,
            bottleneck_strength=strength,
        )

    def score_many(self, records: list[BottleneckRecord]) -> list[BottleneckRecord]:
        return [self.score(record) for record in records]

    def _duration(self, record: BottleneckRecord) -> float:
        bottleneck_type_prior = DURATION_PRIORS.get(record.bottleneck_type, 60.0)
        capex_or_yield_cycle_length = 85.0 if record.bottleneck_type in {"Capacity Constraint", "Yield Constraint", "Infrastructure Constraint"} else 58.0
        repeated_mentions = min(100.0, len(record.evidence) * 22.0)
        return clamp_score(bottleneck_type_prior * 0.45 + capex_or_yield_cycle_length * 0.35 + repeated_mentions * 0.20)

    def _resolution_probability(self, record: BottleneckRecord) -> float:
        evidence_text = " ".join(str(item.get("text", "")) for item in record.evidence).lower()
        improvement_catalysts = 78.0 if any(term in evidence_text for term in ("improve", "relief", "expansion", "qualify", "second source")) else 35.0
        controller_capacity_expansion = 72.0 if any(term in evidence_text for term in ("capacity expansion", "capex", "investment", "ramp")) else 38.0
        policy_or_supply_relief = 70.0 if any(term in evidence_text for term in ("subsidy", "policy", "license", "relief")) else 32.0
        technical_difficulty = TECHNICAL_DIFFICULTY.get(record.bottleneck_type, 55.0)
        return clamp_score(
            improvement_catalysts * 0.35
            + controller_capacity_expansion * 0.30
            + policy_or_supply_relief * 0.20
            - technical_difficulty * 0.15
        )

    def _impact(self, record: BottleneckRecord) -> float:
        theme_dependency = THEME_DEPENDENCY.get(record.theme_name, {}).get(record.bottleneck_type, 62.0)
        beneficiary_link_strength = mean([float(item.get("relationship_strength", 0.0)) for item in record.beneficiaries]) if record.beneficiaries else 35.0
        evidence_text = " ".join(str(item.get("text", "")) for item in record.evidence).lower()
        catalyst_interaction = 78.0 if any(term in evidence_text for term in ("shortage", "limits", "constraint", "bottleneck", "yield")) else 45.0
        lifecycle_relevance = 82.0 if record.bottleneck_type in {"Yield Constraint", "Capacity Constraint", "Infrastructure Constraint"} else 58.0
        return clamp_score(theme_dependency * 0.45 + beneficiary_link_strength * 0.25 + catalyst_interaction * 0.20 + lifecycle_relevance * 0.10)
