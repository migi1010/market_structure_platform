from __future__ import annotations

from typing import Any, Dict

from alpha_engine.scoring import bounded_score, confidence_label, partial_weighted_score
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
    fcf_conversion = free_cash_flow / max(abs(net_income), 1.0) if net_income != 0 else None
    accrual_ratio = (net_income - operating_cash_flow) / max(abs(total_assets), 1.0) if total_assets != 0 else None
    debt_quality = 1.0 - total_debt / max(total_assets, 1.0) if total_assets != 0 else None
    capex_distortion = abs(capex) / max(abs(operating_cash_flow), 1.0) if operating_cash_flow != 0 else None
    amortization_distortion = depreciation / max(abs(net_income), 1.0) if net_income != 0 else None
    operating_cashflow_quality = operating_cash_flow / max(abs(net_income), 1.0) if net_income != 0 else None
    sbc_dilution = sbc / max(revenue, 1.0) if revenue != 0 and sbc != 0 else None

    adjusted_net_income = net_income - max(0.0, sbc) + max(0.0, depreciation * 0.35)
    factor_scores = {
        "fcf_conversion": (bounded_score(35.0 + min(1.8, fcf_conversion) * 34.0) if fcf_conversion is not None else None, 0.18),
        "ocf_net_income": (bounded_score(40.0 + min(2.0, operating_cashflow_quality) * 28.0) if operating_cashflow_quality is not None else None, 0.16),
        "accrual_ratio": (bounded_score(76.0 - max(0.0, accrual_ratio) * 180.0) if accrual_ratio is not None else None, 0.14),
        "sbc_dilution": (bounded_score(78.0 - max(0.0, sbc_dilution) * 240.0) if sbc_dilution is not None else None, 0.10),
        "debt_quality": (bounded_score(45.0 + max(-1.0, min(1.0, debt_quality)) * 38.0) if debt_quality is not None else None, 0.12),
        "capex_efficiency": (bounded_score(72.0 - max(0.0, capex_distortion - 0.45) * 42.0) if capex_distortion is not None else None, 0.10),
        "amortization_quality": (bounded_score(70.0 - max(0.0, amortization_distortion - 0.35) * 28.0) if amortization_distortion is not None else None, 0.08),
        "margin_proxy": (bounded_score(45.0 + safe_float(info.get("profitMargins")) * 130.0 + safe_float(info.get("grossMargins")) * 45.0), 0.12),
    }
    quality_score, completeness = partial_weighted_score(factor_scores, neutral=48.0)
    bullish_factors = []
    risk_factors = []
    if fcf_conversion is not None and fcf_conversion >= 1.0:
        bullish_factors.append("Free cash flow conversion supports reported earnings.")
    if operating_cashflow_quality is not None and operating_cashflow_quality >= 1.0:
        bullish_factors.append("Operating cash flow covers net income.")
    if debt_quality is not None and debt_quality >= 0.65:
        bullish_factors.append("Balance sheet leverage quality is strong.")
    if accrual_ratio is not None and accrual_ratio > 0.12:
        risk_factors.append("Accrual ratio indicates earnings quality pressure.")
    if sbc_dilution is not None and sbc_dilution > 0.08:
        risk_factors.append("Stock-based compensation dilution is elevated.")
    if completeness < 55:
        risk_factors.append("Financial statement coverage is partial; confidence is reduced.")

    return {
        "ticker": ticker,
        "quality_score": quality_score,
        "earnings_quality_score": quality_score,
        "confidence_score": completeness,
        "confidence_label": confidence_label(completeness),
        "data_completeness": completeness,
        "data_status": "Partial Data" if completeness < 70 else "Complete",
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
        "bullish_factors": bullish_factors,
        "risk_factors": risk_factors,
        "summary": "Normalized earnings adjust net income for cash conversion, accruals, stock-based compensation, leverage quality, capex intensity, and amortization distortion.",
    }
