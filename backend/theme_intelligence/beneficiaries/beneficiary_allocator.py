from __future__ import annotations

from theme_intelligence.beneficiaries.beneficiary_models import BeneficiaryScoreRecord


class BeneficiaryAllocator:
    def bucket(self, record: BeneficiaryScoreRecord) -> str:
        if record.bubble_penalty >= 70 or record.allocation_score < 40:
            return "Avoid"
        if record.allocation_score >= 80 and record.bubble_penalty < 35:
            return "High Conviction"
        if record.allocation_score >= 65:
            return "Medium Conviction"
        if record.allocation_score >= 50 or (record.exposure_score >= 75 and record.bubble_penalty >= 35):
            return "Watchlist"
        return "Avoid"

    def reason(self, record: BeneficiaryScoreRecord) -> str:
        return (
            f"{record.ticker} is placed in the {record.allocation_bucket} research bucket based on "
            f"theme exposure {record.exposure_score}, leverage {record.leverage_score}, "
            f"and bubble risk {record.bubble_risk}."
        )
