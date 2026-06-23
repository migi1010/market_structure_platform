from __future__ import annotations

from theme_intelligence.lifecycle.lifecycle_models import LifecycleExplanation, LifecycleInput, StageDecision


class LifecycleExplainer:
    def explain(self, data: LifecycleInput, decision: StageDecision) -> LifecycleExplanation:
        positives: list[str] = []
        negatives: list[str] = []
        risks: list[str] = []
        triggers: list[str] = []

        if data.emerging_score >= 60:
            positives.append("Mention acceleration is elevated versus the baseline window.")
        elif data.emerging_score < 45:
            negatives.append("Mention acceleration is still limited.")

        if data.catalyst_score >= 55:
            positives.append("Catalyst evidence is visible across recent mentions.")
        elif data.catalyst_score < 35:
            negatives.append("Catalyst confirmation remains weak.")

        if data.entity_strength_score >= 55:
            positives.append("Ticker and beneficiary linkage is strengthening.")
        elif data.entity_strength_score < 40:
            negatives.append("Entity confirmation is still sparse.")

        if data.crowding_proxy >= 70:
            risks.append("Crowding proxy is high, suggesting broad recognition or overextension risk.")
        elif data.crowding_proxy < 45:
            positives.append("Crowding remains low enough for further research.")

        if data.confidence_score < 50:
            risks.append("Lifecycle confidence is limited by incomplete evidence.")
        if decision.stage == "Mature":
            risks.append("Acceleration is lower relative to broad recognition; risk/reward may be less favorable for early positioning.")
        if not risks:
            risks.append("Classification is deterministic and should be monitored as new evidence arrives.")

        triggers.extend(
            [
                "Sustained mention acceleration across multiple independent sources.",
                "New product, capex, policy, or customer adoption catalysts.",
                "More beneficiary tickers and supply-chain roles linked to the theme.",
                "Crowding proxy staying below the next-stage risk threshold.",
            ]
        )

        top_catalysts = self._top_catalysts(data)
        future_catalysts = [item for item in top_catalysts if item.get("timeline_status") == "future"]
        key_blockers = [
            item
            for item in top_catalysts
            if item.get("polarity") == "risk" or "risk" in str(item.get("name", "")).lower() or "shortage" in str(item.get("type", "")).lower()
        ]
        if future_catalysts:
            triggers.insert(0, f"Monitor {future_catalysts[0].get('name')} for confirmation of the next stage.")
        if key_blockers:
            risks.insert(0, f"{key_blockers[0].get('name')} remains a blocker to monitor.")

        primary_bottleneck = self._primary_bottleneck(data)
        bottleneck_risks = self._bottleneck_risks(data)
        if primary_bottleneck:
            name = str(primary_bottleneck.get("name", "Primary bottleneck"))
            risks.insert(0, f"{name} remains a scaling constraint to monitor.")
            fixes = primary_bottleneck.get("what_fixes_it") or []
            if isinstance(fixes, list) and fixes:
                triggers.insert(0, f"{fixes[0]} would improve next-stage evidence for {name}.")
        top_beneficiaries = self._top_beneficiaries(data)
        if top_beneficiaries:
            top = top_beneficiaries[0]
            positives.append(f"{top.get('ticker')} is a leading mapped beneficiary by allocation attractiveness.")
            if float(top.get("bubble_penalty", 0.0)) >= 35:
                risks.append(f"{top.get('ticker')} has elevated bubble or valuation risk in beneficiary scoring.")

        reason = self._reason(data.theme_name, decision)
        return LifecycleExplanation(
            reason,
            positives,
            negatives,
            risks,
            triggers,
            top_catalysts,
            future_catalysts,
            key_blockers,
            primary_bottleneck,
            bottleneck_risks,
            top_beneficiaries,
        )

    @staticmethod
    def _reason(theme_name: str, decision: StageDecision) -> str:
        evidence = "; ".join(decision.matched_rules) if decision.matched_rules else "available score evidence"
        return f"{theme_name} is classified as {decision.stage} based on {evidence}."

    @staticmethod
    def _top_catalysts(data: LifecycleInput) -> list[dict]:
        return sorted(
            [item for item in data.key_catalysts if isinstance(item, dict)],
            key=lambda item: float(item.get("catalyst_strength") or item.get("impact_score") or 0.0),
            reverse=True,
        )[:5]

    @staticmethod
    def _primary_bottleneck(data: LifecycleInput) -> dict | None:
        rows = LifecycleExplainer._bottleneck_risks(data)
        return rows[0] if rows else None

    @staticmethod
    def _bottleneck_risks(data: LifecycleInput) -> list[dict]:
        return sorted(
            [item for item in data.key_bottlenecks if isinstance(item, dict)],
            key=lambda item: float(item.get("bottleneck_strength") or item.get("severity_score") or 0.0),
            reverse=True,
        )[:5]

    @staticmethod
    def _top_beneficiaries(data: LifecycleInput) -> list[dict]:
        source = data.top_beneficiaries or data.beneficiaries
        return sorted(
            [item for item in source if isinstance(item, dict)],
            key=lambda item: float(item.get("allocation_score") or item.get("beneficiary_score") or 0.0),
            reverse=True,
        )[:5]
