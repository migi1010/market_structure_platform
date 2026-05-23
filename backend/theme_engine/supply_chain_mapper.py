from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from quant_engine.data_pipeline import get_quote, safe_float

from .theme_detector import ThemeDefinition, get_theme_definitions


def _leader(symbol: str, role: str) -> Dict[str, Any]:
    try:
        quote = get_quote(symbol)
    except Exception:
        quote = {}
    return {
        "ticker": symbol,
        "company_name": str(quote.get("longName") or quote.get("shortName") or symbol),
        "role": role,
        "market_cap": safe_float(quote.get("marketCap")),
        "price": safe_float(quote.get("currentPrice") or quote.get("regularMarketPrice")),
        "change_percent": safe_float(quote.get("regularMarketChangePercent")),
    }


def map_supply_chain(theme: ThemeDefinition) -> Dict[str, Any]:
    mapped: Dict[str, List[Dict[str, Any]]] = {}
    for role, symbols in theme.supply_chain.items():
        mapped[role] = [_leader(symbol, role) for symbol in symbols]
    leaders = [_leader(symbol, "theme_leader") for symbol in theme.tickers[:8]]
    leaders.sort(key=lambda item: safe_float(item.get("market_cap")), reverse=True)
    return {
        "theme": theme.name,
        "category": theme.category,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "supply_chain": mapped,
        "leaders": leaders[:8],
        "summary": f"{theme.name} supply chain spans {', '.join(role.replace('_', ' ') for role in theme.supply_chain.keys())}.",
    }


def map_all_supply_chains() -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "themes": [map_supply_chain(theme) for theme in get_theme_definitions()],
    }
