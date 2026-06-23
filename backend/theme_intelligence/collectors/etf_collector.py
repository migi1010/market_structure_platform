from __future__ import annotations

import requests

from settings import get_settings
from theme_intelligence.models import CollectorItem, ThemeBeneficiary, ThemeEntity, utc_now_iso


ETF_SYMBOLS: tuple[str, ...] = ("SMH", "SOXX", "BOTZ", "ROBO", "ARKQ")

ETF_THEME_HINTS: dict[str, tuple[str, ...]] = {
    "SMH": ("HBM", "CoWoS", "Advanced Packaging", "AI Infrastructure", "Glass Substrate"),
    "SOXX": ("HBM", "CoWoS", "Advanced Packaging", "Optical Interconnect"),
    "BOTZ": ("Robotics", "Humanoid Robot", "AI Infrastructure"),
    "ROBO": ("Robotics", "Humanoid Robot"),
    "ARKQ": ("Robotics", "Humanoid Robot", "Satellite", "AI Infrastructure"),
}

STATIC_HOLDINGS: dict[str, tuple[tuple[str, str], ...]] = {
    "SMH": (("NVDA", "NVIDIA Corporation"), ("TSM", "Taiwan Semiconductor Manufacturing"), ("AVGO", "Broadcom Inc."), ("ASML", "ASML Holding"), ("AMD", "Advanced Micro Devices")),
    "SOXX": (("NVDA", "NVIDIA Corporation"), ("AVGO", "Broadcom Inc."), ("AMD", "Advanced Micro Devices"), ("QCOM", "Qualcomm"), ("AMAT", "Applied Materials")),
    "BOTZ": (("NVDA", "NVIDIA Corporation"), ("ISRG", "Intuitive Surgical"), ("TER", "Teradyne"), ("ROK", "Rockwell Automation"), ("ABBNY", "ABB Ltd.")),
    "ROBO": (("ISRG", "Intuitive Surgical"), ("TER", "Teradyne"), ("ROK", "Rockwell Automation"), ("ZBRA", "Zebra Technologies"), ("SYM", "Symbotic Inc.")),
    "ARKQ": (("TSLA", "Tesla Inc."), ("TER", "Teradyne"), ("KTOS", "Kratos Defense"), ("TRMB", "Trimble Inc."), ("IRDM", "Iridium Communications")),
}


class ETFCollector:
    def __init__(self, symbols: tuple[str, ...] = ETF_SYMBOLS) -> None:
        self.symbols = symbols

    def collect(self) -> list[CollectorItem]:
        items: list[CollectorItem] = []
        for symbol in self.symbols:
            holdings = self._holdings(symbol)
            names = ", ".join(ticker for ticker, _ in holdings[:5])
            themes = ", ".join(ETF_THEME_HINTS.get(symbol, ()))
            items.append(
                CollectorItem(
                    source="etf_holdings",
                    symbol=symbol,
                    headline=f"{symbol} ETF holdings {names} map to {themes}",
                    published_at=utc_now_iso(),
                    raw={"holdings": [{"ticker": ticker, "company": company} for ticker, company in holdings]},
                )
            )
        return items

    def entities_and_beneficiaries(self) -> tuple[list[ThemeEntity], list[ThemeBeneficiary]]:
        entities: list[ThemeEntity] = []
        beneficiaries: list[ThemeBeneficiary] = []
        for etf in self.symbols:
            holdings = self._holdings(etf)
            themes = ETF_THEME_HINTS.get(etf, ())
            for theme in themes:
                for rank, (ticker, company) in enumerate(holdings[:8], start=1):
                    strength = max(45.0, 92.0 - rank * 6.0)
                    entities.append(ThemeEntity(theme, "company", company, ticker, strength))
                    beneficiaries.append(ThemeBeneficiary(theme, ticker, company, strength, strength))
        return entities, beneficiaries

    def _holdings(self, symbol: str) -> tuple[tuple[str, str], ...]:
        live = self._fmp_holdings(symbol)
        return live or STATIC_HOLDINGS.get(symbol, ())

    def _fmp_holdings(self, symbol: str) -> tuple[tuple[str, str], ...]:
        settings = get_settings()
        if not settings.fmp_api_key:
            return ()
        try:
            response = requests.get(
                f"https://financialmodelingprep.com/api/v3/etf-holder/{symbol}",
                params={"apikey": settings.fmp_api_key},
                timeout=settings.provider_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return ()
        rows: list[tuple[str, str]] = []
        for row in payload[:12] if isinstance(payload, list) else []:
            ticker = str(row.get("asset") or row.get("symbol") or "").upper()
            name = str(row.get("name") or ticker)
            if ticker:
                rows.append((ticker, name))
        return tuple(rows)
