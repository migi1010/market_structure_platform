from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from alpha_engine.scoring import bounded_score, calculate_sector_strength, calculate_stock_alpha
from quant_engine.bubble_engine import analyze_bubble
from quant_engine.data_pipeline import get_history, get_quote, safe_float
from quant_engine.earnings_quality_engine import analyze_earnings_quality
from quant_engine.smart_money_engine import analyze_smart_money

SECTOR_UNIVERSE: List[Dict[str, Any]] = [
    {"sector": "Technology", "etf": "XLK", "companies": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "PLTR"]},
    {"sector": "Healthcare", "etf": "XLV", "companies": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE"]},
    {"sector": "Financials", "etf": "XLF", "companies": ["JPM", "BAC", "GS", "MS", "V", "MA"]},
    {"sector": "Energy", "etf": "XLE", "companies": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC"]},
    {"sector": "Industrials", "etf": "XLI", "companies": ["GE", "CAT", "BA", "HON", "UPS", "RTX"]},
    {"sector": "Consumer", "etf": "XLY", "companies": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX"]},
    {"sector": "Utilities", "etf": "XLU", "companies": ["NEE", "SO", "DUK", "AEP", "SRE", "D"]},
    {"sector": "Real Estate", "etf": "XLRE", "companies": ["PLD", "AMT", "EQIX", "WELL", "SPG", "O"]},
]


def _etf_metrics(symbol: str, market_return: float) -> Dict[str, float]:
    history = get_history(symbol, "9mo")
    if history.empty or len(history) < 64:
        return {"momentum_1m": 0.0, "momentum_3m": 0.0, "relative_strength": -market_return, "relative_volume": 1.0, "volatility": 0.3}
    close = history["Close"].astype(float)
    volume = history["Volume"].astype(float)
    ret_1m = float(close.iloc[-1] / close.iloc[-22] - 1.0)
    ret_3m = float(close.iloc[-1] / close.iloc[-64] - 1.0)
    rel_vol = float(volume.iloc[-1] / max(volume.tail(60).mean(), 1.0))
    vol = float(close.pct_change().dropna().tail(64).std() * np.sqrt(252))
    return {"momentum_1m": ret_1m, "momentum_3m": ret_3m, "relative_strength": ret_3m - market_return, "relative_volume": rel_vol, "volatility": vol}


def analyze_sector_rotation() -> List[Dict[str, Any]]:
    spy = _etf_metrics("SPY", 0.0)
    market_return = spy["momentum_3m"]
    sectors: List[Dict[str, Any]] = []
    for sector in SECTOR_UNIVERSE:
        etf = _etf_metrics(sector["etf"], market_return)
        companies: List[Dict[str, Any]] = []
        cap_total = 0.0
        cap_flow = 0.0
        for symbol in sector["companies"]:
            quote = get_quote(symbol)
            history = get_history(symbol, "9mo")
            close = history["Close"].astype(float) if not history.empty else None
            momentum_1m = float(close.iloc[-1] / close.iloc[-22] - 1.0) if close is not None and len(close) > 22 else 0.0
            momentum_3m = float(close.iloc[-1] / close.iloc[-64] - 1.0) if close is not None and len(close) > 64 else 0.0
            momentum_6m = float(close.iloc[-1] / close.iloc[0] - 1.0) if close is not None and len(close) > 1 else 0.0
            relative_volume = 1.0
            if not history.empty and "Volume" in history:
                volume = history["Volume"].astype(float)
                relative_volume = float(volume.iloc[-1] / max(volume.tail(60).mean(), 1.0))
            smart = analyze_smart_money(symbol)
            earnings = analyze_earnings_quality(symbol)
            bubble = analyze_bubble(symbol)["bubble_analysis_data"]["bubble_index"]
            cap = safe_float(quote.get("marketCap"))
            cap_total += cap
            cap_flow += cap * momentum_1m
            alpha = calculate_stock_alpha(
                trend_strength=momentum_3m,
                relative_volume=relative_volume,
                price_acceleration=momentum_1m - momentum_3m / 3.0,
                momentum=momentum_6m,
                institutional_flow=safe_float(smart.get("smart_money_score")),
                earnings_surprise=(safe_float(earnings.get("quality_score")) - 50.0) / 100.0,
                hmm_prediction=bounded_score(50.0 + (momentum_3m - market_return) * 150.0),
                bubble_index=safe_float(bubble),
            )
            companies.append({
                "ticker": symbol,
                "company_name": quote.get("longName") or quote.get("shortName") or symbol,
                "market_cap": cap,
                "alpha_score": alpha,
                "bubble_score": bubble,
                "relative_strength": bounded_score(50.0 + (momentum_3m - market_return) * 180.0),
                "change_percent": safe_float(quote.get("regularMarketChangePercent")) or momentum_1m * 100.0,
            })

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
        sectors.append({
            "sector": sector["sector"],
            "score": score,
            "relative_strength": bounded_score(50.0 + etf["relative_strength"] * 180.0),
            "flow": bounded_score(50.0 + flow * 220.0),
            "companies": ranked,
            "rotation_state": "Accumulation" if score >= 70 else "Weakening" if score < 45 else "Neutral",
        })
    return sorted(sectors, key=lambda row: row["score"], reverse=True)
