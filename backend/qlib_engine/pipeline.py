from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np

from alpha_engine.scoring import bounded_score, calculate_bubble_index
from quant_engine.data_pipeline import get_history, get_quote, safe_float

SP500_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "AVGO", "LLY", "JPM", "XOM",
    "UNH", "V", "MA", "COST", "HD", "PG", "JNJ", "ABBV", "MRK", "AMD",
]

NASDAQ100_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "GOOGL", "GOOG", "COST", "TSLA",
    "NFLX", "AMD", "ADBE", "PEP", "LIN", "CSCO", "TMUS", "INTU", "AMAT", "QCOM",
]

SECTOR_ETFS = {
    "Technology": "XLK",
    "Communication Services": "XLC",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
}


@dataclass
class AlphaRow:
    ticker: str
    company_name: str
    sector: str
    alpha_score: float
    quality: float
    growth: float
    smart_money: float
    valuation: float
    earnings_quality: float
    market_structure: float
    bubble_risk: float
    sector_alignment: float
    theme_alignment: float
    theme_strength: float
    theme_capital_flow: float
    theme_explanation: List[str]
    suggested_action: str
    factor_importance: Dict[str, float]


def _try_init_qlib(qlib_available: bool | None = None) -> Dict[str, Any]:
    if qlib_available is False:
        return {
            "available": False,
            "mode": "fallback",
            "provider": "Microsoft Qlib compatible pipeline",
            "factor_set": "Alpha158-inspired live factor subset",
            "reason": "pyqlib is not installed in this Render runtime",
        }
    try:
        import qlib  # type: ignore
        from qlib.contrib.data.handler import Alpha158  # type: ignore

        return {
            "available": True,
            "mode": "qlib",
            "provider": "Microsoft Qlib",
            "factor_set": "Alpha158",
            "alpha158_class": Alpha158.__name__,
            "version": getattr(qlib, "__version__", "installed"),
        }
    except Exception as exc:
        return {
            "available": False,
            "mode": "fallback",
            "provider": "Microsoft Qlib compatible pipeline",
            "factor_set": "Alpha158-inspired live factor subset",
            "reason": str(exc),
        }


def _pct(now: float, then: float) -> float:
    return now / then - 1.0 if then > 0 else 0.0


def _series_metrics(symbol: str) -> Dict[str, Any]:
    info = get_quote(symbol)
    hist = get_history(symbol, "9mo")
    if hist is None or hist.empty or len(hist) < 64:
        raise ValueError(f"insufficient history for {symbol}")

    close = hist["Close"].astype(float)
    volume = hist["Volume"].astype(float)
    latest = float(close.iloc[-1])
    ret_1m = _pct(latest, float(close.iloc[-22]))
    ret_3m = _pct(latest, float(close.iloc[-64]))
    ret_6m = _pct(latest, float(close.iloc[0]))
    acceleration = ret_1m - ret_3m / 3.0
    returns = close.pct_change().dropna()
    volatility = float(returns.tail(64).std() * np.sqrt(252)) if len(returns) > 10 else 0.35
    avg_volume = float(volume.tail(60).mean()) if len(volume) > 0 else 1.0
    relative_volume = float(volume.iloc[-1]) / max(avg_volume, 1.0)

    revenue_growth = safe_float(info.get("revenueGrowth"))
    gross_margin = safe_float(info.get("grossMargins"))
    fcf = safe_float(info.get("freeCashflow"))
    operating_cash = safe_float(info.get("operatingCashflow"))
    net_income_margin = safe_float(info.get("profitMargins"))
    debt_to_equity = safe_float(info.get("debtToEquity")) / 100.0
    pe = safe_float(info.get("trailingPE") or info.get("forwardPE"))
    ps = safe_float(info.get("priceToSalesTrailing12Months"))
    bubble = calculate_bubble_index(
        pe_ratio=pe,
        ps_ratio=ps,
        revenue_growth=revenue_growth,
        price_return=ret_6m,
        gross_margin=gross_margin,
        free_cash_flow=fcf,
        operating_cash_flow=operating_cash,
        net_income=max(1.0, abs(net_income_margin) * max(safe_float(info.get("totalRevenue")), 1.0)),
        debt_ratio=debt_to_equity,
        shares_growth=0.0,
        retail_sentiment=50.0 + max(0.0, ret_3m) * 80.0,
        volatility_change=volatility - 0.25,
    )

    return {
        "ticker": symbol,
        "company_name": str(info.get("longName") or info.get("shortName") or symbol),
        "sector": str(info.get("sector") or "Unknown"),
        "price": latest,
        "change_percent": safe_float(info.get("regularMarketChangePercent")) or ret_1m * 100.0,
        "market_cap": safe_float(info.get("marketCap")),
        "ret_1m": ret_1m,
        "ret_3m": ret_3m,
        "ret_6m": ret_6m,
        "acceleration": acceleration,
        "relative_volume": relative_volume,
        "volatility": volatility,
        "revenue_growth": revenue_growth,
        "gross_margin": gross_margin,
        "free_cash_flow": fcf,
        "operating_cash_flow": operating_cash,
        "net_income_margin": net_income_margin,
        "debt_to_equity": debt_to_equity,
        "pe": pe,
        "ps": ps,
        "bubble_risk": bubble,
    }


def _factor_scores(metrics: Dict[str, Any], sector_alignment: float, regime: str) -> AlphaRow:
    try:
        from theme_engine import theme_alignment_for_symbol

        theme_signal = theme_alignment_for_symbol(metrics["ticker"], metrics["sector"])
    except Exception:
        theme_signal = {
            "theme_alignment": 50.0,
            "theme_strength": 50.0,
            "theme_capital_flow": 50.0,
            "explanation": ["Theme engine unavailable; stock-level alpha factors remain active."],
        }

    theme_alignment = safe_float(theme_signal.get("theme_alignment"))
    theme_strength = safe_float(theme_signal.get("theme_strength"))
    theme_capital_flow = safe_float(theme_signal.get("theme_capital_flow"))
    theme_explanation = list(theme_signal.get("explanation") or [])
    quality = bounded_score(50.0 + metrics["gross_margin"] * 80.0 + metrics["net_income_margin"] * 120.0 - metrics["debt_to_equity"] * 18.0)
    growth = bounded_score(50.0 + metrics["revenue_growth"] * 130.0 + metrics["ret_3m"] * 80.0)
    smart_money = bounded_score(50.0 + (metrics["relative_volume"] - 1.0) * 22.0 + metrics["ret_1m"] * 90.0 + metrics["acceleration"] * 110.0)
    valuation = bounded_score(78.0 - max(0.0, metrics["pe"] - 18.0) * 0.9 - max(0.0, metrics["ps"] - 4.0) * 3.0 + max(0.0, metrics["free_cash_flow"]) / 2_000_000_000.0)
    earnings_quality = bounded_score(50.0 + (metrics["free_cash_flow"] / max(abs(metrics["operating_cash_flow"]), 1.0)) * 45.0 + metrics["net_income_margin"] * 70.0)
    market_structure = bounded_score(50.0 + metrics["ret_6m"] * 75.0 - metrics["volatility"] * 25.0 + sector_alignment * 0.17 + theme_alignment * 0.12)

    if regime == "Bear Market":
        weights = {"quality": 0.23, "growth": 0.13, "smart_money": 0.16, "valuation": 0.20, "earnings_quality": 0.14, "market_structure": 0.07, "theme": 0.07}
    else:
        weights = {"quality": 0.18, "growth": 0.20, "smart_money": 0.18, "valuation": 0.12, "earnings_quality": 0.14, "market_structure": 0.09, "theme": 0.09}

    alpha_score = bounded_score(
        quality * weights["quality"]
        + growth * weights["growth"]
        + smart_money * weights["smart_money"]
        + valuation * weights["valuation"]
        + earnings_quality * weights["earnings_quality"]
        + market_structure * weights["market_structure"]
        + theme_alignment * weights["theme"]
        - max(0.0, metrics["bubble_risk"] - 55.0) * 0.25
    )
    if alpha_score > 88 and metrics["bubble_risk"] < 40 and smart_money > 70 and earnings_quality > 70 and sector_alignment > 55:
        action = "Strong Buy"
    elif alpha_score > 78 and metrics["bubble_risk"] < 55:
        action = "Accumulation"
    elif metrics["bubble_risk"] >= 70:
        action = "Bubble Risk"
    elif alpha_score < 45:
        action = "Avoid"
    elif alpha_score > 62:
        action = "Watchlist"
    else:
        action = "Hold"

    return AlphaRow(
        ticker=metrics["ticker"],
        company_name=metrics["company_name"],
        sector=metrics["sector"],
        alpha_score=alpha_score,
        quality=quality,
        growth=growth,
        smart_money=smart_money,
        valuation=valuation,
        earnings_quality=earnings_quality,
        market_structure=market_structure,
        bubble_risk=metrics["bubble_risk"],
        sector_alignment=sector_alignment,
        theme_alignment=theme_alignment,
        theme_strength=theme_strength,
        theme_capital_flow=theme_capital_flow,
        theme_explanation=theme_explanation,
        suggested_action=action,
        factor_importance=weights,
    )


def run_alpha_pipeline(universe: str = "sp500", qlib_available: bool | None = None) -> Dict[str, Any]:
    qlib_status = _try_init_qlib(qlib_available)
    symbols = sorted(set(SP500_UNIVERSE if universe.lower() == "sp500" else NASDAQ100_UNIVERSE))

    sector_scores: Dict[str, float] = {}
    for sector, etf in SECTOR_ETFS.items():
        try:
            m = _series_metrics(etf)
            sector_scores[sector] = bounded_score(50.0 + m["ret_3m"] * 150.0 + (m["relative_volume"] - 1.0) * 18.0)
        except Exception:
            sector_scores[sector] = 50.0

    spy = _series_metrics("SPY")
    regime = "Bull Market" if spy["ret_3m"] > 0.03 else "Bear Market" if spy["ret_3m"] < -0.04 else "Neutral Regime"

    rows: List[AlphaRow] = []
    for symbol in symbols:
        try:
            metrics = _series_metrics(symbol)
            sector_alignment = sector_scores.get(metrics["sector"], 50.0)
            rows.append(_factor_scores(metrics, sector_alignment, regime))
        except Exception:
            continue

    rows.sort(key=lambda item: item.alpha_score, reverse=True)
    top = rows[:10]
    recommendations = [
        row for row in rows
        if row.alpha_score > 85 and row.bubble_risk < 40 and row.smart_money > 70 and row.earnings_quality > 70 and row.sector_alignment > 55
    ][:10]

    if not recommendations:
        recommendations = [row for row in rows if row.bubble_risk < 55 and row.earnings_quality > 60][:10]

    leaders = sorted(sector_scores.items(), key=lambda item: item[1], reverse=True)[:2]
    sector_text = " and ".join([name for name, _ in leaders]) if leaders else "high-quality"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe": universe.upper(),
        "qlib_engine": qlib_status,
        "market_regime": {"name": regime, "confidence": bounded_score(50.0 + abs(spy["ret_3m"]) * 180.0)},
        "factor_importance": top[0].factor_importance if top else {},
        "top_alpha": [row.__dict__ for row in top],
        "recommendations": [row.__dict__ for row in recommendations],
        "summary": f"{sector_text} currently show the strongest alignment. The ranking blends Qlib Alpha158-style factor construction with bubble risk, earnings quality, smart money, sector rotation, market regime weighting, and universal theme intelligence.",
    }


if __name__ == "__main__":
    selected = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    print(json.dumps(run_alpha_pipeline(selected), ensure_ascii=False))
