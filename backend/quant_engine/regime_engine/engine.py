from __future__ import annotations

from typing import Any, Dict

import numpy as np

from alpha_engine.scoring import bounded_score
from quant_engine.data_pipeline import get_history


def detect_market_regime() -> Dict[str, Any]:
    spy = get_history("SPY", "3y")
    qqq = get_history("QQQ", "3y")
    if spy.empty or len(spy) < 120:
        return {"name": "Neutral Regime", "confidence": 50.0, "states": []}

    close = spy["Close"].astype(float)
    returns = close.pct_change().dropna()
    vol = float(returns.tail(30).std() * np.sqrt(252)) if len(returns) > 30 else 0.25
    ret_1m = float(close.iloc[-1] / close.iloc[-22] - 1.0)
    ret_3m = float(close.iloc[-1] / close.iloc[-64] - 1.0)
    ret_6m = float(close.iloc[-1] / close.iloc[-126] - 1.0) if len(close) > 126 else ret_3m
    qqq_close = qqq["Close"].astype(float) if not qqq.empty else close
    qqq_ret = float(qqq_close.iloc[-1] / qqq_close.iloc[-64] - 1.0) if len(qqq_close) > 64 else ret_3m

    hmm_state = None
    try:
        from hmmlearn.hmm import GaussianHMM

        features = np.column_stack([
            returns.tail(500).values,
            returns.tail(500).rolling(20).std().fillna(returns.std()).values,
        ])
        model = GaussianHMM(n_components=5, covariance_type="diag", n_iter=200, random_state=42)
        model.fit(features)
        hidden = model.predict(features)
        current = int(hidden[-1])
        state_ret = float(features[hidden == current, 0].mean())
        state_vol = float(features[hidden == current, 1].mean() * np.sqrt(252))
        hmm_state = {"state": current, "mean_return": state_ret, "annualized_volatility": state_vol}
    except Exception:
        hmm_state = {"state": -1, "mean_return": float(returns.tail(60).mean()), "annualized_volatility": vol}

    if ret_3m > 0.10 and qqq_ret > ret_3m and vol > 0.24:
        name = "AI Speculative Mania"
    elif ret_3m > 0.06 and qqq_ret > ret_3m:
        name = "Risk-On Momentum"
    elif ret_3m > 0.03 and ret_6m > 0 and vol < 0.22:
        name = "Bull Consolidation"
    elif ret_3m > 0.03 and ret_6m > 0:
        name = "Bull Expansion"
    elif ret_3m < -0.05:
        name = "Recession Risk"
    elif vol > 0.32:
        name = "High Volatility"
    elif ret_1m < -0.03 and vol > 0.24:
        name = "Liquidity Stress"
    elif ret_6m > 0.04 and vol > 0.26:
        name = "Late Cycle"
    elif qqq_ret < ret_3m - 0.02 and ret_3m > 0:
        name = "Defensive Rotation"
    elif ret_3m > 0 and vol > 0.24:
        name = "Inflationary Expansion"
    else:
        name = "Bull Consolidation"

    confidence = bounded_score(52.0 + abs(ret_3m) * 180.0 + max(0.0, vol - 0.18) * 65.0)
    return {
        "name": name,
        "confidence": confidence,
        "hmm_state": hmm_state,
        "spy_return_1m": ret_1m,
        "spy_return_3m": ret_3m,
        "spy_return_6m": ret_6m,
        "qqq_relative_strength": qqq_ret - ret_3m,
        "volatility": vol,
    }
