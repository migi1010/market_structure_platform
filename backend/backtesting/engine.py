from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd
import yfinance as yf

from alpha_engine.scoring import bounded_score, calculate_bubble_index
from qlib_engine.pipeline import NASDAQ100_UNIVERSE, SP500_UNIVERSE
from quant_engine.data_pipeline import get_quote, safe_float

BENCHMARKS = ["SPY", "QQQ"]


@dataclass
class FactorSnapshot:
    ticker: str
    sector: str
    alpha_score: float
    quality: float
    growth: float
    smart_money: float
    valuation: float
    earnings_quality: float
    market_structure: float
    bubble_risk: float


def _download_prices(symbols: List[str], period: str) -> pd.DataFrame:
    data = yf.download(symbols, period=period, interval="1d", auto_adjust=True, progress=False, group_by="ticker")
    close_map: Dict[str, pd.Series] = {}
    for symbol in symbols:
        if isinstance(data.columns, pd.MultiIndex):
            if (symbol, "Close") in data.columns:
                close_map[symbol] = pd.to_numeric(data[(symbol, "Close")], errors="coerce")
        elif symbol == symbols[0] and "Close" in data.columns:
            close_map[symbol] = pd.to_numeric(data["Close"], errors="coerce")
    prices = pd.DataFrame(close_map).dropna(how="all")
    return prices.ffill().dropna(how="all")


def _download_volumes(symbols: List[str], period: str) -> pd.DataFrame:
    data = yf.download(symbols, period=period, interval="1d", auto_adjust=True, progress=False, group_by="ticker")
    volume_map: Dict[str, pd.Series] = {}
    for symbol in symbols:
        if isinstance(data.columns, pd.MultiIndex):
            if (symbol, "Volume") in data.columns:
                volume_map[symbol] = pd.to_numeric(data[(symbol, "Volume")], errors="coerce")
        elif symbol == symbols[0] and "Volume" in data.columns:
            volume_map[symbol] = pd.to_numeric(data["Volume"], errors="coerce")
    volumes = pd.DataFrame(volume_map).dropna(how="all")
    return volumes.ffill().dropna(how="all")


def _benchmark_metrics(returns: pd.Series, benchmark_returns: pd.Series) -> Dict[str, float]:
    aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
    if aligned.empty:
        return {"information_ratio": 0.0, "alpha_vs_benchmark": 0.0}
    active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    information_ratio = active.mean() / active.std() * np.sqrt(252) if active.std() > 1e-9 else 0.0
    alpha_vs_benchmark = ((1 + aligned.iloc[:, 0]).prod() - (1 + aligned.iloc[:, 1]).prod()) * 100.0
    return {
        "information_ratio": round(float(information_ratio), 4),
        "alpha_vs_benchmark": round(float(alpha_vs_benchmark), 2),
    }


def _portfolio_metrics(returns: pd.Series, benchmark_returns: pd.Series) -> Dict[str, float]:
    if returns.empty:
        return {
            "cagr": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "information_ratio": 0.0,
            "alpha_vs_benchmark": 0.0,
        }
    total_years = max(len(returns) / 252.0, 1 / 252.0)
    total_return = float((1 + returns).prod())
    cagr = total_return ** (1 / total_years) - 1
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 1e-9 else 0.0
    equity = (1 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    win_rate = float((returns > 0).mean())
    extra = _benchmark_metrics(returns, benchmark_returns)
    return {
        "cagr": round(cagr * 100.0, 2),
        "sharpe_ratio": round(float(sharpe), 4),
        "max_drawdown": round(float(drawdown.min() * 100.0), 2),
        "win_rate": round(win_rate * 100.0, 2),
        "information_ratio": extra["information_ratio"],
        "alpha_vs_benchmark": extra["alpha_vs_benchmark"],
    }


def _market_regime(spy_window: pd.Series) -> str:
    if len(spy_window) < 64:
        return "Neutral Regime"
    ret_3m = float(spy_window.iloc[-1] / spy_window.iloc[-64] - 1.0)
    returns = spy_window.pct_change().dropna()
    volatility = float(returns.tail(21).std() * np.sqrt(252)) if len(returns) > 21 else 0.22
    if ret_3m > 0.06 and volatility > 0.24:
        return "Momentum Mania"
    if ret_3m > 0.03:
        return "Bull Market"
    if ret_3m < -0.05:
        return "Bear Market"
    if volatility > 0.32:
        return "High Volatility"
    return "Neutral Regime"


def _weights_for_regime(regime: str) -> Dict[str, float]:
    if regime == "Bear Market":
        return {"quality": 0.25, "growth": 0.14, "smart_money": 0.17, "valuation": 0.22, "earnings_quality": 0.15, "market_structure": 0.07}
    if regime == "Momentum Mania":
        return {"quality": 0.16, "growth": 0.26, "smart_money": 0.22, "valuation": 0.10, "earnings_quality": 0.12, "market_structure": 0.14}
    return {"quality": 0.20, "growth": 0.20, "smart_money": 0.20, "valuation": 0.15, "earnings_quality": 0.15, "market_structure": 0.10}


def _factor_snapshot(
    ticker: str,
    price_window: pd.Series,
    volume_window: pd.Series,
    benchmark_window: pd.Series,
    regime: str,
) -> FactorSnapshot | None:
    if len(price_window.dropna()) < 64:
        return None
    info = get_quote(ticker)
    latest = float(price_window.iloc[-1])
    ret_1m = float(latest / price_window.iloc[-22] - 1.0) if len(price_window) >= 22 else 0.0
    ret_3m = float(latest / price_window.iloc[-64] - 1.0)
    ret_6m = float(latest / price_window.iloc[0] - 1.0)
    acceleration = ret_1m - ret_3m / 3.0
    relative_volume = float(volume_window.iloc[-1] / max(volume_window.tail(60).mean(), 1.0)) if len(volume_window.dropna()) >= 20 else 1.0
    volatility = float(price_window.pct_change().dropna().tail(64).std() * np.sqrt(252))
    benchmark_ret = float(benchmark_window.iloc[-1] / benchmark_window.iloc[-64] - 1.0) if len(benchmark_window.dropna()) >= 64 else 0.0

    revenue_growth = safe_float(info.get("revenueGrowth"))
    gross_margin = safe_float(info.get("grossMargins"))
    free_cash_flow = safe_float(info.get("freeCashflow"))
    operating_cash_flow = safe_float(info.get("operatingCashflow"))
    net_income_margin = safe_float(info.get("profitMargins"))
    total_revenue = safe_float(info.get("totalRevenue"))
    debt_to_equity = safe_float(info.get("debtToEquity")) / 100.0
    bubble_risk = calculate_bubble_index(
        pe_ratio=safe_float(info.get("trailingPE") or info.get("forwardPE")),
        ps_ratio=safe_float(info.get("priceToSalesTrailing12Months")),
        revenue_growth=revenue_growth,
        price_return=ret_6m,
        gross_margin=gross_margin,
        free_cash_flow=free_cash_flow,
        operating_cash_flow=operating_cash_flow,
        net_income=max(1.0, abs(net_income_margin) * max(total_revenue, 1.0)),
        debt_ratio=debt_to_equity,
        shares_growth=0.0,
        insider_selling_ratio=0.0,
        retail_sentiment=50.0 + max(0.0, ret_3m) * 80.0,
        volatility_change=volatility - 0.25,
        accrual_ratio=max(0.0, (net_income_margin * max(total_revenue, 1.0) - operating_cash_flow) / max(total_revenue, 1.0)),
    )

    quality = bounded_score(50.0 + gross_margin * 80.0 + net_income_margin * 120.0 - debt_to_equity * 18.0)
    growth = bounded_score(50.0 + revenue_growth * 130.0 + ret_3m * 80.0)
    smart_money = bounded_score(50.0 + (relative_volume - 1.0) * 22.0 + ret_1m * 90.0 + acceleration * 110.0)
    valuation = bounded_score(78.0 - max(0.0, safe_float(info.get("trailingPE") or info.get("forwardPE")) - 18.0) * 0.9 - max(0.0, safe_float(info.get("priceToSalesTrailing12Months")) - 4.0) * 3.0 + max(0.0, free_cash_flow) / 2_000_000_000.0)
    earnings_quality = bounded_score(50.0 + (free_cash_flow / max(abs(operating_cash_flow), 1.0)) * 45.0 + net_income_margin * 70.0)
    market_structure = bounded_score(50.0 + ret_6m * 75.0 - volatility * 25.0 + (ret_3m - benchmark_ret) * 60.0)
    weights = _weights_for_regime(regime)
    alpha_score = bounded_score(
        quality * weights["quality"]
        + growth * weights["growth"]
        + smart_money * weights["smart_money"]
        + valuation * weights["valuation"]
        + earnings_quality * weights["earnings_quality"]
        + market_structure * weights["market_structure"]
        - max(0.0, bubble_risk - 55.0) * 0.25
    )

    return FactorSnapshot(
        ticker=ticker,
        sector=str(info.get("sector") or "Unknown"),
        alpha_score=alpha_score,
        quality=quality,
        growth=growth,
        smart_money=smart_money,
        valuation=valuation,
        earnings_quality=earnings_quality,
        market_structure=market_structure,
        bubble_risk=bubble_risk,
    )


def _select_sector_neutral(candidates: List[FactorSnapshot], limit: int = 10, max_per_sector: int = 2) -> List[FactorSnapshot]:
    selected: List[FactorSnapshot] = []
    sector_counts: Dict[str, int] = {}
    for candidate in sorted(candidates, key=lambda row: row.alpha_score, reverse=True):
        if sector_counts.get(candidate.sector, 0) >= max_per_sector:
            continue
        selected.append(candidate)
        sector_counts[candidate.sector] = sector_counts.get(candidate.sector, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def _factor_attribution(snapshots: Iterable[FactorSnapshot]) -> Dict[str, float]:
    rows = list(snapshots)
    if not rows:
        return {"quality": 0.0, "growth": 0.0, "smart_money": 0.0, "valuation": 0.0, "earnings_quality": 0.0, "market_structure": 0.0, "bubble_risk_drag": 0.0}
    return {
        "quality": round(float(np.mean([row.quality for row in rows])), 2),
        "growth": round(float(np.mean([row.growth for row in rows])), 2),
        "smart_money": round(float(np.mean([row.smart_money for row in rows])), 2),
        "valuation": round(float(np.mean([row.valuation for row in rows])), 2),
        "earnings_quality": round(float(np.mean([row.earnings_quality for row in rows])), 2),
        "market_structure": round(float(np.mean([row.market_structure for row in rows])), 2),
        "bubble_risk_drag": round(float(np.mean([row.bubble_risk for row in rows])), 2),
    }


def run_top_alpha_backtest(universe: str = "sp500", years: int = 3) -> Dict[str, Any]:
    # Lazy import: vectorbt pulls numba, plotly, and a large dependency tree (~150-200MB).
    # It must NOT be imported at module level or it will exhaust Render Free Tier RAM on startup.
    import vectorbt as vbt  # noqa: PLC0415
    normalized_universe = "nasdaq100" if universe.lower() == "nasdaq100" else "sp500"
    symbols = sorted(set(NASDAQ100_UNIVERSE if normalized_universe == "nasdaq100" else SP500_UNIVERSE))
    period = f"{max(2, years + 1)}y"
    prices = _download_prices(symbols + BENCHMARKS, period)
    volumes = _download_volumes(symbols, period)
    prices = prices.dropna(subset=["SPY", "QQQ"], how="any")

    start_date = prices.index.max() - pd.DateOffset(years=years)
    prices = prices.loc[prices.index >= start_date]
    volumes = volumes.reindex(prices.index).ffill()

    rebalance_dates = prices.resample("ME").last().index
    weights = pd.DataFrame(0.0, index=prices.index, columns=symbols)
    holdings_history: List[Dict[str, Any]] = []
    factor_samples: List[FactorSnapshot] = []
    walk_forward_windows: List[Dict[str, Any]] = []

    for rebalance_date in rebalance_dates:
        if rebalance_date not in prices.index:
            candidate_date = prices.index[prices.index.get_indexer([rebalance_date], method="ffill")[0]]
        else:
            candidate_date = rebalance_date
        loc = prices.index.get_loc(candidate_date)
        if isinstance(loc, slice) or int(loc) < 126:
            continue

        spy_window = prices["SPY"].iloc[int(loc) - 126:int(loc) + 1]
        regime = _market_regime(spy_window)
        snapshots: List[FactorSnapshot] = []
        for ticker in symbols:
            price_window = prices[ticker].iloc[int(loc) - 126:int(loc) + 1].dropna()
            volume_window = volumes[ticker].iloc[int(loc) - 126:int(loc) + 1].dropna() if ticker in volumes.columns else pd.Series(dtype=float)
            benchmark_window = prices["SPY"].iloc[int(loc) - 126:int(loc) + 1].dropna()
            snapshot = _factor_snapshot(ticker, price_window, volume_window, benchmark_window, regime)
            if snapshot is None:
                continue
            if snapshot.alpha_score > 85 and snapshot.bubble_risk < 40 and snapshot.smart_money > 70 and snapshot.earnings_quality > 70:
                snapshots.append(snapshot)

        selected = _select_sector_neutral(snapshots, limit=10, max_per_sector=2)
        if not selected:
            relaxed = sorted(
                [row for row in snapshots if row.bubble_risk < 55],
                key=lambda row: row.alpha_score,
                reverse=True,
            )[:10]
            selected = _select_sector_neutral(relaxed, limit=10, max_per_sector=2)

        current_weights = {row.ticker: round(1.0 / len(selected), 6) for row in selected} if selected else {}
        weights.loc[candidate_date] = 0.0
        if selected:
            for ticker, weight in current_weights.items():
                weights.loc[candidate_date, ticker] = weight
            factor_samples.extend(selected)

        holdings_history.append({
            "date": candidate_date.strftime("%Y-%m-%d"),
            "regime": regime,
            "holdings": [
                {
                    "ticker": row.ticker,
                    "sector": row.sector,
                    "alpha_score": row.alpha_score,
                    "bubble_risk": row.bubble_risk,
                    "smart_money": row.smart_money,
                    "earnings_quality": row.earnings_quality,
                    "weight": current_weights.get(row.ticker, 0.0),
                }
                for row in selected
            ],
        })
        walk_forward_windows.append({
            "rebalance_date": candidate_date.strftime("%Y-%m-%d"),
            "lookback_days": 126,
            "selected_count": len(selected),
            "sector_neutral": True,
        })

    asset_prices = prices[symbols].dropna(how="all")
    asset_weights = weights.reindex(asset_prices.index).ffill().fillna(0.0)
    portfolio = vbt.Portfolio.from_orders(
        close=asset_prices,
        size=asset_weights,
        size_type="targetpercent",
        init_cash=100.0,
        cash_sharing=True,
        group_by=True,
        call_seq="auto",
        freq="1D",
    )
    portfolio_value = portfolio.value()
    portfolio_returns = portfolio_value.pct_change().dropna()
    spy_returns = prices["SPY"].pct_change().reindex(portfolio_returns.index).dropna()
    qqq_returns = prices["QQQ"].pct_change().reindex(portfolio_returns.index).dropna()
    aligned_returns = portfolio_returns.reindex(spy_returns.index).dropna()

    report_spy = _portfolio_metrics(aligned_returns, spy_returns.reindex(aligned_returns.index).dropna())
    report_qqq = _portfolio_metrics(aligned_returns, qqq_returns.reindex(aligned_returns.index).dropna())

    benchmark_comparison = {
        "SPY": {
            "cagr": _portfolio_metrics(spy_returns.reindex(aligned_returns.index).dropna(), spy_returns.reindex(aligned_returns.index).dropna())["cagr"],
            "sharpe_ratio": _portfolio_metrics(spy_returns.reindex(aligned_returns.index).dropna(), spy_returns.reindex(aligned_returns.index).dropna())["sharpe_ratio"],
            "alpha_vs_portfolio": round(-report_spy["alpha_vs_benchmark"], 2),
        },
        "QQQ": {
            "cagr": _portfolio_metrics(qqq_returns.reindex(aligned_returns.index).dropna(), qqq_returns.reindex(aligned_returns.index).dropna())["cagr"],
            "sharpe_ratio": _portfolio_metrics(qqq_returns.reindex(aligned_returns.index).dropna(), qqq_returns.reindex(aligned_returns.index).dropna())["sharpe_ratio"],
            "alpha_vs_portfolio": round(-report_qqq["alpha_vs_benchmark"], 2),
        },
    }

    equity_curve = [
        {"date": index.strftime("%Y-%m-%d"), "equity": round(float(value), 4)}
        for index, value in portfolio_value.dropna().items()
    ]

    return {
        "generated_at": pd.Timestamp.now(tz=timezone.utc).isoformat(),
        "strategy": "Top 10 Alpha Portfolio",
        "universe": normalized_universe.upper(),
        "rebalance": "monthly",
        "walk_forward": True,
        "sector_neutral": True,
        "selection_rules": {
            "alpha_score_min": 85,
            "bubble_risk_max": 40,
            "smart_money_min": 70,
            "earnings_quality_min": 70,
        },
        "equity_curve": equity_curve,
        "performance_report": {
            "vs_spy": report_spy,
            "vs_qqq": report_qqq,
        },
        "benchmark_comparison": benchmark_comparison,
        "factor_attribution": _factor_attribution(factor_samples),
        "holdings_history": holdings_history,
        "walk_forward_windows": walk_forward_windows,
    }
