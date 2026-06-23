from __future__ import annotations

import requests

from settings import get_settings
from theme_intelligence.models import CollectorItem, utc_now_iso


FILING_COMPANIES: dict[str, str] = {
    "NVDA": "0001045810",
    "INTC": "0000050863",
    "AMD": "0000002488",
    "GLW": "0000024741",
    "TSM": "0001046179",
    "MU": "0000723125",
}


class FilingCollector:
    def __init__(self, companies: dict[str, str] | None = None) -> None:
        self.companies = companies or FILING_COMPANIES

    def collect(self) -> list[CollectorItem]:
        settings = get_settings()
        items: list[CollectorItem] = []
        headers = {"User-Agent": f"{settings.app_name} theme-intelligence contact@example.com"}
        for symbol, cik in self.companies.items():
            try:
                response = requests.get(
                    f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json",
                    headers=headers,
                    timeout=settings.provider_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception:
                continue
            recent = payload.get("filings", {}).get("recent", {}) if isinstance(payload, dict) else {}
            forms = recent.get("form") or []
            dates = recent.get("filingDate") or []
            accession = recent.get("accessionNumber") or []
            for index, form in enumerate(forms[:5]):
                filing_date = str(dates[index]) if index < len(dates) else utc_now_iso()
                accession_number = str(accession[index]) if index < len(accession) else ""
                items.append(
                    CollectorItem(
                        source="sec_filings",
                        symbol=symbol,
                        headline=f"{symbol} filed {form} with SEC; review AI infrastructure, packaging, grid, and robotics disclosures",
                        published_at=filing_date,
                        raw={"form": form, "filing_date": filing_date, "accession_number": accession_number},
                    )
                )
        return items
