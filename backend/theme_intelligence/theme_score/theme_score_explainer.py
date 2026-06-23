from __future__ import annotations

from .theme_score_models import ThemeFinalScore, ThemeScoreInput


class ThemeScoreExplainer:
    def explain(self, result: ThemeFinalScore, score_input: ThemeScoreInput) -> ThemeFinalScore:
        components = result.score_components
        strengths: list[str] = []
        risks: list[str] = []
        allocation_notes: list[str] = []

        if result.ai_potential_score >= 80:
            strengths.append("Strong discovery, catalyst, and beneficiary evidence support elevated AI potential.")
        if score_input.catalyst_strength >= 75:
            strengths.append("Catalyst evidence is broad enough to support continued monitoring.")
        if score_input.beneficiary_quality >= 75:
            strengths.append("Beneficiary quality is supported by allocation and exposure signals.")
        if components.get("lifecycle_opportunity", 0) >= 80:
            strengths.append("Lifecycle positioning suggests room for continued theme development.")

        penalties = components.get("risk_penalties", {})
        if penalties.get("bubble_penalty", 0) >= 45:
            risks.append("Beneficiary bubble risk is elevated and may limit allocation readiness.")
        if penalties.get("crowding_penalty", 0) > 0:
            risks.append("Crowding proxy is above the neutral threshold.")
        if penalties.get("unresolved_bottleneck_penalty", 0) >= 35:
            risks.append("Bottleneck evidence remains material until resolution probability improves.")
        if score_input.lifecycle_stage == "Mature":
            risks.append("Mature lifecycle status can reduce incremental upside despite stable evidence.")

        if result.allocation_readiness >= 70:
            allocation_notes.append("Allocation readiness is supported by beneficiary quality and manageable risk inputs.")
        elif result.allocation_readiness >= 50:
            allocation_notes.append("Allocation readiness is mixed; research priority may be higher than portfolio readiness.")
        else:
            allocation_notes.append("Allocation readiness is constrained by risk, maturity, or beneficiary evidence.")

        result.major_strengths = strengths
        result.major_risks = risks
        result.allocation_notes = allocation_notes
        result.why_high_score = strengths[0] if strengths else ""
        result.why_low_score = risks[0] if risks else ""
        result.conviction_reason = (
            f"{result.conviction_level} reflects a risk-adjusted score of "
            f"{result.risk_adjusted_score} and allocation readiness of {result.allocation_readiness}."
        )
        return result
