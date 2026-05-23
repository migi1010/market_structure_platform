from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.data_pipeline import get_history, get_quote, safe_float

from .supply_chain_mapper import map_supply_chain
from .theme_detector import ThemeDefinition, get_theme_definitions
from .theme_rotation import build_theme_snapshot

PREFERRED_STOCKS: dict[str, tuple[str, ...]] = {
    "ai infrastructure": ("NVDA", "AVGO", "VRT", "AMD", "ETN", "ANET"),
    "semiconductor": ("NVDA", "AMD", "TSM", "ASML", "AMAT", "LRCX", "MU"),
    "hbm": ("NVDA", "MU", "AMD", "TSM", "AVGO"),
    "glass substrate": ("INTC", "AMAT", "TSM", "AMKR", "GLW"),
    "cybersecurity": ("CRWD", "PANW", "ZS", "FTNT", "OKTA"),
    "electric grid": ("ETN", "GE", "PWR", "HUBB", "FCX"),
    "nuclear energy": ("CEG", "VST", "BWXT", "CCJ", "SMR"),
    "nuclear": ("CEG", "VST", "BWXT", "CCJ", "SMR"),
    "shipping": ("ZIM", "MATX", "DAC", "SBLK", "GNK"),
}

COMPANY_FALLBACKS: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "AMD": "Advanced Micro Devices Inc.",
    "AMAT": "Applied Materials Inc.",
    "AMKR": "Amkor Technology Inc.",
    "ANET": "Arista Networks Inc.",
    "ASML": "ASML Holding N.V.",
    "AVGO": "Broadcom Inc.",
    "BWXT": "BWX Technologies Inc.",
    "CCJ": "Cameco Corporation",
    "CEG": "Constellation Energy Corporation",
    "CRWD": "CrowdStrike Holdings Inc.",
    "DAC": "Danaos Corporation",
    "ETN": "Eaton Corporation plc",
    "FCX": "Freeport-McMoRan Inc.",
    "FTNT": "Fortinet Inc.",
    "GE": "GE Aerospace",
    "GNK": "Genco Shipping & Trading Limited",
    "GLW": "Corning Incorporated",
    "HUBB": "Hubbell Incorporated",
    "INTC": "Intel Corporation",
    "LRCX": "Lam Research Corporation",
    "MATX": "Matson Inc.",
    "MU": "Micron Technology Inc.",
    "NVDA": "NVIDIA Corporation",
    "OKTA": "Okta Inc.",
    "PANW": "Palo Alto Networks Inc.",
    "PWR": "Quanta Services Inc.",
    "SBLK": "Star Bulk Carriers Corp.",
    "SMR": "NuScale Power Corporation",
    "TSM": "Taiwan Semiconductor Manufacturing Company Limited",
    "VRT": "Vertiv Holdings Co.",
    "VST": "Vistra Corp.",
    "ZIM": "ZIM Integrated Shipping Services Ltd.",
    "ZS": "Zscaler Inc.",
}


def slugify_theme(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def find_theme(theme_id: str) -> ThemeDefinition | None:
    normalized = theme_id.strip().lower().replace("-", " ")
    slug = slugify_theme(theme_id)
    for theme in get_theme_definitions():
        if normalized == theme.name.lower() or slug == slugify_theme(theme.name) or normalized in theme.name.lower():
            return theme
    aliases = {
        "ai": "AI Infrastructure",
        "grid": "Electric Grid",
        "copper": "Cable / Copper",
        "nuclear": "Nuclear Energy",
        "cyber": "Cybersecurity",
        "security": "Cybersecurity",
    }
    alias_target = aliases.get(normalized)
    if alias_target:
        return find_theme(alias_target)
    return None


def _role_map(theme: ThemeDefinition) -> Dict[str, str]:
    roles: Dict[str, str] = {}
    for role, symbols in theme.supply_chain.items():
        for symbol in symbols:
            roles.setdefault(symbol, role.replace("_", " "))
    for symbol in theme.tickers:
        roles.setdefault(symbol, "theme leader")
    return roles


def _preferred_symbols(theme: ThemeDefinition) -> list[str]:
    key = theme.name.lower()
    symbols = list(PREFERRED_STOCKS.get(key, ()))
    symbols.extend(theme.tickers)
    for bucket in theme.supply_chain.values():
        symbols.extend(bucket)
    seen: set[str] = set()
    ordered: list[str] = []
    for symbol in symbols:
        normalized = symbol.strip().upper()
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _history_metrics(symbol: str) -> dict[str, float | None]:
    try:
        history = get_history(symbol, "3mo")
        if history is None or history.empty or "Close" not in history:
            return {"momentum": None, "relative_volume": None}
        close = history["Close"].dropna().astype(float)
        volume = history["Volume"].dropna().astype(float) if "Volume" in history else None
        momentum = float(close.iloc[-1] / close.iloc[0] - 1.0) if len(close) > 1 else None
        relative_volume = float(volume.iloc[-1] / max(volume.tail(45).mean(), 1.0)) if volume is not None and len(volume) > 10 else None
        return {"momentum": momentum, "relative_volume": relative_volume}
    except Exception:
        return {"momentum": None, "relative_volume": None}


def _stock_row(symbol: str, role: str, theme_score: float) -> Dict[str, Any]:
    quote: dict[str, Any] = {}
    try:
        quote = get_quote(symbol)
    except Exception:
        quote = {}
    metrics = _history_metrics(symbol)
    price = safe_float(quote.get("currentPrice") or quote.get("regularMarketPrice"))
    change_percent = safe_float(quote.get("regularMarketChangePercent"))
    market_cap = safe_float(quote.get("marketCap") or quote.get("market_cap"))
    momentum = metrics["momentum"]
    relative_volume = metrics["relative_volume"]
    alpha_score = bounded_score(
        48.0
        + (momentum or 0.0) * 90.0
        + ((relative_volume or 1.0) - 1.0) * 16.0
        + theme_score * 0.22
        + min(market_cap, 1_000_000_000_000.0) / 1_000_000_000_000.0 * 8.0
    ) if momentum is not None or price > 0 else None
    smart_money = bounded_score(46.0 + ((relative_volume or 1.0) - 1.0) * 26.0 + max(0.0, momentum or 0.0) * 55.0) if relative_volume is not None or momentum is not None else None
    pe = safe_float(quote.get("trailingPE") or quote.get("forwardPE"))
    ps = safe_float(quote.get("priceToSalesTrailing12Months"))
    bubble_risk = bounded_score(30.0 + max(0.0, pe - 28.0) * 0.75 + max(0.0, ps - 6.0) * 3.6 + max(0.0, momentum or 0.0) * 34.0) if pe > 0 or ps > 0 or momentum is not None else None
    confidence_inputs = [price > 0, momentum is not None, relative_volume is not None, market_cap > 0]
    confidence_score = bounded_score(sum(1 for value in confidence_inputs if value) / len(confidence_inputs) * 100.0)
    return {
        "ticker": symbol,
        "company_name": str(quote.get("longName") or quote.get("shortName") or COMPANY_FALLBACKS.get(symbol) or symbol),
        "role": role,
        "price": round(price, 4) if price > 0 else None,
        "change_percent": round(change_percent, 4) if change_percent != 0.0 else None,
        "market_cap": market_cap if market_cap > 0 else None,
        "alpha_score": round(alpha_score, 2) if alpha_score is not None else None,
        "smart_money": round(smart_money, 2) if smart_money is not None else None,
        "bubble_risk": round(bubble_risk, 2) if bubble_risk is not None else None,
        "confidence_score": confidence_score,
        "confidence_label": confidence_label(confidence_score),
        "quote_status": quote.get("quoteStatus") or ("live" if price > 0 else "unavailable"),
    }


def get_theme_stocks(theme_id: str, limit: int = 10) -> Dict[str, Any]:
    theme = find_theme(theme_id)
    if theme is None:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "theme": theme_id,
            "theme_id": slugify_theme(theme_id),
            "related_stocks": [],
            "top_alpha_stocks": [],
            "fallback": True,
            "summary": "Theme not found in the institutional theme universe.",
        }
    snapshot = {row.get("theme"): row for row in build_theme_snapshot()}
    theme_metrics = snapshot.get(theme.name, {})
    theme_score = safe_float(theme_metrics.get("theme_strength_score"))
    roles = _role_map(theme)
    rows = [_stock_row(symbol, roles.get(symbol, "theme exposure"), theme_score) for symbol in _preferred_symbols(theme)]
    related = rows[:limit]
    top_alpha = sorted(related, key=lambda item: safe_float(item.get("alpha_score")), reverse=True)[: min(5, limit)]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "theme": theme.name,
        "theme_id": slugify_theme(theme.name),
        "category": theme.category,
        "description": theme.description,
        "related_stocks": related,
        "top_alpha_stocks": top_alpha,
        "summary": f"{theme.name} related stocks include {', '.join(row['ticker'] for row in related[:3])}.",
    }


def get_theme_stocks_static(theme_id: str, limit: int = 10) -> Dict[str, Any]:
    theme = find_theme(theme_id)
    if theme is None:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "theme": theme_id,
            "theme_id": slugify_theme(theme_id),
            "related_stocks": [],
            "top_alpha_stocks": [],
            "fallback": True,
            "summary": "Theme not found in the institutional theme universe.",
        }
    roles = _role_map(theme)
    rows = [
        {
            "ticker": symbol,
            "company_name": COMPANY_FALLBACKS.get(symbol) or symbol,
            "role": roles.get(symbol, "theme exposure"),
            "price": None,
            "change_percent": None,
            "market_cap": None,
            "alpha_score": None,
            "smart_money": None,
            "bubble_risk": None,
            "confidence_score": 20.0,
            "confidence_label": "Partial Data",
            "quote_status": "unavailable",
        }
        for symbol in _preferred_symbols(theme)[:limit]
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "theme": theme.name,
        "theme_id": slugify_theme(theme.name),
        "category": theme.category,
        "description": theme.description,
        "related_stocks": rows,
        "top_alpha_stocks": rows[: min(5, limit)],
        "summary": f"{theme.name} related stocks include {', '.join(row['ticker'] for row in rows[:3])}.",
        "fallback": True,
    }


def get_theme_detail(theme_id: str) -> Dict[str, Any]:
    theme = find_theme(theme_id)
    if theme is None:
        stocks = get_theme_stocks(theme_id)
        return {**stocks, "theme_score": None, "confidence": "Unavailable", "status": "Unavailable", "supply_chain": {}, "capital_flow": None, "bubble_risk": None}
    snapshot = {row.get("theme"): row for row in build_theme_snapshot()}
    metrics = snapshot.get(theme.name, {})
    stocks = get_theme_stocks(theme.name, limit=12)
    supply_chain = map_supply_chain(theme)
    bubble_values = [safe_float(row.get("bubble_risk")) for row in stocks["related_stocks"] if row.get("bubble_risk") is not None]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "theme": theme.name,
        "theme_id": slugify_theme(theme.name),
        "category": theme.category,
        "description": theme.description,
        "theme_score": metrics.get("theme_strength_score"),
        "confidence": metrics.get("confidence_label") or "Partial Data",
        "confidence_score": metrics.get("confidence_score"),
        "status": metrics.get("status") or "Watchlist",
        "supply_chain": supply_chain.get("supply_chain", {}),
        "related_stocks": stocks["related_stocks"],
        "top_alpha_stocks": stocks["top_alpha_stocks"],
        "capital_flow": metrics.get("theme_capital_flow_score"),
        "bubble_risk": round(sum(bubble_values) / len(bubble_values), 2) if bubble_values else None,
        "explainability": metrics.get("explainability") or [],
        "risks": metrics.get("risks") or [],
        "summary": stocks["summary"],
    }


def get_theme_detail_static(theme_id: str) -> Dict[str, Any]:
    theme = find_theme(theme_id)
    stocks = get_theme_stocks_static(theme_id, limit=12)
    if theme is None:
        return {**stocks, "theme_score": None, "confidence": "Unavailable", "status": "Unavailable", "supply_chain": {}, "capital_flow": None, "bubble_risk": None}
    supply_chain: Dict[str, List[Dict[str, Any]]] = {}
    roles = _role_map(theme)
    for role, symbols in theme.supply_chain.items():
        supply_chain[role] = [
            {
                "ticker": symbol,
                "company_name": COMPANY_FALLBACKS.get(symbol) or symbol,
                "role": roles.get(symbol, role.replace("_", " ")),
                "price": None,
                "change_percent": None,
            }
            for symbol in symbols[:6]
        ]
    return {
        **stocks,
        "theme_score": None,
        "confidence": "Partial Data",
        "confidence_score": 20.0,
        "status": "Calibrating",
        "supply_chain": supply_chain,
        "capital_flow": None,
        "bubble_risk": None,
        "explainability": ["Theme stock universe is available; live alpha and capital-flow scores are warming up."],
        "risks": ["Live quote enrichment is temporarily unavailable."],
    }
