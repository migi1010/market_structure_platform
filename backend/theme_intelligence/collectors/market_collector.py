from __future__ import annotations

from theme_intelligence.models import CollectorItem, utc_now_iso

from quant_engine.data_pipeline import get_quote, safe_float


MARKET_SYMBOLS: tuple[str, ...] = ("SPY", "QQQ", "SMH", "SOXX", "XLK", "XLI", "XLF", "XLV", "XLE")


class MarketCollector:
    def __init__(self, symbols: tuple[str, ...] = MARKET_SYMBOLS) -> None:
        self.symbols = symbols

    def collect(self) -> list[CollectorItem]:
        items: list[CollectorItem] = []
        for symbol in self.symbols:
            try:
                quote = get_quote(symbol)
            except Exception:
                continue
            change = safe_float(quote.get("regularMarketChangePercent") or quote.get("change_percent"))
            price = quote.get("currentPrice") or quote.get("regularMarketPrice") or quote.get("price")
            headline = f"{symbol} market proxy change {change:.2f}% with price {price or 'unavailable'}"
            items.append(
                CollectorItem(
                    source="market",
                    symbol=symbol,
                    headline=headline,
                    published_at=utc_now_iso(),
                    raw={"change_percent": change, "price": price, **quote},
                )
            )
        return items
