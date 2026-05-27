from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.data_pipeline import get_quote, safe_float
from quant_engine.factors.lightweight import score_basket, score_symbol, score_symbols
from quant_engine.narrative_engine import enrich_sector_narrative
from quant_engine.ranking_engine import enrich_universe_ranking
from quant_engine.theme_engine import enrich_sector_leadership

SECTOR_UNIVERSE: List[Dict[str, Any]] = [
    {"sector": "Technology", "etf": "XLK", "companies": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "PLTR"]},
    {"sector": "Energy", "etf": "XLE", "companies": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC"]},
    {"sector": "Healthcare", "etf": "XLV", "companies": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE"]},
    {"sector": "Financials", "etf": "XLF", "companies": ["JPM", "BAC", "GS", "MS", "V", "MA"]},
    {"sector": "Industrials", "etf": "XLI", "companies": ["GE", "CAT", "BA", "HON", "UPS", "RTX"]},
    {"sector": "Utilities", "etf": "XLU", "companies": ["NEE", "SO", "DUK", "AEP", "SRE", "D"]},
    {"sector": "Consumer Discretionary", "etf": "XLY", "companies": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX"]},
    {"sector": "Consumer Staples", "etf": "XLP", "companies": ["WMT", "COST", "PG", "KO", "PEP", "PM"]},
    {"sector": "Materials", "etf": "XLB", "companies": ["LIN", "SHW", "APD", "ECL", "FCX", "NEM"]},
    {"sector": "Real Estate", "etf": "XLRE", "companies": ["PLD", "AMT", "EQIX", "WELL", "SPG", "O"]},
    {"sector": "Communication Services", "etf": "XLC", "companies": ["META", "GOOGL", "GOOG", "NFLX", "DIS", "TMUS"]},
    {"sector": "Defense", "etf": "ITA", "companies": ["LMT", "RTX", "NOC", "GD", "LHX", "BA"]},
    {"sector": "Infrastructure", "etf": "PAVE", "companies": ["PWR", "ETN", "VMC", "MLM", "URI", "CAT"]},
    {"sector": "Commodities", "etf": "DBC", "companies": ["FCX", "XOM", "CVX", "NEM", "SCCO", "TECK"]},
    {"sector": "Nuclear", "etf": "URA", "companies": ["CEG", "VST", "NEE", "SMR", "CCJ", "BWXT"]},
    {"sector": "Shipping", "etf": "IYT", "companies": ["ZIM", "DAC", "SBLK", "GNK", "MATX", "KEX"]},
    {"sector": "Copper", "etf": "COPX", "companies": ["FCX", "SCCO", "TECK", "BHP", "RIO", "VALE"]},
    {"sector": "Aerospace", "etf": "ITA", "companies": ["BA", "RTX", "LMT", "NOC", "GD", "TDG"]},
]


def _company_metrics(symbol: str) -> Dict[str, Any]:
    factors = score_symbol(symbol)
    quote = get_quote(symbol)
    drawdown = _finite(factors.get("drawdown_pressure"))
    bubble = bounded_score(100.0 - drawdown) if drawdown is not None else None
    return {
        "ticker": symbol,
        "company_name": quote.get("longName") or quote.get("shortName") or symbol,
        "market_cap": safe_float(quote.get("marketCap")),
        "alpha_score": factors.get("alpha_score"),
        "bubble_score": bubble,
        "relative_strength": factors.get("relative_strength_spy"),
        "change_percent": safe_float(quote.get("regularMarketChangePercent")),
        "momentum_20d": factors.get("momentum_20d"),
        "momentum_60d": factors.get("momentum_60d"),
        "volume_participation": factors.get("volume_participation"),
        "trend_consistency": factors.get("trend_consistency"),
        "confidence_score": factors.get("confidence_score"),
        "confidence_label": factors.get("confidence_label"),
        "lifecycle_state": factors.get("lifecycle_state"),
    }


def _sector_metrics(sector: Dict[str, Any]) -> Dict[str, Any]:
    etf = score_symbol(sector["etf"])
    basket = score_basket(sector["companies"], limit=6)
    company_factor_rows = score_symbols(sector["companies"], limit=6)
    companies = [_company_from_factor(row) for row in company_factor_rows]
    ranked = sorted(companies, key=lambda row: _rankable(row.get("alpha_score")), reverse=True)
    for index, company in enumerate(ranked, start=1):
        company["sector_rank"] = index
    score = _weighted_optional([
        (etf.get("alpha_score"), 0.38),
        (basket.get("score"), 0.28),
        (etf.get("relative_strength_spy"), 0.16),
        (basket.get("participation_score"), 0.12),
        (etf.get("trend_consistency"), 0.06),
    ])
    relative_strength = _weighted_optional([
        (etf.get("relative_strength_spy"), 0.70),
        (basket.get("relative_strength"), 0.30),
    ])
    flow = _weighted_optional([
        (etf.get("volume_participation"), 0.45),
        (basket.get("volume_participation"), 0.35),
        (basket.get("participation_score"), 0.20),
    ])
    confidence_score = _weighted_optional([
        (etf.get("confidence_score"), 0.55),
        (basket.get("confidence_score"), 0.45),
    ])
    return {
        "sector": sector["sector"],
        "score": score,
        "relative_strength": relative_strength,
        "flow": flow,
        "companies": ranked,
        "rotation_state": "Accumulation" if _rankable(score) >= 70 else "Weakening" if _rankable(score) < 45 else "Neutral",
        "confidence_score": confidence_score,
        "confidence_label": confidence_label(confidence_score) if confidence_score is not None else "Unavailable",
        "momentum_20d": etf.get("momentum_20d"),
        "momentum_60d": etf.get("momentum_60d"),
        "volume_participation": flow,
        "trend_consistency": etf.get("trend_consistency"),
        "participation_breadth": basket.get("participation_score"),
        "lifecycle_state": "live" if confidence_score is not None and confidence_score >= 62.0 else "partial_live" if score is not None else "warming",
        "explanation": [
            f"{sector['sector']} rotation uses Render-safe 3-month ETF and constituent lightweight factors.",
            "Confidence is reduced when ETF history or constituent factor coverage is partial.",
        ],
    }


def analyze_sector_rotation() -> List[Dict[str, Any]]:
    sectors: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_sector_metrics, sector): sector["sector"] for sector in SECTOR_UNIVERSE[:12]}
        for future in as_completed(futures):
            sectors.append(future.result())
    ranked = sorted(sectors, key=lambda row: _rankable(row.get("score")), reverse=True)
    return [enrich_universe_ranking(enrich_sector_narrative(enrich_sector_leadership(row, index)), "sector", index) for index, row in enumerate(ranked, start=1)]


def _company_from_factor(row: Dict[str, Any]) -> Dict[str, Any]:
    symbol = str(row.get("symbol") or "").upper()
    quote = get_quote(symbol)
    drawdown = _finite(row.get("drawdown_pressure"))
    return {
        "ticker": symbol,
        "company_name": quote.get("longName") or quote.get("shortName") or symbol,
        "market_cap": safe_float(quote.get("marketCap")),
        "alpha_score": row.get("alpha_score"),
        "bubble_score": bounded_score(100.0 - drawdown) if drawdown is not None else None,
        "relative_strength": row.get("relative_strength_spy"),
        "change_percent": safe_float(quote.get("regularMarketChangePercent")),
        "momentum_20d": row.get("momentum_20d"),
        "momentum_60d": row.get("momentum_60d"),
        "volume_participation": row.get("volume_participation"),
        "trend_consistency": row.get("trend_consistency"),
        "confidence_score": row.get("confidence_score"),
        "confidence_label": row.get("confidence_label"),
        "lifecycle_state": row.get("lifecycle_state"),
    }


def _finite(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if np_isfinite(parsed) else None


def _weighted_optional(values: list[tuple[Any, float]]) -> float | None:
    usable: list[tuple[float, float]] = []
    for value, weight in values:
        parsed = _finite(value)
        if parsed is not None:
            usable.append((parsed, weight))
    if not usable:
        return None
    total = sum(weight for _, weight in usable) or 1.0
    return bounded_score(sum(value * weight for value, weight in usable) / total)


def _rankable(value: Any) -> float:
    parsed = _finite(value)
    return parsed if parsed is not None else -1.0


def np_isfinite(value: float) -> bool:
    try:
        return math.isfinite(value)
    except (TypeError, ValueError):
        return False
