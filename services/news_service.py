from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def _category(title: str) -> str:
    lower = title.lower()
    if any(word in lower for word in ["earnings", "revenue", "profit"]):
        return "Earnings"
    if any(word in lower for word in ["ai", "artificial intelligence", "chip"]):
        return "AI"
    if any(word in lower for word in ["regulation", "sec", "lawsuit"]):
        return "Regulation"
    if "insider" in lower:
        return "Insider Trading"
    if any(word in lower for word in ["merger", "acquire", "m&a"]):
        return "M&A"
    if any(word in lower for word in ["fed", "inflation", "rates"]):
        return "Macro"
    return "General"


def _sentiment(title: str) -> str:
    lower = title.lower()
    if any(word in lower for word in ["beat", "surge", "rally", "upgrade", "growth", "record"]):
        return "Bullish"
    if any(word in lower for word in ["miss", "fall", "drop", "downgrade", "lawsuit", "risk"]):
        return "Bearish"
    return "Neutral"


def normalize_news(news: List[Dict[str, Any]], symbol: str) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in news[:8]:
        content = item.get("content", item)
        title = content.get("title") or item.get("title") or "No News"
        url_node = content.get("clickThroughUrl") or {}
        link = url_node.get("url") if isinstance(url_node, dict) else content.get("link")
        publisher_node = content.get("provider") or {}
        publisher = publisher_node.get("displayName") if isinstance(publisher_node, dict) else item.get("publisher")
        publish_time = content.get("pubDate") or item.get("providerPublishTime")
        if isinstance(publish_time, (int, float)):
            publish_time = datetime.fromtimestamp(publish_time, tz=timezone.utc).isoformat()
        normalized.append(
            {
                "title": title,
                "publisher": publisher or "Yahoo Finance",
                "link": link or item.get("link") or "#",
                "provider_publish_time": publish_time or datetime.now(timezone.utc).isoformat(),
                "sentiment": _sentiment(title),
                "category": _category(title),
                "summary": f"{symbol} related {_category(title).lower()} intelligence detected from live market news.",
            }
        )
    return normalized
