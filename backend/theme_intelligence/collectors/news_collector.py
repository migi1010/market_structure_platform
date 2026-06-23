from __future__ import annotations

import time
from typing import Any

import requests

from settings import get_settings
from theme_intelligence.models import CollectorItem, utc_now_iso


NEWS_SYMBOLS: tuple[str, ...] = (
    "NVDA",
    "AMD",
    "AVGO",
    "TSM",
    "INTC",
    "MU",
    "GLW",
    "ANET",
    "VRT",
    "ETN",
    "CEG",
    "SMR",
    "ISRG",
    "TER",
    "RKLB",
    "IONQ",
)


class NewsCollector:
    def __init__(self, symbols: tuple[str, ...] = NEWS_SYMBOLS) -> None:
        self.symbols = symbols

    def collect(self) -> list[CollectorItem]:
        return [*self._collect_finnhub(), *self._collect_fmp()]

    def _collect_finnhub(self) -> list[CollectorItem]:
        settings = get_settings()
        if not settings.finnhub_api_key:
            return []
        items: list[CollectorItem] = []
        today = time.strftime("%Y-%m-%d", time.gmtime())
        for symbol in self.symbols[:10]:
            try:
                response = requests.get(
                    "https://finnhub.io/api/v1/company-news",
                    params={"symbol": symbol, "from": today, "to": today, "token": settings.finnhub_api_key},
                    timeout=settings.provider_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception:
                continue
            for row in payload[:8] if isinstance(payload, list) else []:
                headline = str(row.get("headline") or "").strip()
                if not headline:
                    continue
                published = row.get("datetime")
                published_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(published))) if published else utc_now_iso()
                items.append(
                    CollectorItem(
                        source="finnhub",
                        symbol=symbol,
                        headline=headline,
                        published_at=published_at,
                        url=row.get("url"),
                        raw=row,
                    )
                )
        return items

    def _collect_fmp(self) -> list[CollectorItem]:
        settings = get_settings()
        if not settings.fmp_api_key:
            return []
        items: list[CollectorItem] = []
        try:
            response = requests.get(
                "https://financialmodelingprep.com/api/v3/stock_news",
                params={"tickers": ",".join(self.symbols[:12]), "limit": 50, "apikey": settings.fmp_api_key},
                timeout=settings.provider_timeout_seconds,
            )
            response.raise_for_status()
            payload: Any = response.json()
        except Exception:
            return []
        for row in payload if isinstance(payload, list) else []:
            headline = str(row.get("title") or row.get("headline") or "").strip()
            if not headline:
                continue
            items.append(
                CollectorItem(
                    source="fmp",
                    symbol=str(row.get("symbol") or "").upper() or None,
                    headline=headline,
                    published_at=str(row.get("publishedDate") or row.get("date") or utc_now_iso()),
                    url=row.get("url"),
                    raw=row,
                )
            )
        return items
