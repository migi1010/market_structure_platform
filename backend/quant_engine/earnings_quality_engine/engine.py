from __future__ import annotations

from typing import Any, Dict

from alpha_engine.scoring import bounded_score
from quant_engine.data_pipeline import get_quote, get_statements, safe_float, statement_value


def analyze_earnings_quality(symbol: str) -> Dict[str, Any]:
    ticker = symbol.strip().upper()
    info = get_quote(ticker)
    financials, cashflow, balance = get_statements(ticker)

    revenue = statement_value(financials, ["Total Revenue", "Operating Revenue"])
    net_income = statement_value(financials, ["Net Income", "Net Income Common Stockholders"])
    operating_cash_flow = statement_value(cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"])
    capex = statement_value(cashflow, ["Capital Expenditure", "Capital Expenditures"])
    free_cash_flow = statement_value(cashflow, ["Free Cash Flow"]) or operating_cash_flow + capex
    depreciation = statement_value(cashflow, ["Depreciation And Amortization", "Depreciation"])
    total_assets = statement_value(balance, ["Total Assets"])
    total_liabilities = statement_value(balance, ["Total Liabilities Net Minority Interest", "Total Liab"])
    total_debt = statement_value(balance, ["Total Debt", "Long Term Debt"])

    sbc = safe_float(info.get("stockBasedCompensation"))
    fcf_conversion = free_cash_flow / max(abs(net_income), 1.0)
    accrual_ratio = (net_income - operating_cash_flow) / max(abs(total_assets), 1.0)
    debt_quality = 1.0 - total_debt / max(total_assets, 1.0)
    capex_distortion = abs(capex) / max(abs(operating_cash_flow), 1.0)
    amortization_distortion = depreciation / max(abs(net_income), 1.0)
    operating_cashflow_quality = operating_cash_flow / max(abs(net_income), 1.0)
    sbc_dilution = sbc / max(revenue, 1.0)

    adjusted_net_income = net_income - max(0.0, sbc) + max(0.0, depreciation * 0.35)
    quality_score = bounded_score(
        50.0
        + min(1.5, fcf_conversion) * 22.0
        - max(0.0, accrual_ratio) * 160.0
        - max(0.0, sbc_dilution) * 180.0
        + debt_quality * 16.0
        - max(0.0, capex_distortion - 0.45) * 30.0
        - max(0.0, amortization_distortion - 0.35) * 20.0
    )

    return {
        "ticker": ticker,
        "quality_score": quality_score,
        "adjusted_net_income": adjusted_net_income,
        "net_income": net_income,
        "free_cash_flow": free_cash_flow,
        "operating_cash_flow": operating_cash_flow,
        "fcf_conversion": fcf_conversion,
        "accrual_ratio": accrual_ratio,
        "sbc_dilution": sbc_dilution,
        "debt_quality": debt_quality,
        "capex_distortion": capex_distortion,
        "amortization_distortion": amortization_distortion,
        "operating_cashflow_quality": operating_cashflow_quality,
        "summary": "Normalized earnings adjust net income for cash conversion, accruals, stock-based compensation, leverage quality, capex intensity, and amortization distortion.",
    }
