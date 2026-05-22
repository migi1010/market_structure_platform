from __future__ import annotations

from typing import Any, Dict

import numpy as np

from alpha_engine.scoring import calculate_bubble_index, classify_bubble, explain_bubble
from quant_engine.data_pipeline import (
    get_history,
    get_quote,
    get_statements,
    previous_statement_value,
    safe_float,
    statement_value,
)


def analyze_bubble(symbol: str) -> Dict[str, Any]:
    ticker = symbol.strip().upper()
    info = get_quote(ticker)
    financials, cashflow, balance = get_statements(ticker)
    history = get_history(ticker, "9mo")

    revenue = statement_value(financials, ["Total Revenue", "Operating Revenue"])
    previous_revenue = previous_statement_value(financials, ["Total Revenue", "Operating Revenue"])
    gross_profit = statement_value(financials, ["Gross Profit"])
    net_income = statement_value(financials, ["Net Income", "Net Income Common Stockholders"])
    operating_cash_flow = statement_value(cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"])
    free_cash_flow = statement_value(cashflow, ["Free Cash Flow"])
    if free_cash_flow == 0.0:
      capex = statement_value(cashflow, ["Capital Expenditure", "Capital Expenditures"])
      free_cash_flow = operating_cash_flow + capex
    total_assets = statement_value(balance, ["Total Assets"])
    total_liabilities = statement_value(balance, ["Total Liabilities Net Minority Interest", "Total Liab"])

    revenue_growth = (revenue - previous_revenue) / previous_revenue if previous_revenue > 0 else safe_float(info.get("revenueGrowth"))
    gross_margin = gross_profit / revenue if revenue > 0 else safe_float(info.get("grossMargins"))
    debt_ratio = total_liabilities / total_assets if total_assets > 0 else safe_float(info.get("debtToEquity")) / 100.0
    price_return = 0.0
    volatility_change = 0.0
    if history is not None and not history.empty and len(history) > 64:
        close = history["Close"].astype(float)
        price_return = float(close.iloc[-1] / close.iloc[0] - 1.0)
        returns = close.pct_change().dropna()
        if len(returns) > 44:
            volatility_change = float(returns.tail(20).std() * np.sqrt(252) - returns.head(64).std() * np.sqrt(252))

    shares = safe_float(info.get("sharesOutstanding"))
    implied_shares = safe_float(info.get("impliedSharesOutstanding"))
    shares_growth = (shares - implied_shares) / implied_shares if shares > 0 and implied_shares > 0 else 0.0
    accrual_ratio = (net_income - operating_cash_flow) / max(abs(total_assets), 1.0)
    retail_sentiment = min(100.0, max(0.0, 50.0 + max(0.0, price_return) * 80.0))
    inputs = {
        "pe_ratio": safe_float(info.get("trailingPE") or info.get("forwardPE")),
        "ps_ratio": safe_float(info.get("priceToSalesTrailing12Months")),
        "revenue_growth": revenue_growth,
        "price_return": price_return,
        "gross_margin": gross_margin,
        "free_cash_flow": free_cash_flow,
        "operating_cash_flow": operating_cash_flow,
        "net_income": net_income,
        "debt_ratio": debt_ratio,
        "shares_growth": shares_growth,
        "insider_selling_ratio": 0.0,
        "retail_sentiment": retail_sentiment,
        "volatility_change": volatility_change,
        "accrual_ratio": accrual_ratio,
    }
    score = calculate_bubble_index(**inputs)
    fcf_quality = free_cash_flow / max(abs(operating_cash_flow), 1.0)
    net_income_quality = operating_cash_flow / max(abs(net_income), 1.0)

    return {
        "ticker": ticker,
        "company_name": info.get("longName") or info.get("shortName") or ticker,
        "price": safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        "sector": info.get("sector") or "Unknown",
        "bubble_analysis_data": {
            "revenue": revenue,
            "net_income": net_income,
            "gross_margin": gross_margin,
            "operating_cash_flow": operating_cash_flow,
            "free_cash_flow": free_cash_flow,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "debt_ratio": debt_ratio,
            "pe_ratio": inputs["pe_ratio"],
            "ps_ratio": inputs["ps_ratio"],
            "bubble_index": score,
            "classification": classify_bubble(score),
            "valuation_heat": inputs["pe_ratio"] + inputs["ps_ratio"],
            "revenue_divergence": price_return - revenue_growth,
            "fcf_quality": fcf_quality,
            "dilution_risk": max(0.0, shares_growth * 100.0),
            "distribution_signal": max(0.0, debt_ratio - 0.55) * 100.0,
            "retail_speculation": retail_sentiment,
            "accrual_ratio": accrual_ratio,
            "net_income_quality": net_income_quality,
            "ai_summary": explain_bubble(inputs, score),
        },
    }
