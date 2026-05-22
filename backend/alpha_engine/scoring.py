from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def bounded_score(value: float) -> float:
    return round(float(min(100.0, max(0.0, value))), 2)


def calculate_bubble_index(
    pe_ratio: float = 0.0,
    ps_ratio: float = 0.0,
    revenue_growth: float = 0.0,
    price_return: float = 0.0,
    gross_margin: float = 0.0,
    free_cash_flow: float = 0.0,
    operating_cash_flow: float = 0.0,
    net_income: float = 0.0,
    debt_ratio: float = 0.0,
    shares_growth: float = 0.0,
    insider_selling_ratio: float = 0.0,
    retail_sentiment: float = 50.0,
    volatility_change: float = 0.0,
    accrual_ratio: float = 0.0,
) -> float:
    valuation_expansion = bounded_score(max(0.0, pe_ratio - 22.0) * 1.35 + max(0.0, ps_ratio - 5.0) * 5.0)
    price_revenue_divergence = bounded_score(50.0 + (price_return - revenue_growth) * 180.0)
    fcf_margin = free_cash_flow / max(abs(operating_cash_flow), 1.0)
    negative_cashflow_risk = bounded_score(45.0 + max(0.0, -free_cash_flow / 1_000_000_000.0) * 8.0 + max(0.0, 0.35 - fcf_margin) * 70.0)
    dilution_risk = bounded_score(35.0 + max(0.0, shares_growth) * 420.0)
    distribution_signal = bounded_score(35.0 + max(0.0, insider_selling_ratio) * 85.0 + max(0.0, debt_ratio - 0.55) * 70.0)
    retail_euphoria = bounded_score(retail_sentiment)
    volatility_acceleration = bounded_score(45.0 + max(0.0, volatility_change) * 170.0)
    accrual_quality_penalty = bounded_score(50.0 + max(0.0, accrual_ratio) * 120.0 + (0.0 if net_income <= 0 else max(0.0, 1.0 - free_cash_flow / max(net_income, 1.0)) * 35.0))

    score = (
        0.25 * valuation_expansion
        + 0.20 * price_revenue_divergence
        + 0.15 * negative_cashflow_risk
        + 0.15 * dilution_risk
        + 0.10 * distribution_signal
        + 0.10 * retail_euphoria
        + 0.05 * volatility_acceleration
    )
    return bounded_score(score * 0.9 + accrual_quality_penalty * 0.1)


def classify_bubble(score: float) -> str:
    if score >= 85:
        return "Extreme Mania"
    if score >= 70:
        return "Bubble Risk"
    if score >= 50:
        return "Overheated"
    if score >= 30:
        return "Speculative"
    return "Healthy"


def explain_bubble(inputs: Dict[str, float], score: float) -> str:
    drivers: List[str] = []
    if (inputs.get("price_return", 0.0) - inputs.get("revenue_growth", 0.0)) > 0.18:
        drivers.append("price expansion is outpacing revenue growth")
    if inputs.get("free_cash_flow", 0.0) < 0:
        drivers.append("free cash flow quality is deteriorating")
    if inputs.get("shares_growth", 0.0) > 0.03:
        drivers.append("share dilution is rising")
    if inputs.get("insider_selling_ratio", 0.0) > 0.35:
        drivers.append("distribution pressure is visible")
    if inputs.get("retail_sentiment", 50.0) > 70:
        drivers.append("retail momentum is elevated")
    if not drivers:
        drivers.append("valuation, cash flow, and sentiment conditions remain broadly controlled")
    return f"{classify_bubble(score)}: " + ", ".join(drivers).capitalize() + "."


def calculate_stock_alpha(
    trend_strength: float,
    relative_volume: float,
    price_acceleration: float,
    momentum: float,
    institutional_flow: float,
    earnings_surprise: float,
    hmm_prediction: float,
    bubble_index: float,
) -> float:
    trend_component = 50.0 + trend_strength * 170.0
    volume_component = 50.0 + (relative_volume - 1.0) * 22.0
    acceleration_component = 50.0 + price_acceleration * 260.0
    momentum_component = 50.0 + momentum * 130.0
    earnings_component = 50.0 + earnings_surprise * 120.0
    bubble_penalty = max(0.0, bubble_index - 55.0) * 0.45
    score = (
        trend_component * 0.20
        + volume_component * 0.13
        + acceleration_component * 0.14
        + momentum_component * 0.18
        + institutional_flow * 0.12
        + earnings_component * 0.10
        + hmm_prediction * 0.08
        + (100.0 - bubble_index) * 0.05
        - bubble_penalty
    )
    return bounded_score(score)


def calculate_sector_strength(
    price_momentum: float,
    relative_strength: float,
    volume_strength: float,
    market_cap_flow: float,
    volatility: float,
    earnings_growth: float,
    analyst_sentiment: float,
    bubble_risk: float,
) -> float:
    momentum_component = 50.0 + price_momentum * 190.0
    relative_component = 50.0 + relative_strength * 210.0
    volume_component = 50.0 + (volume_strength - 1.0) * 24.0
    flow_component = 50.0 + market_cap_flow * 160.0
    volatility_component = 100.0 - min(100.0, max(0.0, volatility * 160.0))
    earnings_component = 50.0 + earnings_growth * 130.0
    score = (
        momentum_component * 0.22
        + relative_component * 0.20
        + volume_component * 0.13
        + flow_component * 0.12
        + volatility_component * 0.10
        + earnings_component * 0.10
        + analyst_sentiment * 0.08
        + (100.0 - bubble_risk) * 0.05
    )
    return bounded_score(score)


class ScoringRankingSystem:
    def __init__(self) -> None:
        self.regime_weights = {
            0: {"growth": 0.40, "quality": 0.10, "valuation": 0.10, "momentum": 0.25, "smart_money": 0.15},
            1: {"quality": 0.40, "valuation": 0.30, "growth": 0.10, "momentum": 0.10, "smart_money": 0.10},
            2: {"quality": 0.35, "valuation": 0.25, "growth": 0.15, "momentum": 0.15, "smart_money": 0.10},
        }

    @staticmethod
    def _winsorize_and_zscore(series: pd.Series) -> pd.Series:
        clean = series.replace([np.inf, -np.inf], np.nan).fillna(series.median())
        lower = clean.quantile(0.01)
        upper = clean.quantile(0.99)
        clipped = clean.clip(lower=lower, upper=upper)
        std = clipped.std() if clipped.std() > 1e-6 else 1.0
        return (((clipped - clipped.mean()) / std + 3.0) / 6.0 * 100.0).clip(0.0, 100.0)

    def process_universe(self, tickers: List[str], regime: int = 0) -> Dict[str, pd.DataFrame]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=260)
        rows: List[Dict[str, float | str]] = []

        for ticker in tickers:
            try:
                data = yf.download(ticker, start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
                if data.empty or len(data) < 64:
                    continue
                close = data["Close"].astype(float)
                volume = data["Volume"].astype(float)
                ret_1m = close.iloc[-1] / close.iloc[-22] - 1.0
                ret_3m = close.iloc[-1] / close.iloc[-64] - 1.0
                ret_6m = close.iloc[-1] / close.iloc[0] - 1.0
                vol = np.log(close / close.shift(1)).std() * np.sqrt(252)
                rel_volume = volume.iloc[-1] / max(volume.tail(60).mean(), 1.0)
                smart_money = bounded_score(50.0 + (rel_volume - 1.0) * 24.0 + ret_1m * 100.0)
                bubble = bounded_score(42.0 + max(0.0, ret_3m) * 80.0 + max(0.0, rel_volume - 1.2) * 18.0)
                rows.append({
                    "ticker": ticker,
                    "growth": ret_6m,
                    "quality": 1.0 / max(float(vol), 0.05),
                    "valuation": -ret_1m,
                    "momentum": ret_1m + ret_3m,
                    "smart_money": smart_money,
                    "bubble_score": bubble,
                    "relative_volume": rel_volume,
                })
            except Exception as exc:
                logger.warning("Failed to score %s: %s", ticker, exc)

        raw = pd.DataFrame(rows)
        if raw.empty:
            empty = pd.DataFrame()
            return {"alpha": empty, "smart_money": empty, "bubble": empty}

        df = pd.DataFrame({"Ticker": raw["ticker"]})
        df["Growth"] = self._winsorize_and_zscore(raw["growth"])
        df["Quality"] = self._winsorize_and_zscore(raw["quality"])
        df["Valuation"] = self._winsorize_and_zscore(raw["valuation"])
        df["Momentum"] = self._winsorize_and_zscore(raw["momentum"])
        df["SmartMoney"] = self._winsorize_and_zscore(raw["smart_money"])
        weights = self.regime_weights.get(regime, self.regime_weights[0])
        df["Alpha_Score"] = (
            df["Growth"] * weights.get("growth", 0.0)
            + df["Quality"] * weights.get("quality", 0.0)
            + df["Valuation"] * weights.get("valuation", 0.0)
            + df["Momentum"] * weights.get("momentum", 0.0)
            + df["SmartMoney"] * weights.get("smart_money", 0.0)
        ).clip(0.0, 100.0)
        df["BubbleScore"] = raw["bubble_score"].values
        df["Volume_Ratio"] = raw["relative_volume"].map(lambda value: f"{value:.2f}x")
        df = df.sort_values("Alpha_Score", ascending=False)
        smart = df[["Ticker", "SmartMoney", "Volume_Ratio"]].sort_values("SmartMoney", ascending=False)
        bubble = df[["Ticker", "BubbleScore"]].sort_values("BubbleScore", ascending=False)
        return {"alpha": df, "smart_money": smart, "bubble": bubble}
