from __future__ import annotations

from typing import Any, Dict

import numpy as np

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.data_pipeline import get_history, get_quote, safe_float


def analyze_smart_money(symbol: str, quote: Dict[str, Any] | None = None) -> Dict[str, Any]:
    ticker = symbol.strip().upper()
    quote = quote if isinstance(quote, dict) else get_quote(ticker)
    history = get_history(ticker, "9mo")
    if history is None or history.empty or len(history) < 64:
        volume = safe_float(quote.get("regularMarketVolume") or quote.get("volume"))
        average_volume = safe_float(quote.get("averageVolume") or quote.get("averageDailyVolume10Day"))
        market_cap = safe_float(quote.get("marketCap"))
        relative_volume = volume / max(average_volume, 1.0) if volume > 0 and average_volume > 0 else None
        liquidity_quality = bounded_score(35.0 + min(market_cap, 500_000_000_000.0) / 10_000_000_000.0 + min(volume, 50_000_000.0) / 1_200_000.0) if market_cap > 0 or volume > 0 else None
        abnormal_volume = bounded_score(48.0 + (relative_volume - 1.0) * 26.0) if relative_volume is not None else None
        available = sum(value is not None for value in [relative_volume, liquidity_quality, abnormal_volume])
        confidence = bounded_score(available / 3.0 * 100.0)
        base = [value for value in [liquidity_quality, abnormal_volume] if value is not None]
        score = bounded_score(float(np.mean(base)) - (100.0 - confidence) * 0.18) if base else None
        return {
            "ticker": ticker,
            "smart_money_score": score,
            "institutional_flow": "Partial Data",
            "confidence": round(confidence / 100.0, 3),
            "confidence_score": confidence,
            "confidence_label": confidence_label(confidence),
            "data_completeness": confidence,
            "accumulation": None,
            "abnormal_volume": abnormal_volume,
            "relative_volume": round(relative_volume, 3) if relative_volume is not None else None,
            "institutional_footprint": liquidity_quality,
            "price_volume_divergence": None,
            "stealth_accumulation": None,
            "bullish_factors": ["Liquidity profile is available from quote data."] if liquidity_quality is not None else [],
            "risk_factors": ["Insufficient price and volume history; treating signal as partial data."],
            "summary": "Partial Data: live quote liquidity is available, but historical accumulation confirmation is still calibrating.",
        }

    close = history["Close"].astype(float)
    volume = history["Volume"].astype(float)
    latest = float(close.iloc[-1])
    ret_1m = latest / float(close.iloc[-22]) - 1.0
    ret_3m = latest / float(close.iloc[-64]) - 1.0
    avg_volume_20 = float(volume.tail(20).mean())
    avg_volume_60 = float(volume.tail(60).mean())
    relative_volume = float(volume.iloc[-1]) / max(avg_volume_60, 1.0)
    up_days = close.diff() > 0
    down_days = close.diff() < 0
    up_volume = float(volume[up_days].tail(60).sum())
    down_volume = float(volume[down_days].tail(60).sum())
    accumulation_ratio = up_volume / max(up_volume + down_volume, 1.0)
    price_volume_divergence = relative_volume - max(0.0, abs(ret_1m) * 8.0)
    low_range = float((close.tail(20).max() - close.tail(20).min()) / max(close.tail(20).min(), 1.0))

    accumulation = bounded_score(50.0 + (accumulation_ratio - 0.5) * 120.0 + ret_3m * 55.0)
    abnormal_volume = bounded_score(50.0 + (relative_volume - 1.0) * 28.0)
    institutional_footprint = bounded_score(45.0 + price_volume_divergence * 22.0 + accumulation_ratio * 35.0)
    stealth_accumulation = bounded_score(55.0 + max(0.0, relative_volume - 1.0) * 18.0 + max(0.0, 0.08 - low_range) * 180.0)
    score = bounded_score(accumulation * 0.34 + abnormal_volume * 0.22 + institutional_footprint * 0.26 + stealth_accumulation * 0.18)
    market_cap = safe_float(quote.get("marketCap"))
    liquidity_quality = bounded_score(40.0 + min(market_cap, 700_000_000_000.0) / 12_000_000_000.0 + min(avg_volume_60, 70_000_000.0) / 1_500_000.0)
    if market_cap < 2_000_000_000 and relative_volume > 2.5:
        score = bounded_score(score - 10.0)
    confidence_score = bounded_score(min(len(history), 189) / 189.0 * 45.0 + min(avg_volume_60, 20_000_000.0) / 20_000_000.0 * 25.0 + liquidity_quality * 0.30)
    bullish_factors = []
    risk_factors = []
    if accumulation >= 62:
        bullish_factors.append("Accumulation ratio shows more volume on advancing sessions.")
    if abnormal_volume >= 62:
        bullish_factors.append("Relative volume is expanding above its 60-day baseline.")
    if stealth_accumulation >= 65:
        bullish_factors.append("Volatility compression with elevated participation suggests stealth accumulation.")
    if score < 45:
        risk_factors.append("Price-volume structure lacks institutional confirmation.")
    if market_cap < 2_000_000_000 and relative_volume > 2.5:
        risk_factors.append("Small-cap liquidity adjustment reduces confidence in one-day volume spikes.")

    return {
        "ticker": ticker,
        "smart_money_score": score,
        "institutional_flow": "Positive" if score >= 65 else "Negative" if score <= 40 else "Neutral",
        "confidence": round(confidence_score / 100.0, 3),
        "confidence_score": confidence_score,
        "confidence_label": confidence_label(confidence_score),
        "data_completeness": confidence_score,
        "accumulation": accumulation,
        "abnormal_volume": abnormal_volume,
        "relative_volume": round(relative_volume, 3),
        "volume_structure": round(avg_volume_20 / max(avg_volume_60, 1.0), 3),
        "institutional_footprint": institutional_footprint,
        "price_volume_divergence": round(price_volume_divergence, 3),
        "stealth_accumulation": stealth_accumulation,
        "liquidity_quality": liquidity_quality,
        "dark_pool_style_signal": score >= 72 and low_range < 0.08,
        "bullish_factors": bullish_factors,
        "risk_factors": risk_factors,
        "summary": "Volume structure receives higher weight than delayed 13F signals. The score emphasizes accumulation, abnormal participation, price-volume divergence, and stealth accumulation behavior.",
    }
