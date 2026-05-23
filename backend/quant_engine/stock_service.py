from __future__ import annotations

from typing import Any, Dict, List

from quant_engine.bubble_engine import analyze_bubble
from quant_engine.data_pipeline import get_history, get_news, get_quote, safe_float
from quant_engine.earnings_quality_engine import analyze_earnings_quality
from quant_engine.regime_engine import detect_market_regime
from quant_engine.smart_money_engine import analyze_smart_money

COMMON_METADATA: dict[str, dict[str, str]] = {
    "AAPL": {"company_name": "Apple Inc.", "sector": "Technology"},
    "NVDA": {"company_name": "NVIDIA Corporation", "sector": "Technology"},
    "MSFT": {"company_name": "Microsoft Corporation", "sector": "Technology"},
    "AMZN": {"company_name": "Amazon.com Inc.", "sector": "Consumer Discretionary"},
    "META": {"company_name": "Meta Platforms Inc.", "sector": "Communication Services"},
    "TSLA": {"company_name": "Tesla Inc.", "sector": "Consumer Discretionary"},
    "PLTR": {"company_name": "Palantir Technologies Inc.", "sector": "Technology"},
    "AMD": {"company_name": "Advanced Micro Devices Inc.", "sector": "Technology"},
    "AVGO": {"company_name": "Broadcom Inc.", "sector": "Technology"},
    "NOW": {"company_name": "ServiceNow Inc.", "sector": "Technology"},
    "SPY": {"company_name": "SPDR S&P 500 ETF Trust", "sector": "ETF"},
    "QQQ": {"company_name": "Invesco QQQ Trust", "sector": "ETF"},
    "SMH": {"company_name": "VanEck Semiconductor ETF", "sector": "ETF"},
}


def _nullable_float(value: Any) -> float | None:
    parsed = safe_float(value)
    return parsed if parsed > 0 else None


def _number_or_none(value: Any) -> float | None:
    parsed = safe_float(value)
    return parsed if parsed != 0.0 else None


def _first_positive(*values: Any) -> float | None:
    for value in values:
        parsed = _nullable_float(value)
        if parsed is not None:
            return parsed
    return None


def _first_number(*values: Any) -> float | None:
    for value in values:
        parsed = _number_or_none(value)
        if parsed is not None:
            return parsed
    return None


def _safe_engine(name: str, task: Any, fallback: Any) -> Any:
    try:
        result = task()
        return result if result is not None else fallback
    except Exception:
        return fallback


def _history_snapshot(symbol: str) -> Dict[str, float | None]:
    try:
        history = get_history(symbol, "10d")
        if history is None or history.empty or "Close" not in history:
            history = get_history(symbol, "3mo")
        if history is None or history.empty or "Close" not in history:
            return {"price": None, "change": None, "change_percent": None}
        close = history["Close"].dropna().astype(float)
        if close.empty:
            return {"price": None, "change": None, "change_percent": None}
        latest = float(close.iloc[-1])
        previous = float(close.iloc[-2]) if len(close) > 1 else latest
        change = latest - previous
        change_percent = (change / previous * 100.0) if previous > 0 else None
        return {"price": latest, "change": change, "change_percent": change_percent}
    except Exception:
        return {"price": None, "change": None, "change_percent": None}


def _fallback_bubble(symbol: str, quote: Dict[str, Any], price: float | None) -> Dict[str, Any]:
    return {
        "ticker": symbol,
        "company_name": _company_name(symbol, quote),
        "price": price,
        "sector": _sector(symbol, quote),
        "bubble_analysis_data": {
            "available": False,
            "status": "calibrating",
            "revenue": None,
            "net_income": None,
            "gross_margin": None,
            "operating_cash_flow": None,
            "free_cash_flow": None,
            "total_assets": None,
            "total_liabilities": None,
            "debt_ratio": None,
            "pe_ratio": _number_or_none(quote.get("trailingPE") or quote.get("forwardPE")),
            "ps_ratio": _number_or_none(quote.get("priceToSalesTrailing12Months")),
            "bubble_index": None,
            "classification": "Calibrating",
            "confidence": "unavailable",
            "confidence_score": None,
            "confidence_label": "Unavailable",
            "valuation_heat": None,
            "revenue_divergence": None,
            "fcf_quality": None,
            "dilution_risk": None,
            "distribution_signal": None,
            "retail_speculation": None,
            "accrual_ratio": None,
            "net_income_quality": None,
            "ai_summary": "Bubble intelligence is calibrating. Live fundamentals are temporarily unavailable.",
        },
    }


def _company_name(symbol: str, quote: Dict[str, Any]) -> str:
    raw = quote.get("longName") or quote.get("shortName") or quote.get("displayName")
    if isinstance(raw, str) and raw.strip() and raw.strip().upper() not in {"UNKNOWN", "N/A"}:
        return raw.strip()
    return COMMON_METADATA.get(symbol, {}).get("company_name", symbol)


def _sector(symbol: str, quote: Dict[str, Any]) -> str:
    raw = quote.get("sector") or quote.get("industry")
    if isinstance(raw, str) and raw.strip() and raw.strip().upper() not in {"UNKNOWN", "N/A"}:
        return raw.strip()
    return COMMON_METADATA.get(symbol, {}).get("sector", "US Equity")


def _resolve_price_snapshot(symbol: str, quote: Dict[str, Any], bubble: Dict[str, Any]) -> Dict[str, Any]:
    history = _history_snapshot(symbol)
    price = _first_positive(
        quote.get("currentPrice"),
        quote.get("regularMarketPrice"),
        quote.get("price"),
        quote.get("last_price"),
        quote.get("lastPrice"),
        quote.get("close"),
        bubble.get("price"),
        history["price"],
    )
    previous = _first_positive(
        quote.get("previousClose"),
        quote.get("regularMarketPreviousClose"),
        quote.get("previous_close"),
        quote.get("previousClosePrice"),
    )
    change = _first_number(
        quote.get("regularMarketChange"),
        quote.get("change"),
        quote.get("priceChange"),
        history["change"],
    )
    change_percent = _first_number(
        quote.get("regularMarketChangePercent"),
        quote.get("change_percent"),
        quote.get("changePercent"),
        quote.get("percentChange"),
        history["change_percent"],
    )
    if change_percent is None and price is not None and previous is not None and previous > 0:
        change_percent = (price - previous) / previous * 100.0
    if change is None and price is not None and previous is not None:
        change = price - previous
    quote_status = str(quote.get("quoteStatus") or quote.get("quote_status") or "").strip().lower()
    if not quote_status:
        quote_status = "live" if price is not None else "unavailable"
    return {
        "price": round(float(price), 4) if price is not None and price > 0 else None,
        "change": round(float(change), 4) if change is not None else None,
        "change_percent": round(float(change_percent), 4) if change_percent is not None else None,
        "source": quote_status if price is not None else "unavailable",
    }


def _resolve_market_cap(quote: Dict[str, Any]) -> float | None:
    return _first_positive(quote.get("marketCap"), quote.get("market_cap"))


def _fallback_smart_money() -> Dict[str, Any]:
    return {
        "available": False,
        "status": "calibrating",
        "smart_money_score": None,
        "score": None,
        "confidence": "unavailable",
        "confidence_score": None,
        "confidence_label": "Unavailable",
        "accumulation_detection": None,
        "abnormal_volume": None,
        "institutional_footprint": None,
        "price_volume_divergence": None,
        "stealth_accumulation": None,
        "dark_pool_style_logic": None,
        "summary": "Smart money model is calibrating. Live volume structure is temporarily unavailable.",
    }


def _fallback_earnings() -> Dict[str, Any]:
    return {
        "available": False,
        "status": "calibrating",
        "earnings_quality_score": None,
        "quality_score": None,
        "confidence": "unavailable",
        "confidence_score": None,
        "confidence_label": "Unavailable",
        "fcf_conversion": None,
        "accrual_ratio": None,
        "sbc_dilution": None,
        "debt_quality": None,
        "capex_distortion": None,
        "amortization_distortion": None,
        "operating_cashflow_quality": None,
        "adjusted_net_income": None,
        "summary": "Earnings quality engine is calibrating. Live fundamentals are temporarily unavailable.",
    }


def _looks_like_empty_bubble(data: Dict[str, Any]) -> bool:
    financial_keys = ["revenue", "net_income", "operating_cash_flow", "free_cash_flow", "total_assets", "total_liabilities"]
    values = [data.get(key) for key in financial_keys]
    score = data.get("bubble_index")
    return all(value in (None, 0, 0.0) for value in values) and score in (None, 50, 50.0)


def _looks_like_empty_score(data: Dict[str, Any], score_key: str) -> bool:
    score = data.get(score_key)
    confidence = data.get("confidence_score")
    return score in (50, 50.0, None) and confidence in (None, 0, 0.0)


def fallback_stock_payload(symbol: str) -> Dict[str, Any]:
    ticker = symbol.strip().upper()
    metadata = COMMON_METADATA.get(ticker, {"company_name": ticker, "sector": "US Equity"})
    analyst = {
        "available": False,
        "high": None,
        "average": None,
        "low": None,
        "average_target": None,
        "implied_upside": None,
        "buy": None,
        "hold": None,
        "sell": None,
    }
    return {
        "ticker": ticker,
        "company_name": metadata["company_name"],
        "price": None,
        "change": None,
        "change_percent": None,
        "market_cap": None,
        "sector": metadata["sector"],
        "quote_status": "unavailable",
        "bubble_analysis_data": _fallback_bubble(ticker, {}, None)["bubble_analysis_data"],
        "earnings_quality": _fallback_earnings(),
        "smart_money": _fallback_smart_money(),
        "analyst_targets": analyst,
        "analyst_consensus": analyst,
        "hmm_prediction": {
            "available": False,
            "predicted_trend": "Calibrating model...",
            "bull_probability": None,
            "bear_probability": None,
            "regime_state": "Awaiting regime confirmation...",
            "confidence": None,
            "message": "Using fallback market regime...",
        },
        "news": [],
    }


def _analyst_consensus(symbol: str, price: float | None) -> Dict[str, Any]:
    info = get_quote(symbol)
    buy = hold = sell = 0
    opinions = int(safe_float(info.get("numberOfAnalystOpinions")))
    if opinions > 0:
        recommendation = str(info.get("recommendationKey") or "").lower()
        if recommendation in {"strong_buy", "buy"}:
            buy = max(1, round(opinions * 0.72))
            hold = max(0, round(opinions * 0.22))
            sell = max(0, opinions - buy - hold)
        elif recommendation == "hold":
            hold = max(1, round(opinions * 0.58))
            buy = max(0, round(opinions * 0.30))
            sell = max(0, opinions - buy - hold)
        elif recommendation in {"sell", "strong_sell"}:
            sell = max(1, round(opinions * 0.58))
            hold = max(0, round(opinions * 0.28))
            buy = max(0, opinions - sell - hold)

    high = _nullable_float(info.get("targetHighPrice"))
    average = _nullable_float(info.get("targetMeanPrice"))
    low = _nullable_float(info.get("targetLowPrice"))
    has_target = average is not None or high is not None or low is not None
    has_ratings = opinions > 0 and (buy + hold + sell) > 0
    available = has_target or has_ratings
    implied = round(((average - price) / price * 100.0), 2) if price is not None and price > 0 and average is not None else None

    return {
        "available": available,
        "high": high,
        "average": average,
        "low": low,
        "average_target": average,
        "implied_upside": implied,
        "buy": buy if has_ratings else None,
        "hold": hold if has_ratings else None,
        "sell": sell if has_ratings else None,
    }


def _news(symbol: str) -> List[Dict[str, Any]]:
    raw_news = get_news(symbol)
    items: List[Dict[str, Any]] = []
    for raw in raw_news[:8]:
        content = raw.get("content", raw)
        title = content.get("title") or raw.get("title") or "No News"
        publisher_node = content.get("provider")
        publisher = publisher_node.get("displayName") if isinstance(publisher_node, dict) else content.get("publisher") or raw.get("publisher") or "Yahoo Finance"
        link_node = content.get("clickThroughUrl")
        link = link_node.get("url") if isinstance(link_node, dict) else content.get("link") or raw.get("link") or "#"
        lower = str(title).lower()
        sentiment = "Bullish" if any(word in lower for word in ["beat", "surge", "upgrade", "growth", "record"]) else "Bearish" if any(word in lower for word in ["miss", "drop", "downgrade", "risk", "lawsuit"]) else "Neutral"
        category = "Earnings" if any(word in lower for word in ["earnings", "revenue", "profit"]) else "AI" if "ai" in lower or "artificial intelligence" in lower else "General"
        items.append({
            "title": str(title),
            "publisher": str(publisher),
            "link": str(link),
            "provider_publish_time": raw.get("providerPublishTime") or raw.get("provider_publish_time") or "",
            "sentiment": sentiment,
            "category": category,
            "summary": f"{symbol} market intelligence from live news flow. Monitor price reaction, volume confirmation, and revision risk.",
        })
    return items


def analyze_stock(symbol: str) -> Dict[str, Any]:
    ticker = symbol.strip().upper()
    quote = get_quote(ticker)
    provisional = _resolve_price_snapshot(ticker, quote, {})
    bubble = _safe_engine("bubble", lambda: analyze_bubble(ticker), _fallback_bubble(ticker, quote, provisional["price"]))
    snapshot = _resolve_price_snapshot(ticker, quote, bubble)
    earnings = _safe_engine("earnings_quality", lambda: analyze_earnings_quality(ticker), _fallback_earnings())
    smart = _safe_engine("smart_money", lambda: analyze_smart_money(ticker), _fallback_smart_money())
    regime = _safe_engine("market_regime", detect_market_regime, {"name": "Calibrating", "confidence": 50.0, "fallback": True})
    price = snapshot["price"]
    analyst = _analyst_consensus(ticker, price)
    smart_raw = smart.get("smart_money_score")
    smart_score = safe_float(smart_raw, 50.0) if smart_raw is not None else None
    regime_name = str(regime.get("name") or "Calibrating")
    regime_confidence = safe_float(regime.get("confidence"), 50.0)
    bullish_regimes = {"Bull Expansion", "Bull Consolidation", "Risk-On Momentum", "Inflationary Expansion", "AI Speculative Mania"}
    bearish_regimes = {"High Volatility", "Defensive Rotation", "Recession Risk", "Liquidity Stress"}
    trend = "Bullish" if regime_name in bullish_regimes or (smart_score is not None and smart_score >= 60) else "Bearish" if regime_name in bearish_regimes else "Low Confidence"
    model_available = not bool(regime.get("fallback"))
    smart_component = ((smart_score - 50.0) / 180.0) if smart_score is not None else 0.0
    bull_probability = min(0.92, max(0.08, 0.5 + smart_component + (regime_confidence - 50.0) / 420.0)) if model_available else None
    bubble_data = bubble.get("bubble_analysis_data") or _fallback_bubble(ticker, quote, price)["bubble_analysis_data"]
    if _looks_like_empty_bubble(bubble_data):
        bubble_data = _fallback_bubble(ticker, quote, price)["bubble_analysis_data"]
    if _looks_like_empty_score(earnings, "earnings_quality_score"):
        earnings = _fallback_earnings()
    if _looks_like_empty_score(smart, "smart_money_score"):
        smart = _fallback_smart_money()

    return {
        "ticker": ticker,
        "company_name": _company_name(ticker, quote),
        "price": price,
        "change": snapshot["change"],
        "change_percent": snapshot["change_percent"],
        "market_cap": _resolve_market_cap(quote),
        "sector": _sector(ticker, quote),
        "quote_status": snapshot["source"],
        "bubble_analysis_data": bubble_data,
        "earnings_quality": earnings,
        "smart_money": smart,
        "analyst_targets": analyst,
        "analyst_consensus": analyst,
        "hmm_prediction": {
            "available": model_available,
            "predicted_trend": trend,
            "bull_probability": round(bull_probability, 4) if bull_probability is not None else None,
            "bear_probability": round(1.0 - bull_probability, 4) if bull_probability is not None else None,
            "regime_state": regime_name if model_available else "Awaiting regime confirmation...",
            "confidence": round(min(0.95, max(0.32, regime_confidence / 100.0)), 3) if model_available else None,
            "message": "Using fallback market regime..." if bool(regime.get("fallback")) else "Awaiting regime confirmation...",
        },
        "news": _news(ticker),
    }
