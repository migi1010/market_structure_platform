from __future__ import annotations

from theme_intelligence.storage.theme_repository import ThemeRepository

from .stock_research_engine import StockResearchEngine
from .stock_research_repository import StockResearchRepository


def export_stock_research(ticker: str, repository: ThemeRepository | None = None) -> dict:
    engine = StockResearchEngine(StockResearchRepository(repository))
    return engine.build(ticker).to_dict()
