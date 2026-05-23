from __future__ import annotations

import math
from datetime import datetime, timezone
from functools import lru_cache
from statistics import mean
from typing import Any, Dict, List

import numpy as np

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.data_pipeline import get_history, get_quote, safe_float

from .theme_detector import ThemeDefinition


def _pct(now: float, then: float) -> float:
    return now / then - 1.0 if then > 0 else 0.0


def _avg(values: List[float], default: float = 0.0) -> float:
    usable = [value for value in values if math.isfinite(value)]
    return float(mean(usable)) if usable else default


@lru_cache(maxsize=512)
def symbol_market_snapshot(symbol: str, use_history: bool = False) -> Dict[str, Any]:
    normalized = symbol.strip().upper()
    quote = get_quote(normalized)
    price = safe_float(quote.get("currentPrice") or quote.get("regularMarketPrice") or quote.get("previousClose"))
    day_change = safe_float(quote.get("regularMarketChangePercent")) / 100.0
    revenue_growth = safe_float(quote.get("revenueGrowth"))
    earnings_growth = safe_float(quote.get("earningsQuarterlyGrowth") or quote.get("earningsGrowth"))
    gross_margin = safe_float(quote.get("grossMargins"))
    operating_margin = safe_float(quote.get("operatingMargins"))
    volume = safe_float(quote.get("regularMarketVolume") or quote.get("volume"))
    avg_volume = safe_float(quote.get("averageVolume") or quote.get("averageDailyVolume10Day"))
    relative_volume = volume / max(avg_volume, 1.0) if volume > 0 else 1.0
    beta = safe_float(quote.get("beta"))
    market_cap = safe_float(quote.get("marketCap"))
    forward_pe = safe_float(quote.get("forwardPE") or quote.get("trailingPE"))
    ps = safe_float(quote.get("priceToSalesTrailing12Months"))
    one_year_change = safe_float(quote.get("52WeekChange"))
    if abs(one_year_change) > 3.0:
        one_year_change = one_year_change / 100.0

    ret_1m = day_change * 8.0
    ret_3m = one_year_change / 4.0 if one_year_change else day_change * 20.0
    ret_6m = one_year_change / 2.0 if one_year_change else day_change * 40.0
    volatility = 0.30 + max(0.0, beta - 1.0) * 0.12 if beta else 0.34

    if use_history:
        try:
            history = get_history(normalized, "9mo")
            if history is not None and not history.empty and len(history) >= 64:
                close = history["Close"].astype(float)
                volume_series = history["Volume"].astype(float)
                latest = float(close.iloc[-1])
                if latest > 0:
                    price = latest
                ret_1m = _pct(latest, float(close.iloc[-22]))
                ret_3m = _pct(latest, float(close.iloc[-64]))
                ret_6m = _pct(latest, float(close.iloc[0]))
                returns = close.pct_change().dropna()
                volatility = float(returns.tail(64).std() * np.sqrt(252)) if len(returns) > 10 else volatility
                avg_history_volume = float(volume_series.tail(60).mean()) if len(volume_series) else avg_volume
                relative_volume = float(volume_series.iloc[-1]) / max(avg_history_volume, 1.0)
        except Exception:
            pass

    acceleration = ret_1m - ret_3m / 3.0
    quality_proxy = bounded_score(50.0 + gross_margin * 70.0 + operating_margin * 65.0 + max(0.0, revenue_growth) * 55.0)
    valuation_heat = bounded_score(max(0.0, forward_pe - 20.0) * 1.1 + max(0.0, ps - 4.0) * 4.0)
    return {
        "symbol": normalized,
        "price": price,
        "ret_1m": ret_1m,
        "ret_3m": ret_3m,
        "ret_6m": ret_6m,
        "acceleration": acceleration,
        "relative_volume": relative_volume,
        "volatility": volatility,
        "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth,
        "quality_proxy": quality_proxy,
        "market_cap": market_cap,
        "valuation_heat": valuation_heat,
        "day_change_percent": day_change * 100.0,
    }


def _macro_snapshot() -> Dict[str, Any]:
    symbols = {
        "SPY": "equities",
        "QQQ": "growth",
        "SOXX": "semiconductors",
        "VIXY": "volatility",
        "DX-Y.NYB": "dollar",
        "^TNX": "ten_year_yield",
        "HYG": "credit",
        "BTC-USD": "crypto_liquidity",
        "GC=F": "gold",
        "CL=F": "oil",
    }
    values = {}
    for symbol, key in symbols.items():
        values[key] = symbol_market_snapshot(symbol, use_history=True)
    spy = values["equities"]
    qqq = values["growth"]
    vix = values["volatility"]
    hyg = values["credit"]
    oil = values["oil"]
    gold = values["gold"]
    risk_on_score = bounded_score(50.0 + spy["ret_3m"] * 180.0 + qqq["ret_1m"] * 120.0 + hyg["ret_3m"] * 110.0 - max(0.0, vix["ret_1m"]) * 90.0)
    liquidity_score = bounded_score(50.0 + qqq["ret_3m"] * 130.0 + values["crypto_liquidity"]["ret_3m"] * 35.0 - values["dollar"]["ret_3m"] * 80.0)
    volatility_score = bounded_score(50.0 + vix["ret_1m"] * 160.0 + max(0.0, spy["volatility"] - 0.22) * 120.0)
    inflation_score = bounded_score(50.0 + oil["ret_3m"] * 120.0 + gold["ret_3m"] * 80.0 + values["ten_year_yield"]["ret_3m"] * 40.0)
    ai_capex_score = bounded_score(50.0 + values["semiconductors"]["ret_3m"] * 160.0 + qqq["ret_3m"] * 90.0)
    return {
        "risk_on_off": "Risk-On" if risk_on_score >= 58 else "Risk-Off" if risk_on_score <= 42 else "Neutral",
        "risk_on_score": risk_on_score,
        "liquidity_regime": "Expanding" if liquidity_score >= 58 else "Tightening" if liquidity_score <= 42 else "Neutral",
        "liquidity_score": liquidity_score,
        "volatility_regime": "High Volatility" if volatility_score >= 62 else "Compressed" if volatility_score <= 38 else "Normal",
        "volatility_score": volatility_score,
        "inflation_regime": "Inflationary" if inflation_score >= 58 else "Disinflationary" if inflation_score <= 42 else "Balanced",
        "inflation_score": inflation_score,
        "AI_capex_regime": "Accelerating" if ai_capex_score >= 60 else "Cooling" if ai_capex_score <= 42 else "Stable",
        "AI_capex_score": ai_capex_score,
    }


def detect_cross_asset_regime() -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **_macro_snapshot(),
    }


def score_theme(theme: ThemeDefinition, spy_snapshot: Dict[str, Any] | None = None, macro: Dict[str, Any] | None = None) -> Dict[str, Any]:
    spy = spy_snapshot or symbol_market_snapshot("SPY", use_history=True)
    macro_state = macro or _macro_snapshot()
    etf_metrics = [symbol_market_snapshot(symbol, use_history=True) for symbol in theme.etf_symbols]
    equity_metrics = [symbol_market_snapshot(symbol, use_history=False) for symbol in theme.tickers[:8]]
    leaders = sorted(equity_metrics, key=lambda item: item["ret_3m"], reverse=True)[:4]

    etf_momentum = _avg([item["ret_3m"] for item in etf_metrics], _avg([item["ret_3m"] for item in equity_metrics]))
    equity_momentum = _avg([item["ret_3m"] for item in equity_metrics])
    relative_momentum = equity_momentum - spy["ret_3m"]
    etf_relative_strength = etf_momentum - spy["ret_3m"]
    volume_expansion = _avg([item["relative_volume"] for item in equity_metrics], 1.0)
    earnings_acceleration = _avg([item["earnings_growth"] for item in equity_metrics])
    revenue_acceleration = _avg([item["revenue_growth"] for item in equity_metrics])
    capex_trend = bounded_score(50.0 + max(0.0, revenue_acceleration) * 80.0 + max(0.0, earnings_acceleration) * 50.0)
    breadth = sum(1 for item in equity_metrics if item["ret_1m"] > 0 or item["ret_3m"] > 0) / max(len(equity_metrics), 1)
    leadership_concentration = (max([item["market_cap"] for item in equity_metrics] or [0.0]) / max(sum(item["market_cap"] for item in equity_metrics), 1.0)) if equity_metrics else 0.0
    smart_money_accumulation = bounded_score(50.0 + (volume_expansion - 1.0) * 24.0 + max(0.0, relative_momentum) * 170.0 + max(0.0, breadth - 0.5) * 40.0)
    institutional_accumulation = bounded_score(smart_money_accumulation * 0.65 + max(0.0, etf_relative_strength) * 150.0)
    options_activity = bounded_score(48.0 + (volume_expansion - 1.0) * 22.0 + max(0.0, _avg([item["volatility"] for item in leaders], 0.3) - 0.30) * 70.0)
    valuation_heat = _avg([item["valuation_heat"] for item in equity_metrics], 45.0)
    supply_chain_acceleration = bounded_score(50.0 + _avg([item["acceleration"] for item in equity_metrics]) * 220.0 + revenue_acceleration * 70.0)

    narrative = _narrative_proxy(theme, equity_metrics)
    macro_alignment = _macro_alignment(theme, macro_state)
    relative_momentum_score = bounded_score(50.0 + relative_momentum * 95.0)
    etf_relative_strength_score = bounded_score(50.0 + etf_relative_strength * 95.0)
    volume_score = bounded_score(50.0 + (volume_expansion - 1.0) * 18.0)
    earnings_score = bounded_score(50.0 + earnings_acceleration * 72.0)
    revenue_score = bounded_score(50.0 + revenue_acceleration * 72.0)
    breadth_score = bounded_score(breadth * 100.0)
    leadership_balance_score = bounded_score(100.0 - min(100.0, leadership_concentration * 150.0))
    theme_strength_score = bounded_score(
        relative_momentum_score * 0.16
        + etf_relative_strength_score * 0.11
        + volume_score * 0.09
        + institutional_accumulation * 0.12
        + earnings_score * 0.08
        + revenue_score * 0.08
        + capex_trend * 0.07
        + smart_money_accumulation * 0.08
        + narrative["narrative_acceleration"] * 0.06
        + breadth_score * 0.06
        + leadership_balance_score * 0.03
        + options_activity * 0.03
        + supply_chain_acceleration * 0.03
        + macro_alignment * 0.10
    )
    capital_flow_score = bounded_score(
        smart_money_accumulation * 0.34
        + institutional_accumulation * 0.28
        + relative_momentum_score * 0.18
        + breadth_score * 0.12
        + options_activity * 0.08
    )
    emerging_score = bounded_score(
        bounded_score(_avg([item["acceleration"] for item in equity_metrics]) * 120.0 + 48.0) * 0.32
        + capital_flow_score * 0.28
        + narrative["narrative_acceleration"] * 0.18
        + supply_chain_acceleration * 0.12
        + macro_alignment * 0.10
    )
    overheating_score = bounded_score(valuation_heat * 0.38 + narrative["narrative_saturation"] * 0.22 + max(0.0, leadership_concentration * 100.0 - 35.0) * 0.28 + options_activity * 0.12)
    theme_strength_score = bounded_score(theme_strength_score - max(0.0, overheating_score - 72.0) * 0.16)
    capital_flow_score = bounded_score(capital_flow_score - max(0.0, overheating_score - 82.0) * 0.10)
    data_completeness = bounded_score(
        min(len([item for item in equity_metrics if item["price"] > 0]), max(len(theme.tickers[:8]), 1)) / max(len(theme.tickers[:8]), 1) * 36.0
        + min(len(etf_metrics), max(len(theme.etf_symbols), 1)) / max(len(theme.etf_symbols), 1) * 22.0
        + min(100.0, breadth * 100.0) * 0.18
        + min(100.0, max(0.0, volume_expansion) * 50.0) * 0.12
        + macro_alignment * 0.12
    )
    confidence_score = bounded_score(data_completeness - max(0.0, overheating_score - 82.0) * 0.10)
    status = _theme_status(theme_strength_score, emerging_score, overheating_score, capital_flow_score)

    return {
        "theme": theme.name,
        "category": theme.category,
        "description": theme.description,
        "theme_strength_score": theme_strength_score,
        "theme_capital_flow_score": capital_flow_score,
        "emerging_score": emerging_score,
        "overheating_score": overheating_score,
        "status": status,
        "confidence_score": confidence_score,
        "confidence_label": confidence_label(confidence_score),
        "data_completeness": data_completeness,
        "relative_momentum": round(relative_momentum * 100.0, 2),
        "etf_relative_strength": round(etf_relative_strength * 100.0, 2),
        "volume_expansion": round(volume_expansion, 2),
        "institutional_accumulation": institutional_accumulation,
        "earnings_acceleration": round(earnings_acceleration * 100.0, 2),
        "revenue_acceleration": round(revenue_acceleration * 100.0, 2),
        "capex_trend": capex_trend,
        "smart_money_accumulation": smart_money_accumulation,
        "narrative_strength": narrative["narrative_strength"],
        "narrative_acceleration": narrative["narrative_acceleration"],
        "narrative_saturation": narrative["narrative_saturation"],
        "narrative_bubble_risk": narrative["narrative_bubble_risk"],
        "breadth_participation": round(breadth * 100.0, 2),
        "leadership_concentration": round(leadership_concentration * 100.0, 2),
        "relative_strength_vs_spy": round(relative_momentum * 100.0, 2),
        "options_activity": options_activity,
        "supply_chain_acceleration": supply_chain_acceleration,
        "macro_alignment": macro_alignment,
        "leaders": [
            {
                "ticker": item["symbol"],
                "momentum_3m": round(item["ret_3m"] * 100.0, 2),
                "relative_volume": round(item["relative_volume"], 2),
                "day_change_percent": round(item["day_change_percent"], 2),
            }
            for item in leaders
        ],
        "etfs": list(theme.etf_symbols),
        "macro_tags": list(theme.macro_alignment),
        "explainability": _explain_theme(theme.name, theme_strength_score, capital_flow_score, macro_alignment, narrative["narrative_acceleration"]),
        "risks": _theme_risks(overheating_score, valuation_heat, narrative["narrative_saturation"], confidence_score),
    }


def _theme_status(strength: float, emerging: float, overheating: float, flow: float) -> str:
    if strength < 38 and flow < 42:
        return "Weak"
    if overheating >= 78 and strength >= 65:
        return "Overheated"
    if strength >= 82 and flow >= 70:
        return "Leadership"
    if emerging >= 68 and flow >= 58:
        return "Emerging"
    if strength >= 62 and flow >= 58:
        return "Accumulating"
    if strength < 48 and flow < 50:
        return "Cooling"
    return "Watchlist"


def _theme_risks(overheating: float, valuation_heat: float, narrative_saturation: float, confidence: float) -> List[str]:
    risks: List[str] = []
    if overheating >= 72:
        risks.append("Theme is showing overheating risk from valuation, narrative saturation, or leadership concentration.")
    if valuation_heat >= 65:
        risks.append("Valuation premium is elevated across the theme basket.")
    if narrative_saturation >= 72:
        risks.append("Narrative saturation is rising and may reduce forward alpha.")
    if confidence < 55:
        risks.append("Theme signal is based on partial data coverage.")
    if not risks:
        risks.append("No major theme-level risk concentration detected.")
    return risks


def _macro_alignment(theme: ThemeDefinition, macro: Dict[str, Any]) -> float:
    scores: List[float] = []
    for tag in theme.macro_alignment:
        if tag == "risk_on":
            scores.append(safe_float(macro.get("risk_on_score")))
        elif tag == "risk_off":
            scores.append(100.0 - safe_float(macro.get("risk_on_score")))
        elif tag == "liquidity":
            scores.append(safe_float(macro.get("liquidity_score")))
        elif tag == "AI_capex":
            scores.append(safe_float(macro.get("AI_capex_score")))
        elif tag == "inflation":
            scores.append(safe_float(macro.get("inflation_score")))
        elif tag == "rates_down":
            ten_year = symbol_market_snapshot("^TNX", use_history=True)
            scores.append(bounded_score(55.0 - ten_year["ret_3m"] * 120.0))
        elif tag == "oil":
            oil = symbol_market_snapshot("CL=F", use_history=True)
            scores.append(bounded_score(50.0 + oil["ret_3m"] * 130.0))
        elif tag == "global_trade":
            scores.append(bounded_score(50.0 + symbol_market_snapshot("IYT", use_history=True)["ret_3m"] * 150.0))
        elif tag == "defensive":
            scores.append(bounded_score(50.0 + max(0.0, 50.0 - safe_float(macro.get("risk_on_score"))) * 0.8))
        elif tag in {"fiscal", "capex", "rates"}:
            scores.append(55.0)
    return bounded_score(_avg(scores, 50.0))


def _narrative_proxy(theme: ThemeDefinition, equity_metrics: List[Dict[str, Any]]) -> Dict[str, float]:
    acceleration = _avg([item["acceleration"] for item in equity_metrics])
    volume = _avg([item["relative_volume"] for item in equity_metrics], 1.0)
    revenue = _avg([item["revenue_growth"] for item in equity_metrics])
    momentum = _avg([item["ret_3m"] for item in equity_metrics])
    keyword_depth = min(len(theme.narrative_keywords), 8)
    narrative_acceleration = bounded_score(45.0 + max(0.0, acceleration) * 260.0 + max(0.0, volume - 1.0) * 18.0 + max(0.0, revenue) * 42.0)
    narrative_strength = bounded_score(42.0 + max(0.0, momentum) * 120.0 + keyword_depth * 2.5 + max(0.0, volume - 1.0) * 12.0)
    narrative_saturation = bounded_score(max(28.0, narrative_strength - 8.0) + max(0.0, momentum) * 55.0)
    return {
        "narrative_strength": narrative_strength,
        "narrative_acceleration": narrative_acceleration,
        "narrative_saturation": narrative_saturation,
        "narrative_bubble_risk": bounded_score(narrative_saturation * 0.62 + max(0.0, narrative_acceleration - 72.0) * 0.35),
    }


def _explain_theme(theme: str, strength: float, flow: float, macro: float, narrative: float) -> List[str]:
    reasons: List[str] = []
    if strength >= 75:
        reasons.append(f"{theme} is showing strong cross-sectional relative momentum.")
    if flow >= 70:
        reasons.append("Capital flow proxy indicates institutional accumulation and breadth expansion.")
    if macro >= 65:
        reasons.append("Cross-asset regime is aligned with the theme.")
    if narrative >= 68:
        reasons.append("Narrative acceleration is visible in available news and market proxies.")
    if not reasons:
        reasons.append("Theme remains watchlist-worthy but lacks broad confirmation across factors.")
    return reasons
