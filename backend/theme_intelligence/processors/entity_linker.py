from __future__ import annotations

import re
from dataclasses import dataclass

from theme_intelligence.collectors.etf_collector import ETF_THEME_HINTS, STATIC_HOLDINGS
from theme_intelligence.models import ThemeBeneficiary, ThemeEntity, ThemeMention, clamp_score


COMPANY_BY_TICKER: dict[str, tuple[str, str, str]] = {
    "NVDA": ("NVIDIA Corporation", "Semiconductors", "accelerator"),
    "AMD": ("Advanced Micro Devices", "Semiconductors", "accelerator"),
    "AVGO": ("Broadcom Inc.", "Semiconductors", "networking"),
    "TSM": ("Taiwan Semiconductor Manufacturing", "Semiconductors", "foundry"),
    "INTC": ("Intel Corporation", "Semiconductors", "packaging"),
    "MU": ("Micron Technology", "Semiconductors", "memory"),
    "GLW": ("Corning Inc.", "Materials", "substrate_materials"),
    "ANET": ("Arista Networks", "Technology Hardware", "networking"),
    "ETN": ("Eaton Corporation", "Industrials", "power_equipment"),
    "VRT": ("Vertiv Holdings", "Industrials", "data_center_power"),
    "ISRG": ("Intuitive Surgical", "Healthcare Equipment", "robotics_platform"),
    "TER": ("Teradyne", "Semiconductor Equipment", "automation_equipment"),
    "CEG": ("Constellation Energy", "Utilities", "power_generation"),
    "SMR": ("NuScale Power", "Utilities", "reactor_technology"),
}


@dataclass(frozen=True)
class EntityLinkResult:
    entities: list[ThemeEntity]
    beneficiaries: list[ThemeBeneficiary]


class EntityLinker:
    def link(self, mentions: list[ThemeMention]) -> EntityLinkResult:
        entities: list[ThemeEntity] = []
        beneficiaries: list[ThemeBeneficiary] = []
        seen_entities: set[tuple[str, str, str]] = set()
        seen_beneficiaries: set[tuple[str, str]] = set()
        for mention in mentions:
            for ticker in self._tickers_for(mention):
                company, sector, role = COMPANY_BY_TICKER.get(ticker, (ticker, "US Equity", "theme_exposure"))
                self._add_entity(entities, seen_entities, mention.theme_name, "ticker", ticker, ticker, 68)
                self._add_entity(entities, seen_entities, mention.theme_name, "company", company, ticker, 74)
                self._add_entity(entities, seen_entities, mention.theme_name, "sector", sector, ticker, 58)
                self._add_entity(entities, seen_entities, mention.theme_name, "supply_chain_role", role, ticker, 70)
                if (mention.theme_name, ticker) not in seen_beneficiaries:
                    seen_beneficiaries.add((mention.theme_name, ticker))
                    beneficiaries.append(
                        ThemeBeneficiary(
                            theme_name=mention.theme_name,
                            ticker=ticker,
                            company_name=company,
                            beneficiary_score=clamp_score(70.0 + max(0.0, mention.sentiment - 50.0) * 0.25),
                            relationship_strength=74.0,
                            updated_at=mention.mention_time,
                        )
                    )
            if mention.source == "etf_holdings" and mention.symbol:
                etf = mention.symbol.upper()
                self._add_entity(entities, seen_entities, mention.theme_name, "etf", etf, etf, 76)
                for ticker, company in STATIC_HOLDINGS.get(etf, ())[:5]:
                    if mention.theme_name in ETF_THEME_HINTS.get(etf, ()):
                        self._add_entity(entities, seen_entities, mention.theme_name, "company", company, ticker, 64)
        return EntityLinkResult(entities, beneficiaries)

    @staticmethod
    def _add_entity(entities: list[ThemeEntity], seen: set[tuple[str, str, str]], theme: str, entity_type: str, company: str, ticker: str, strength: float) -> None:
        key = (theme, entity_type, ticker)
        if key in seen:
            return
        seen.add(key)
        entities.append(ThemeEntity(theme, entity_type, company, ticker, strength))

    @staticmethod
    def _tickers_for(mention: ThemeMention) -> set[str]:
        tickers: set[str] = set()
        if mention.symbol and mention.symbol.upper() not in STATIC_HOLDINGS:
            tickers.add(mention.symbol.upper())
        upper = mention.headline.upper()
        for ticker in COMPANY_BY_TICKER:
            if re.search(rf"(?<![A-Z0-9]){re.escape(ticker)}(?![A-Z0-9])", upper):
                tickers.add(ticker)
        for ticker, (company, _, _) in COMPANY_BY_TICKER.items():
            if company.lower().split()[0] in mention.headline.lower():
                tickers.add(ticker)
        return tickers
