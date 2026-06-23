from __future__ import annotations

from theme_intelligence.discovery.discovery_models import DiscoveryBrief
from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeMention
from theme_intelligence.scoring.emerging_score import EmergingScoreResult


class BriefGenerator:
    def build(
        self,
        theme_name: str,
        emerging: EmergingScoreResult,
        catalysts: list[CatalystRecord],
        beneficiaries: list[ThemeBeneficiary],
        crowding_proxy: float,
    ) -> DiscoveryBrief:
        why_now = (
            f"{theme_name} is showing a recent attention pickup versus its baseline window."
            if emerging.score >= 60
            else f"{theme_name} has early evidence, but acceleration is not broadly confirmed yet."
        )
        signals = [
            f"{emerging.recent_count} recent mentions versus {emerging.baseline_count} baseline mentions.",
            f"{emerging.unique_sources} independent source types observed in the recent window.",
        ]
        if catalysts:
            signals.append(f"{len(catalysts[:5])} catalyst records are linked to the theme.")
        if beneficiaries:
            signals.append(f"{len(beneficiaries[:5])} beneficiary candidates have mapped relationships.")

        risks = []
        if emerging.unique_sources <= 1:
            risks.append("Source diversity is still limited; confirmation may be fragile.")
        if crowding_proxy >= 35:
            risks.append("Crowding proxy is elevated, so the theme may already be partially recognized.")
        if not catalysts:
            risks.append("No high-confidence catalyst has been classified yet.")
        if not risks:
            risks.append("Evidence is constructive, but market pricing and execution risk still need monitoring.")

        watch_triggers = [
            "New product launch or customer adoption mentions.",
            "Earnings call language confirming demand or capacity expansion.",
            "ETF holding changes or new beneficiary tickers linked to the theme.",
            "Supply shortage, policy, or technology breakthrough catalysts.",
        ]
        return DiscoveryBrief(why_now, signals, risks, watch_triggers)
