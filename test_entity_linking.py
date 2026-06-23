from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.models import ThemeMention
from theme_intelligence.processors.entity_linker import EntityLinker


def test_entity_linker_outputs_ticker_company_etf_sector_and_supply_chain_role() -> None:
    linker = EntityLinker()
    mentions = [
        ThemeMention("HBM", "finnhub", "NVDA", "NVIDIA Blackwell boosts HBM memory stack demand", "2026-06-05T00:00:00+00:00", 74),
        ThemeMention("Robotics", "etf_holdings", "BOTZ", "BOTZ ETF holdings include ISRG and TER robotics exposure", "2026-06-05T00:00:00+00:00", 60),
    ]

    result = linker.link(mentions)
    entity_types = {entity.entity_type for entity in result.entities}
    tickers = {entity.ticker for entity in result.entities}
    beneficiary_tickers = {row.ticker for row in result.beneficiaries}

    assert {"ticker", "company", "etf", "sector", "supply_chain_role"}.issubset(entity_types)
    assert "NVDA" in tickers
    assert "BOTZ" in tickers
    assert "NVDA" in beneficiary_tickers
