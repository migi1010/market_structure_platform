from __future__ import annotations

from typing import Any, Dict

import numpy as np

from alpha_engine.scoring import bounded_score
from quant_engine.data_pipeline import get_history


def analyze_smart_money(symbol: str) -> Dict[str, Any]:
    ticker = symbol.strip().upper()
    history = get_history(ticker, "9mo")
    if history is None or history.empty or len(history) < 64:
        return {
            "ticker": ticker,
            "smart_money_score": 50.0,
            "institutional_flow": "Neutral",
            "confidence": 0.5,
            "accumulation": 50.0,
            "abnormal_volume": 50.0,
            "institutional_footprint": 50.0,
            "price_volume_divergence": 0.0,
            "stealth_accumulation": 50.0,
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

    return {
        "ticker": ticker,
        "smart_money_score": score,
        "institutional_flow": "Positive" if score >= 65 else "Negative" if score <= 40 else "Neutral",
        "confidence": round(score / 100.0, 3),
        "accumulation": accumulation,
        "abnormal_volume": abnormal_volume,
        "relative_volume": round(relative_volume, 3),
        "volume_structure": round(avg_volume_20 / max(avg_volume_60, 1.0), 3),
        "institutional_footprint": institutional_footprint,
        "price_volume_divergence": round(price_volume_divergence, 3),
        "stealth_accumulation": stealth_accumulation,
        "dark_pool_style_signal": score >= 72 and low_range < 0.08,
        "summary": "Volume structure receives higher weight than delayed 13F signals. The score emphasizes accumulation, abnormal participation, price-volume divergence, and stealth accumulation behavior.",
    }
