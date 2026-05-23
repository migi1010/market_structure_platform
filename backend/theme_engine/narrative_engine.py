from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from alpha_engine.scoring import bounded_score
from quant_engine.data_pipeline import get_news, safe_float

from .theme_detector import ThemeDefinition, get_theme_definitions


def _news_text(item: Dict[str, Any]) -> str:
    parts = [
        item.get("title"),
        item.get("summary"),
        item.get("publisher"),
        item.get("content"),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _keyword_hits(texts: Iterable[str], keywords: Iterable[str]) -> int:
    lowered_keywords = [keyword.lower() for keyword in keywords]
    return sum(1 for text in texts for keyword in lowered_keywords if keyword and keyword in text)


def analyze_theme_narrative(theme: ThemeDefinition, news_limit_per_symbol: int = 3) -> Dict[str, Any]:
    texts: List[str] = []
    articles: List[Dict[str, Any]] = []
    for symbol in theme.tickers[:4]:
        try:
            for item in get_news(symbol)[:news_limit_per_symbol]:
                texts.append(_news_text(item))
                articles.append({
                    "ticker": symbol,
                    "title": str(item.get("title") or ""),
                    "publisher": str(item.get("publisher") or item.get("provider") or ""),
                    "link": str(item.get("link") or ""),
                })
        except Exception:
            continue

    hits = _keyword_hits(texts, theme.narrative_keywords)
    article_count = max(len(texts), 1)
    hit_density = hits / article_count
    narrative_strength = bounded_score(38.0 + hit_density * 18.0 + min(article_count, 12) * 2.0)
    narrative_acceleration = bounded_score(35.0 + min(hits, 12) * 4.5)
    narrative_saturation = bounded_score(max(20.0, narrative_strength - 10.0) + max(0, hits - 6) * 3.0)
    narrative_bubble_risk = bounded_score(narrative_saturation * 0.72 + max(0.0, narrative_acceleration - 70.0) * 0.45)

    return {
        "theme": theme.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "yfinance_news_with_market_proxy",
        "keywords": list(theme.narrative_keywords),
        "article_count": len(articles),
        "keyword_hits": hits,
        "narrative_strength": narrative_strength,
        "narrative_acceleration": narrative_acceleration,
        "narrative_saturation": narrative_saturation,
        "narrative_bubble_risk": narrative_bubble_risk,
        "articles": articles[:8],
        "summary": _narrative_summary(theme.name, narrative_strength, narrative_acceleration, narrative_saturation),
    }


def analyze_all_narratives(limit: int = 12) -> Dict[str, Any]:
    narratives = [analyze_theme_narrative(theme) for theme in get_theme_definitions()[:limit]]
    narratives.sort(key=lambda item: safe_float(item.get("narrative_acceleration")), reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "narratives": narratives,
    }


def _narrative_summary(theme_name: str, strength: float, acceleration: float, saturation: float) -> str:
    if acceleration >= 75 and saturation < 75:
        return f"{theme_name} narrative is accelerating without broad saturation, a constructive early-theme profile."
    if saturation >= 80:
        return f"{theme_name} narrative is widely saturated; monitor bubble risk and crowding."
    if strength >= 65:
        return f"{theme_name} narrative remains institutionally relevant with steady market attention."
    return f"{theme_name} narrative is present but not yet dominant in available market news."
