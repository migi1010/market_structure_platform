from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _latest_statement_value(statement: pd.DataFrame, names: List[str]) -> float:
    if statement is None or statement.empty:
        return 0.0
    for name in names:
        if name in statement.index:
            series = statement.loc[name]
            if hasattr(series, "iloc") and len(series) > 0:
                return _safe_float(series.iloc[0])
    return 0.0


@dataclass(frozen=True)
class YFinanceSnapshot:
    symbol: str
    ticker: yf.Ticker
    info: Dict[str, Any]
    financials: pd.DataFrame
    cashflow: pd.DataFrame
    balance_sheet: pd.DataFrame
    news: List[Dict[str, Any]]


def fetch_snapshot(symbol: str) -> YFinanceSnapshot:
    normalized = symbol.strip().upper()
    ticker = yf.Ticker(normalized)
    info = ticker.info or {}
    return YFinanceSnapshot(
        symbol=normalized,
        ticker=ticker,
        info=info,
        financials=ticker.financials,
        cashflow=ticker.cashflow,
        balance_sheet=ticker.balance_sheet,
        news=ticker.news or [],
    )


def extract_fundamentals(snapshot: YFinanceSnapshot) -> Dict[str, float]:
    info = snapshot.info
    revenue = _latest_statement_value(snapshot.financials, ["Total Revenue", "Operating Revenue"])
    gross_profit = _latest_statement_value(snapshot.financials, ["Gross Profit"])
    net_income = _latest_statement_value(snapshot.financials, ["Net Income", "Net Income Common Stockholders"])
    operating_cash_flow = _latest_statement_value(snapshot.cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"])
    free_cash_flow = _latest_statement_value(snapshot.cashflow, ["Free Cash Flow"])
    if free_cash_flow == 0.0:
        capex = _latest_statement_value(snapshot.cashflow, ["Capital Expenditure", "Capital Expenditures"])
        free_cash_flow = operating_cash_flow + capex
    total_assets = _latest_statement_value(snapshot.balance_sheet, ["Total Assets"])
    total_liabilities = _latest_statement_value(snapshot.balance_sheet, ["Total Liabilities Net Minority Interest", "Total Liab"])
    gross_margin = gross_profit / revenue if revenue > 0 else _safe_float(info.get("grossMargins"))
    debt_ratio = total_liabilities / total_assets if total_assets > 0 else 0.0

    return {
        "revenue": revenue,
        "net_income": net_income,
        "gross_margin": gross_margin,
        "operating_cash_flow": operating_cash_flow,
        "free_cash_flow": free_cash_flow,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "debt_ratio": debt_ratio,
        "pe_ratio": _safe_float(info.get("trailingPE") or info.get("forwardPE")),
        "ps_ratio": _safe_float(info.get("priceToSalesTrailing12Months")),
        "price": _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        "market_cap": _safe_float(info.get("marketCap")),
    }
