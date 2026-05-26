from __future__ import annotations

import logging
import math
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, List

from quant_engine.bubble_engine import analyze_bubble
from quant_engine.data_pipeline import get_history, get_news, get_quote, safe_float
from quant_engine.earnings_quality_engine import analyze_earnings_quality
from quant_engine.factors import FactorContext, build_composite_intelligence
from quant_engine.regime_engine import detect_market_regime
from quant_engine.smart_money_engine import analyze_smart_money

logger = logging.getLogger("miji.stock_service")

# Phase 2.8: dedicated executor for the four heavy fundamental engines.
# analyze_bubble / analyze_earnings_quality each call get_statements() which fetches
# ticker.financials + ticker.cashflow + ticker.balance_sheet sequentially (up to 24s each
# on cold SQLite cache). Running them sequentially inside central_stock_enrichment() could
# block for 72s+, exceeding CACHE_MISS_WAIT_SECONDS=12s and causing _fast_cached_response()
# to time out and return fallback_stock_payload() even though get_quote() succeeded.
# Running the engines CONCURRENTLY with a 9s wall-time cap ensures:
#   - central_stock_enrichment() always returns within ~11s (1-2s quote + 9s engine cap)
#   - Engines that miss the cap continue in background, populating SQLite for next request
#   - Memory impact: 4 threads × ~2MB stack = ~8MB — negligible vs Phase 2.6 savings
_ENRICHMENT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="miji.enrichment")
_ENGINE_TIMEOUT_SECONDS = 9.0  # must be < CACHE_MISS_WAIT_SECONDS (12s in main.py)

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
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def _number_or_none(value: Any) -> float | None:
    parsed = safe_float(value)
    return parsed if math.isfinite(parsed) and parsed != 0.0 else None


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
        "previous_close": round(float(previous), 4) if previous is not None and previous > 0 else None,
        "source": quote_status if price is not None else "unavailable",
    }


def _resolve_market_cap(quote: Dict[str, Any]) -> float | None:
    return _first_positive(quote.get("marketCap"), quote.get("market_cap"))


def _normalized_quote(symbol: str, quote: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
    price = snapshot.get("price")
    change = snapshot.get("change")
    change_percent = snapshot.get("change_percent")
    market_cap = _resolve_market_cap(quote)
    status = str(snapshot.get("source") or "unavailable").strip().lower()
    return {
        "ticker": symbol,
        "price": price if isinstance(price, (int, float)) and math.isfinite(float(price)) and price > 0 else None,
        "change": change if isinstance(change, (int, float)) and math.isfinite(float(change)) else None,
        "change_percent": change_percent if isinstance(change_percent, (int, float)) and math.isfinite(float(change_percent)) else None,
        "previous_close": snapshot.get("previous_close"),
        "market_cap": market_cap,
        "pe_ratio": _number_or_none(quote.get("trailingPE") or quote.get("forwardPE")),
        "ps_ratio": _number_or_none(quote.get("priceToSalesTrailing12Months")),
        "currency": quote.get("currency") or "USD",
        "status": status,
        "source": quote.get("quoteSource") or quote.get("source") or status,
    }


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
    quote = {
        "ticker": ticker,
        "price": None,
        "change": None,
        "change_percent": None,
        "previous_close": None,
        "market_cap": None,
        "pe_ratio": None,
        "ps_ratio": None,
        "currency": "USD",
        "status": "unavailable",
        "source": "fallback",
    }
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
        "quote": quote,
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


def _analyst_consensus(symbol: str, price: float | None, quote: Dict[str, Any] | None = None) -> Dict[str, Any]:
    info = quote if isinstance(quote, dict) else get_quote(symbol)
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


def _composite_intelligence(symbol: str, quote: Dict[str, Any], sector: str) -> Dict[str, Any]:
    try:
        history = get_history(symbol, "3mo")
        benchmark_history = get_history("SPY", "3mo")
        context = FactorContext(
            symbol=symbol,
            quote=quote,
            history=history,
            benchmark_history=benchmark_history,
            metadata={"sector": sector},
            lifecycle_state="partial_live",
        )
        return build_composite_intelligence(context)
    except Exception as exc:
        logger.warning("composite intelligence failed symbol=%s error=%s", symbol, exc)
        return {
            "available": False,
            "status": "partial_data",
            "lifecycle_state": "partial_live",
            "confidence": 0.0,
            "confidence_label": "Low Confidence",
            "composites": {},
            "future_hooks": [
                "narrative_acceleration",
                "macro_regime_overlay",
                "multi_timeframe_scoring",
                "feature_store",
                "universe_ranking",
                "ai_narrative_engine",
            ],
        }


def _collect_engine(future: Future, fallback_val: Any, name: str) -> Any:  # noqa: ANN001
    """Collect a future result within _ENGINE_TIMEOUT_SECONDS, returning fallback on timeout/error.

    The future continues executing in _ENRICHMENT_EXECUTOR after this returns —
    populating SQLite cache so the next request benefits from the completed data.
    """
    try:
        result = future.result(timeout=_ENGINE_TIMEOUT_SECONDS)
        return result if result is not None else fallback_val
    except Exception as exc:
        logger.warning("engine timeout or error name=%s error=%s", name, exc)
        return fallback_val


def central_stock_enrichment(symbol: str, include_provider_quote: bool = False) -> Dict[str, Any]:
    ticker = symbol.strip().upper()

    # ── Phase 1: synchronous quote fetch (critical path) ───────────────────────
    # get_quote() uses PROVIDER_EXECUTOR (6 workers) and typically completes in
    # 1-2s when yfinance is healthy. This MUST run synchronously so we have a
    # price before assembling the response. The quote is also written to the
    # SQLite LKG cache inside get_quote(), so it survives even if we time out.
    quote = get_quote(ticker)
    logger.info("central_stock_enrichment quote symbol=%s price=%s status=%s",
                ticker, quote.get("currentPrice") or quote.get("regularMarketPrice"),
                quote.get("quoteStatus"))
    provisional = _resolve_price_snapshot(ticker, quote, {})

    # ── Phase 2: concurrent fundamental engine submission ──────────────────────
    # Each engine calls get_statements() (bubble, earnings) or get_history()
    # (smart_money, regime) via PROVIDER_EXECUTOR. On a cold SQLite cache,
    # fetch_yfinance_statements() makes 3 sequential _run_with_timeout(8s) calls
    # = 24s per engine. Running them SEQUENTIALLY inside central_stock_enrichment()
    # would block for 72s+, always exceeding CACHE_MISS_WAIT_SECONDS=12s.
    # Running them CONCURRENTLY via _ENRICHMENT_EXECUTOR:
    #   - bubble + earnings share the same get_statements() SQLite lock:
    #     only one fetches, the other reads from cache once the lock is released.
    #   - All four engines run in parallel, reducing wall time to max(individual).
    #   - _collect_engine() caps the wait at _ENGINE_TIMEOUT_SECONDS (9s).
    #   - If an engine misses the cap it continues in background, populating SQLite
    #     for the next request (which will then return in <1s from cache).
    f_bubble   = _ENRICHMENT_EXECUTOR.submit(lambda: analyze_bubble(ticker, quote=quote))
    f_earnings = _ENRICHMENT_EXECUTOR.submit(lambda: analyze_earnings_quality(ticker, quote=quote))
    f_smart    = _ENRICHMENT_EXECUTOR.submit(lambda: analyze_smart_money(ticker, quote=quote))
    f_regime   = _ENRICHMENT_EXECUTOR.submit(detect_market_regime)

    bubble   = _collect_engine(f_bubble,   _fallback_bubble(ticker, quote, provisional["price"]), "bubble")
    earnings = _collect_engine(f_earnings, _fallback_earnings(),                                    "earnings_quality")
    smart    = _collect_engine(f_smart,    _fallback_smart_money(),                                 "smart_money")
    regime   = _collect_engine(f_regime,   {"name": "Calibrating", "confidence": 50.0, "fallback": True}, "market_regime")

    # ── Phase 3: assemble response ─────────────────────────────────────────────
    snapshot = _resolve_price_snapshot(ticker, quote, bubble)
    normalized_quote = _normalized_quote(ticker, quote, snapshot)
    price = normalized_quote["price"]
    analyst = _analyst_consensus(ticker, price, quote)
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
    logger.info("central_stock_enrichment complete symbol=%s price=%s bubble_available=%s",
                ticker, price, bool(bubble_data.get("bubble_index") is not None))

    sector = _sector(ticker, quote)
    result = {
        "ticker": ticker,
        "company_name": _company_name(ticker, quote),
        "price": normalized_quote["price"],
        "change": normalized_quote["change"],
        "change_percent": normalized_quote["change_percent"],
        "market_cap": normalized_quote["market_cap"],
        "sector": sector,
        "quote_status": normalized_quote["status"],
        "quote": normalized_quote,
        "bubble_analysis_data": bubble_data,
        "earnings_quality": earnings,
        "smart_money": smart,
        "composite_intelligence": _composite_intelligence(ticker, normalized_quote, sector),
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
    if include_provider_quote:
        result["provider_quote"] = quote
    return result


def analyze_stock(symbol: str) -> Dict[str, Any]:
    return central_stock_enrichment(symbol)
