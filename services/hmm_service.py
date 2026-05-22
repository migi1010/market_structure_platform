from __future__ import annotations

import os
from typing import Dict

import yfinance as yf

from market_structure.regime_hmm import MarketRegimeHMM


def run_hmm_prediction(symbol: str) -> Dict[str, float | str]:
    model_path = "./models/market_regime_hmm.pkl"
    hmm = MarketRegimeHMM()
    if os.path.exists(model_path):
        hmm.load_model(model_path)
    if not hmm.is_fitted:
        hmm.train(period="5y")
        hmm.save_model(model_path)

    history = yf.download(symbol.strip().upper(), period="8mo", progress=False)
    probabilities = hmm.get_regime_probabilities(history)
    latest = probabilities[-1]
    predictions = hmm.predict(history)
    current_state = int(predictions[-1])
    regime_state = hmm.regime_mapping.get(current_state, f"State {current_state}")

    bear_probability = float(latest[current_state]) if "Bear" in regime_state else float(min(0.95, latest.max() * 0.45))
    bull_probability = float(max(0.05, 1.0 - bear_probability))
    predicted_trend = "Bullish" if bull_probability >= bear_probability else "Bearish"

    return {
        "predicted_trend": predicted_trend,
        "bull_probability": round(bull_probability, 4),
        "bear_probability": round(bear_probability, 4),
        "regime_state": regime_state,
        "confidence": round(float(latest.max()), 2),
    }
