from __future__ import annotations

from collections import defaultdict

from .portfolio_models import DiversificationResult, LIFECYCLE_TARGETS, PortfolioAllocation, PortfolioThemeCandidate, round_score


class PortfolioDiversifier:
    def evaluate(
        self,
        allocations: list[PortfolioAllocation],
        candidates: list[PortfolioThemeCandidate],
        portfolio_type: str,
    ) -> DiversificationResult:
        candidate_map = {row.theme_id: row for row in candidates}
        lifecycle_mix = self.lifecycle_mix(allocations, candidates)
        lifecycle_balance = self.lifecycle_balance_score(lifecycle_mix, portfolio_type)
        theme_count_penalty = max(0.0, 5 - len(allocations)) * 7.0
        lifecycle_concentration_penalty = max(0.0, max(lifecycle_mix.values() or [0.0]) - 50.0) * 0.45
        bottleneck_penalty, bottleneck_notes = self._overlap_penalty(allocations, candidate_map, "bottleneck")
        beneficiary_penalty, beneficiary_notes = self._overlap_penalty(allocations, candidate_map, "beneficiary")
        max_weight_penalty = max(0.0, max((row.weight for row in allocations), default=0.0) - 35.0) * 0.85
        diversification_score = round_score(
            100.0
            - theme_count_penalty
            - lifecycle_concentration_penalty
            - bottleneck_penalty
            - beneficiary_penalty
            - max_weight_penalty
        )
        notes = []
        if theme_count_penalty:
            notes.append("Portfolio has fewer than five themes, reducing diversification.")
        if lifecycle_concentration_penalty:
            notes.append("Lifecycle exposure is concentrated in one stage.")
        notes.extend(bottleneck_notes)
        notes.extend(beneficiary_notes)
        if max_weight_penalty:
            notes.append("Single-theme weight exceeds the default concentration threshold.")
        return DiversificationResult(
            diversification_score=diversification_score,
            lifecycle_mix=lifecycle_mix,
            lifecycle_balance=lifecycle_balance,
            bottleneck_overlap_penalty=round_score(bottleneck_penalty),
            beneficiary_overlap_penalty=round_score(beneficiary_penalty),
            diversification_notes=notes,
        )

    def lifecycle_mix(self, allocations: list[PortfolioAllocation], candidates: list[PortfolioThemeCandidate]) -> dict[str, float]:
        candidate_map = {row.theme_id: row for row in candidates}
        candidate_name_map = {row.theme_name: row for row in candidates}
        mix = {"Seed": 0.0, "Early": 0.0, "Growth": 0.0, "Expansion": 0.0, "Mature": 0.0}
        for allocation in allocations:
            candidate = candidate_map.get(allocation.theme_id) or candidate_name_map.get(allocation.theme)
            if candidate is None:
                continue
            stage = candidate.lifecycle_stage if candidate.lifecycle_stage in mix else "Seed"
            mix[stage] += allocation.weight
        return {key: round(value, 2) for key, value in mix.items()}

    def lifecycle_balance_score(self, lifecycle_mix: dict[str, float], portfolio_type: str) -> float:
        target = LIFECYCLE_TARGETS.get(portfolio_type, LIFECYCLE_TARGETS["balanced_growth"])
        deviation = sum(abs(lifecycle_mix.get(stage, 0.0) - target.get(stage, 0.0)) for stage in {"Seed", "Early", "Growth", "Expansion", "Mature"})
        return round_score(100.0 - deviation * 0.5)

    @staticmethod
    def _overlap_penalty(
        allocations: list[PortfolioAllocation],
        candidate_map: dict[str, PortfolioThemeCandidate],
        overlap_type: str,
    ) -> tuple[float, list[str]]:
        grouped: dict[str, float] = defaultdict(float)
        for allocation in allocations:
            candidate = candidate_map.get(allocation.theme_id)
            if candidate is None:
                continue
            keys = candidate.bottleneck_overlap_keys if overlap_type == "bottleneck" else candidate.beneficiary_overlap_keys
            for key in {item for item in keys if item}:
                grouped[key] += allocation.weight
        if not grouped:
            return 0.0, []
        threshold = 45.0 if overlap_type == "bottleneck" else 40.0
        label = "bottleneck/controller" if overlap_type == "bottleneck" else "beneficiary"
        penalty = 0.0
        notes: list[str] = []
        for key, weight in grouped.items():
            excess = max(0.0, weight - threshold)
            if excess:
                penalty += excess * 0.60
                notes.append(f"Shared {label} overlap {key} represents {weight:.0f}% of portfolio weight.")
        return penalty, notes
