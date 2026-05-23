from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import numpy as np

from alpha_engine.scoring import bounded_score, calculate_sector_strength, calculate_stock_alpha, confidence_label
from quant_engine.data_pipeline import get_history, get_quote, safe_float

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


def _etf_metrics(symbol: str, market_return: float) -> Dict[str, float]:
    history = get_history(symbol, "9mo")
    if history.empty or len(history) < 64:
        quote = get_quote(symbol)
        change = safe_float(quote.get("regularMarketChangePercent")) / 100.0
        volume = safe_float(quote.get("regularMarketVolume") or quote.get("volume"))
        avg_volume = safe_float(quote.get("averageVolume") or quote.get("averageDailyVolume10Day"))
        rel_vol = volume / max(avg_volume, 1.0) if volume > 0 and avg_volume > 0 else 0.85
        return {"momentum_1m": change, "momentum_3m": change * 3.0, "relative_strength": change * 3.0 - market_return, "relative_volume": rel_vol, "volatility": 0.38, "confidence": 35.0}
    close = history["Close"].astype(float)
    volume = history["Volume"].astype(float)
    ret_1m = float(close.iloc[-1] / close.iloc[-22] - 1.0)
    ret_3m = float(close.iloc[-1] / close.iloc[-64] - 1.0)
    rel_vol = float(volume.iloc[-1] / max(volume.tail(60).mean(), 1.0))
    vol = float(close.pct_change().dropna().tail(64).std() * np.sqrt(252))
    confidence = bounded_score(min(len(history), 189) / 189.0 * 70.0 + min(rel_vol, 2.0) / 2.0 * 15.0 + 15.0)
    return {"momentum_1m": ret_1m, "momentum_3m": ret_3m, "relative_strength": ret_3m - market_return, "relative_volume": rel_vol, "volatility": vol, "confidence": confidence}


def _company_metrics(symbol: str, market_return: float) -> Dict[str, Any]:
    quote = get_quote(symbol)
    history = get_history(symbol, "9mo")
    close = history["Close"].astype(float) if not history.empty and "Close" in history else None
    momentum_1m = float(close.iloc[-1] / close.iloc[-22] - 1.0) if close is not None and len(close) > 22 else 0.0
    momentum_3m = float(close.iloc[-1] / close.iloc[-64] - 1.0) if close is not None and len(close) > 64 else 0.0
    momentum_6m = float(close.iloc[-1] / close.iloc[0] - 1.0) if close is not None and len(close) > 1 else 0.0
    relative_volume = 1.0
    if not history.empty and "Volume" in history:
        volume = history["Volume"].astype(float)
        relative_volume = float(volume.iloc[-1] / max(volume.tail(60).mean(), 1.0))

    pe_ratio = safe_float(quote.get("trailingPE") or quote.get("forwardPE"))
    ps_ratio = safe_float(quote.get("priceToSalesTrailing12Months"))
    profit_margin = safe_float(quote.get("profitMargins"))
    revenue_growth = safe_float(quote.get("revenueGrowth"))
    debt_to_equity = safe_float(quote.get("debtToEquity")) / 100.0
    bubble = bounded_score(
        30.0
        + max(0.0, pe_ratio - 25.0) * 0.6
        + max(0.0, ps_ratio - 6.0) * 2.4
        + max(0.0, momentum_6m - revenue_growth) * 45.0
        + max(0.0, debt_to_equity - 0.7) * 18.0
        - max(0.0, profit_margin) * 12.0
    )
    earnings_quality = bounded_score(50.0 + profit_margin * 80.0 + revenue_growth * 35.0 - debt_to_equity * 12.0)
    smart_money = bounded_score(50.0 + momentum_3m * 110.0 + (relative_volume - 1.0) * 18.0 + (momentum_1m - momentum_3m / 3.0) * 80.0)
    alpha = calculate_stock_alpha(
        trend_strength=momentum_3m,
        relative_volume=relative_volume,
        price_acceleration=momentum_1m - momentum_3m / 3.0,
        momentum=momentum_6m,
        institutional_flow=smart_money,
        earnings_surprise=(earnings_quality - 50.0) / 100.0,
        hmm_prediction=bounded_score(50.0 + (momentum_3m - market_return) * 150.0),
        bubble_index=bubble,
    )
    return {
        "ticker": symbol,
        "company_name": quote.get("longName") or quote.get("shortName") or symbol,
        "market_cap": safe_float(quote.get("marketCap")),
        "alpha_score": alpha,
        "bubble_score": bubble,
        "relative_strength": bounded_score(50.0 + (momentum_3m - market_return) * 180.0),
        "change_percent": safe_float(quote.get("regularMarketChangePercent")) or momentum_1m * 100.0,
    }


def _sector_metrics(sector: Dict[str, Any], market_return: float) -> Dict[str, Any]:
    etf = _etf_metrics(sector["etf"], market_return)
    companies: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(6, len(sector["companies"]))) as executor:
        futures = {executor.submit(_company_metrics, symbol, market_return): symbol for symbol in sector["companies"]}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                companies.append(future.result())
            except Exception:
                quote = get_quote(symbol)
                companies.append({
                    "ticker": symbol,
                    "company_name": quote.get("longName") or quote.get("shortName") or symbol,
                    "market_cap": safe_float(quote.get("marketCap")),
                    "alpha_score": 42.0,
                    "bubble_score": 48.0,
                    "relative_strength": 42.0,
                    "change_percent": safe_float(quote.get("regularMarketChangePercent")),
                    "confidence_score": 25.0,
                    "confidence_label": "Low Confidence",
                })

    cap_total = float(sum(item["market_cap"] for item in companies))
    cap_flow = float(sum(item["market_cap"] * (item["change_percent"] / 100.0) for item in companies))
    avg_alpha = float(np.mean([item["alpha_score"] for item in companies])) if companies else 50.0
    avg_bubble = float(np.mean([item["bubble_score"] for item in companies])) if companies else 50.0
    flow = cap_flow / cap_total if cap_total > 0 else etf["momentum_1m"]
    score = calculate_sector_strength(
        price_momentum=etf["momentum_3m"],
        relative_strength=etf["relative_strength"],
        volume_strength=etf["relative_volume"],
        market_cap_flow=flow,
        volatility=etf["volatility"],
        earnings_growth=(avg_alpha - 50.0) / 100.0,
        analyst_sentiment=avg_alpha,
        bubble_risk=avg_bubble,
    )
    ranked = sorted(companies, key=lambda row: row["alpha_score"], reverse=True)
    for index, company in enumerate(ranked, start=1):
        company["sector_rank"] = index
    confidence_score = bounded_score(etf.get("confidence", 40.0) * 0.45 + min(len(companies), len(sector["companies"])) / max(len(sector["companies"]), 1) * 35.0 + (100.0 - avg_bubble) * 0.20)
    return {
        "sector": sector["sector"],
        "score": score,
        "relative_strength": bounded_score(50.0 + etf["relative_strength"] * 180.0),
        "flow": bounded_score(50.0 + flow * 220.0),
        "companies": ranked,
        "rotation_state": "Accumulation" if score >= 70 else "Weakening" if score < 45 else "Neutral",
        "confidence_score": confidence_score,
        "confidence_label": confidence_label(confidence_score),
        "explanation": [
            f"{sector['sector']} rotation score reflects relative strength, volume participation, capital flow, volatility-adjusted momentum, and breadth.",
            "Confidence is reduced when ETF history or constituent coverage is partial.",
        ],
    }


def analyze_sector_rotation() -> List[Dict[str, Any]]:
    spy = _etf_metrics("SPY", 0.0)
    market_return = spy["momentum_3m"]
    sectors: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_sector_metrics, sector, market_return): sector["sector"] for sector in SECTOR_UNIVERSE}
        for future in as_completed(futures):
            sectors.append(future.result())
    return sorted(sectors, key=lambda row: row["score"], reverse=True)
