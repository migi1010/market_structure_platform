from __future__ import annotations

from typing import Any, Dict, List

from quant_engine.bubble_engine import analyze_bubble
from quant_engine.data_pipeline import get_news, get_quote, safe_float
from quant_engine.earnings_quality_engine import analyze_earnings_quality
from quant_engine.regime_engine import detect_market_regime
from quant_engine.smart_money_engine import analyze_smart_money


def _analyst_consensus(symbol: str, price: float) -> Dict[str, float]:
    info = get_quote(symbol)
    buy = hold = sell = 0.0
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

    average = safe_float(info.get("targetMeanPrice"))
    implied = ((average - price) / price * 100.0) if price > 0 and average > 0 else 0.0
    return {
        "high": safe_float(info.get("targetHighPrice")),
        "average": average,
        "low": safe_float(info.get("targetLowPrice")),
        "average_target": average,
        "implied_upside": round(implied, 2),
        "buy": float(buy),
        "hold": float(hold),
        "sell": float(sell),
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
    bubble = analyze_bubble(ticker)
    earnings = analyze_earnings_quality(ticker)
    smart = analyze_smart_money(ticker)
    regime = detect_market_regime()
    price = safe_float(quote.get("currentPrice") or quote.get("regularMarketPrice") or bubble.get("price"))
    analyst = _analyst_consensus(ticker, price)
    trend = "Bullish" if smart["smart_money_score"] >= 60 and regime["name"] in {"Bull Market", "Momentum Mania"} else "Bearish" if regime["name"] in {"Bear Market", "Risk-off"} else "Neutral"
    bull_probability = min(0.92, max(0.08, 0.5 + (smart["smart_money_score"] - 50.0) / 150.0))

    return {
        "ticker": ticker,
        "company_name": quote.get("longName") or quote.get("shortName") or ticker,
        "price": price,
        "change_percent": safe_float(quote.get("regularMarketChangePercent")),
        "market_cap": safe_float(quote.get("marketCap")),
        "sector": quote.get("sector") or "Unknown",
        "bubble_analysis_data": bubble["bubble_analysis_data"],
        "earnings_quality": earnings,
        "smart_money": smart,
        "analyst_targets": analyst,
        "analyst_consensus": analyst,
        "hmm_prediction": {
            "predicted_trend": trend,
            "bull_probability": round(bull_probability, 4),
            "bear_probability": round(1.0 - bull_probability, 4),
            "regime_state": regime["name"],
            "confidence": round(min(0.95, max(0.45, regime["confidence"] / 100.0)), 3),
        },
        "news": _news(ticker),
    }
