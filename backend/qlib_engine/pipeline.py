from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np

from alpha_engine.scoring import bounded_score, calculate_bubble_index, confidence_label, data_completeness, partial_weighted_score
from quant_engine.data_pipeline import get_history, get_quote, safe_float

SP500_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "AVGO", "LLY", "JPM", "XOM",
    "UNH", "V", "MA", "COST", "HD", "PG", "JNJ", "ABBV", "MRK", "AMD",
]

NASDAQ100_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "GOOGL", "GOOG", "COST", "TSLA",
    "NFLX", "AMD", "ADBE", "PEP", "LIN", "CSCO", "TMUS", "INTU", "AMAT", "QCOM",
]

UNIVERSE_PRESETS = {
    "sp500": SP500_UNIVERSE,
    "nasdaq100": NASDAQ100_UNIVERSE,
    "dow30": ["AAPL", "MSFT", "NVDA", "AMZN", "JPM", "V", "WMT", "UNH", "HD", "PG", "JNJ", "KO", "MRK", "CRM", "MCD", "AXP", "IBM", "GS", "CAT", "DIS"],
    "russell2000": ["IWM", "SMCI", "PLTR", "CELH", "ELF", "ONTO", "FIX", "AIT", "FN", "SPSC", "MMSI", "RMBS", "UFPI", "SSD", "WING", "EXLS", "HQY", "BOOT", "CRS", "BMI"],
    "sox": ["NVDA", "AMD", "AVGO", "QCOM", "AMAT", "LRCX", "KLAC", "TSM", "ASML", "MRVL", "MU", "INTC", "TXN", "ADI", "NXPI", "MCHP", "ON", "MPWR", "TER", "QRVO"],
    "smh": ["NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "AMAT", "TXN", "LRCX", "MU", "ADI", "KLAC", "INTC", "MRVL", "NXPI", "MCHP", "ON", "MPWR", "TER", "QRVO"],
    "soxx": ["NVDA", "AVGO", "AMD", "QCOM", "AMAT", "LRCX", "KLAC", "MU", "INTC", "TXN", "ADI", "MRVL", "NXPI", "MCHP", "ON", "MPWR", "TER", "QRVO", "SWKS", "ENTG"],
    "xlk": ["MSFT", "AAPL", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "ADBE", "CSCO", "ACN", "NOW", "INTU", "QCOM", "IBM", "TXN", "AMAT", "LRCX", "MU", "PANW", "ANET"],
    "xle": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "WMB", "KMI", "HAL", "BKR", "DVN", "FANG", "HES", "TRGP", "OKE", "CTRA", "APA"],
    "xlf": ["JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP", "C", "BLK", "SCHW", "PGR", "CB", "MMC", "AIG", "TRV", "CME", "ICE", "SPGI", "MCO"],
    "xlv": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE", "TMO", "ABT", "DHR", "ISRG", "AMGN", "BSX", "GILD", "SYK", "MDT", "VRTX", "REGN", "CI", "CVS", "BMY"],
    "xli": ["GE", "CAT", "RTX", "HON", "UPS", "UNP", "BA", "DE", "ETN", "LMT", "ADP", "PH", "TT", "ITW", "EMR", "WM", "MMM", "NOC", "GD", "PWR"],
    "xlu": ["NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "PEG", "EXC", "XEL", "ED", "EIX", "WEC", "AWK", "PCG", "ETR", "DTE", "PPL", "FE", "CMS"],
    "xlb": ["LIN", "SHW", "APD", "ECL", "FCX", "NEM", "CTVA", "DD", "DOW", "NUE", "MLM", "VMC", "PPG", "IFF", "STLD", "BALL", "AVY", "CF", "MOS", "ALB"],
    "xly": ["AMZN", "TSLA", "HD", "MCD", "LOW", "BKNG", "TJX", "NKE", "SBUX", "ORLY", "CMG", "AZO", "MAR", "HLT", "DHI", "LEN", "GM", "F", "ROST", "YUM"],
    "xlp": ["WMT", "COST", "PG", "KO", "PEP", "PM", "MDLZ", "MO", "CL", "TGT", "KMB", "KDP", "GIS", "HSY", "SJM", "CAG", "KHC", "KR", "ADM", "TSN"],
    "iwm": ["IWM", "SMCI", "PLTR", "CELH", "ELF", "ONTO", "FIX", "AIT", "FN", "SPSC", "MMSI", "RMBS", "UFPI", "SSD", "WING", "EXLS", "HQY", "BOOT", "CRS", "BMI"],
    "dia": ["AAPL", "MSFT", "NVDA", "AMZN", "JPM", "V", "WMT", "UNH", "HD", "PG", "JNJ", "KO", "MRK", "CRM", "MCD", "AXP", "IBM", "GS", "CAT", "DIS"],
    "arkk": ["TSLA", "COIN", "ROKU", "SQ", "HOOD", "CRSP", "SHOP", "PLTR", "PATH", "TWLO", "U", "DKNG", "TDOC", "BEAM", "PACB", "EXAS", "DNA", "NTLA", "EDIT", "SOFI"],
    "ai_infrastructure": ["NVDA", "AMD", "AVGO", "ANET", "VRT", "ETN", "DELL", "SMCI", "PWR", "TT", "CARR", "TSM", "ASML", "AMAT", "LRCX"],
    "semiconductor": ["NVDA", "AMD", "AVGO", "QCOM", "AMAT", "LRCX", "KLAC", "TSM", "ASML", "MRVL", "MU", "INTC", "TXN", "ADI", "NXPI"],
    "memory_cycle": ["MU", "WDC", "STX", "AMAT", "LRCX", "KLAC", "NVDA", "AMD", "TSM", "DELL", "HPQ"],
    "glass_substrate": ["GLW", "AMAT", "INTC", "TSM", "KLAC", "ASML", "NVDA", "AMD"],
    "electric_grid": ["ETN", "PWR", "HUBB", "NEE", "SO", "DUK", "AEP", "CEG", "VST", "FCX", "SCCO"],
    "cable_copper": ["FCX", "SCCO", "TECK", "APH", "TEL", "GLW", "ETN", "PWR", "HUBB"],
    "nuclear_energy": ["CEG", "VST", "NEE", "SMR", "CCJ", "BWXT", "DUK", "SO", "AEP"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "WMB", "KMI"],
    "defense": ["LMT", "RTX", "NOC", "GD", "LHX", "BA", "HII", "TXT", "TDG", "GE"],
    "industrial_automation": ["ROK", "EMR", "HON", "ETN", "ITW", "PH", "ABBNY", "AME", "DOV", "FTV"],
    "shipping": ["ZIM", "DAC", "SBLK", "GNK", "MATX", "KEX", "UPS", "FDX", "XPO", "CHRW"],
    "commodities": ["FCX", "XOM", "CVX", "NEM", "SCCO", "TECK", "ALB", "MOS", "CF", "NUE", "STLD"],
    "traditional_industry": ["CAT", "DE", "EMR", "ITW", "DOW", "DD", "NUE", "STLD", "VMC", "MLM", "URI"],
    "healthcare_innovation": ["LLY", "ISRG", "REGN", "VRTX", "TMO", "DHR", "BSX", "SYK", "ABT", "MRNA"],
    "financial_rotation": ["JPM", "BAC", "GS", "MS", "V", "MA", "AXP", "BLK", "SCHW", "CME", "ICE"],
}

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
    confidence_score: float
    confidence_label: str
    bullish_factors: List[str]
    risk_factors: List[str]


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
    completeness = data_completeness({
        "price": latest,
        "volume": avg_volume,
        "revenue_growth": revenue_growth,
        "gross_margin": gross_margin,
        "free_cash_flow": fcf,
        "operating_cash_flow": operating_cash,
        "market_cap": safe_float(info.get("marketCap")),
        "pe": pe,
        "ps": ps,
    })

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
        "data_completeness": completeness,
    }


def _factor_scores(metrics: Dict[str, Any], sector_alignment: float, regime: str) -> AlphaRow:
    try:
        from theme_engine import theme_alignment_for_symbol

        theme_signal = theme_alignment_for_symbol(metrics["ticker"], metrics["sector"])
    except Exception:
        theme_signal = {
            "theme_alignment": 44.0,
            "theme_strength": 42.0,
            "theme_capital_flow": 43.0,
            "explanation": ["Theme engine unavailable; stock-level alpha factors remain active."],
        }

    theme_alignment = safe_float(theme_signal.get("theme_alignment"))
    theme_strength = safe_float(theme_signal.get("theme_strength"))
    theme_capital_flow = safe_float(theme_signal.get("theme_capital_flow"))
    theme_explanation = list(theme_signal.get("explanation") or [])
    momentum_score = bounded_score(48.0 + metrics["ret_3m"] * 145.0 + metrics["ret_6m"] * 60.0 + metrics["acceleration"] * 110.0)
    earnings_quality = bounded_score(46.0 + (metrics["free_cash_flow"] / max(abs(metrics["operating_cash_flow"]), 1.0)) * 42.0 + metrics["net_income_margin"] * 68.0 + metrics["gross_margin"] * 24.0)
    smart_money = bounded_score(45.0 + (metrics["relative_volume"] - 1.0) * 20.0 + metrics["ret_1m"] * 85.0 + metrics["acceleration"] * 105.0)
    valuation = bounded_score(82.0 - max(0.0, metrics["pe"] - 18.0) * 0.85 - max(0.0, metrics["ps"] - 4.0) * 2.8 + max(0.0, metrics["free_cash_flow"]) / 2_200_000_000.0)
    free_cash_flow_score = bounded_score(42.0 + max(-1.0, min(1.8, metrics["free_cash_flow"] / max(abs(metrics["operating_cash_flow"]), 1.0))) * 34.0)
    relative_strength_score = bounded_score(50.0 + metrics["ret_3m"] * 120.0 + sector_alignment * 0.25)
    volatility_compression_score = bounded_score(82.0 - metrics["volatility"] * 105.0 + max(0.0, metrics["ret_3m"]) * 35.0)
    balance_sheet_strength_score = bounded_score(74.0 - metrics["debt_to_equity"] * 24.0 + metrics["net_income_margin"] * 38.0)
    regime_alignment_score = bounded_score(55.0 + metrics["ret_3m"] * 95.0) if regime != "Bear Market" else bounded_score(60.0 + valuation * 0.18 + free_cash_flow_score * 0.22 - metrics["volatility"] * 25.0)
    growth = bounded_score(48.0 + metrics["revenue_growth"] * 125.0 + metrics["ret_3m"] * 55.0)
    quality = bounded_score(earnings_quality * 0.52 + balance_sheet_strength_score * 0.28 + free_cash_flow_score * 0.20)
    market_structure = bounded_score(momentum_score * 0.35 + relative_strength_score * 0.28 + volatility_compression_score * 0.17 + sector_alignment * 0.12 + theme_alignment * 0.08)

    weights = {
        "momentum_score": 0.15,
        "earnings_quality_score": 0.15,
        "smart_money_score": 0.12,
        "sector_strength_score": 0.10,
        "theme_alignment_score": 0.10,
        "valuation_score": 0.08,
        "free_cash_flow_score": 0.08,
        "relative_strength_score": 0.07,
        "volatility_compression_score": 0.05,
        "balance_sheet_strength_score": 0.05,
        "regime_alignment_score": 0.05,
    }
    if regime == "Bear Market":
        weights.update({"earnings_quality_score": 0.18, "valuation_score": 0.11, "free_cash_flow_score": 0.11, "balance_sheet_strength_score": 0.08, "momentum_score": 0.10})
    elif regime == "Momentum Mania":
        weights.update({"theme_alignment_score": 0.13, "momentum_score": 0.17, "volatility_compression_score": 0.03, "valuation_score": 0.06})
    factor_values = {
        "momentum_score": (momentum_score, weights["momentum_score"]),
        "earnings_quality_score": (earnings_quality, weights["earnings_quality_score"]),
        "smart_money_score": (smart_money, weights["smart_money_score"]),
        "sector_strength_score": (sector_alignment, weights["sector_strength_score"]),
        "theme_alignment_score": (theme_alignment, weights["theme_alignment_score"]),
        "valuation_score": (valuation, weights["valuation_score"]),
        "free_cash_flow_score": (free_cash_flow_score, weights["free_cash_flow_score"]),
        "relative_strength_score": (relative_strength_score, weights["relative_strength_score"]),
        "volatility_compression_score": (volatility_compression_score, weights["volatility_compression_score"]),
        "balance_sheet_strength_score": (balance_sheet_strength_score, weights["balance_sheet_strength_score"]),
        "regime_alignment_score": (regime_alignment_score, weights["regime_alignment_score"]),
    }
    raw_alpha, factor_completeness = partial_weighted_score(factor_values, neutral=46.0)
    bubble_penalty = max(0.0, metrics["bubble_risk"] - 60.0) * (0.32 if regime == "Momentum Mania" else 0.22)
    liquidity_weight = min(1.0, max(0.72, metrics["market_cap"] / 25_000_000_000.0)) if metrics["market_cap"] > 0 else 0.82
    alpha_score = bounded_score(raw_alpha * liquidity_weight + 50.0 * (1.0 - liquidity_weight) - bubble_penalty)
    confidence_score = bounded_score(metrics.get("data_completeness", 0.0) * 0.55 + factor_completeness * 0.30 + min(metrics["market_cap"], 50_000_000_000.0) / 50_000_000_000.0 * 15.0)
    bullish_factors = []
    risk_factors = []
    if momentum_score >= 68:
        bullish_factors.append("Relative momentum is leading the market.")
    if smart_money >= 65:
        bullish_factors.append("Volume structure suggests institutional accumulation.")
    if earnings_quality >= 65:
        bullish_factors.append("Earnings quality and cash conversion support the ranking.")
    if theme_alignment >= 65:
        bullish_factors.append("Theme alignment is positive.")
    if metrics["bubble_risk"] >= 65:
        risk_factors.append("Bubble risk is elevated and reduces alpha conviction.")
    if confidence_score < 55:
        risk_factors.append("Partial data coverage lowers model confidence.")
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
        confidence_score=confidence_score,
        confidence_label=confidence_label(confidence_score),
        bullish_factors=bullish_factors,
        risk_factors=risk_factors,
    )


def run_alpha_pipeline(universe: str = "sp500", qlib_available: bool | None = None) -> Dict[str, Any]:
    qlib_status = _try_init_qlib(qlib_available)
    universe_key = universe.lower().strip().replace(" ", "_").replace("/", "_").replace("-", "_")
    symbols = sorted(set(UNIVERSE_PRESETS.get(universe_key, SP500_UNIVERSE)))

    sector_scores: Dict[str, float] = {}
    for sector, etf in SECTOR_ETFS.items():
        try:
            m = _series_metrics(etf)
            sector_scores[sector] = bounded_score(50.0 + m["ret_3m"] * 150.0 + (m["relative_volume"] - 1.0) * 18.0)
        except Exception:
            sector_scores[sector] = 42.0

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
        "universe": universe_key.upper(),
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
