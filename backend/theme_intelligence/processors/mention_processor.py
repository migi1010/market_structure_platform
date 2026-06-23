from __future__ import annotations

from theme_intelligence.models import CatalystRecord, CollectorItem, ThemeMention, clamp_score
from theme_intelligence.processors.keyword_expander import KeywordExpander
from theme_intelligence.processors.sentiment_processor import SentimentProcessor
from theme_intelligence.processors.theme_extractor import ThemeExtractor


CATALYST_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("blackwell", "NVIDIA Blackwell", "product_cycle"),
    ("intel packaging", "Intel Packaging", "packaging_capacity"),
    ("ai datacenter expansion", "AI Datacenter Expansion", "capex_cycle"),
    ("data center expansion", "AI Datacenter Expansion", "capex_cycle"),
    ("small modular reactor", "Small Modular Reactor", "energy_supply"),
    ("silicon photonics", "Silicon Photonics", "interconnect"),
)


class MentionProcessor:
    def __init__(
        self,
        extractor: ThemeExtractor | None = None,
        sentiment: SentimentProcessor | None = None,
        keyword_expander: KeywordExpander | None = None,
    ) -> None:
        self.extractor = extractor or ThemeExtractor()
        self.sentiment = sentiment or SentimentProcessor()
        self.keyword_expander = keyword_expander or KeywordExpander()

    def process(self, items: list[CollectorItem]) -> tuple[list[ThemeMention], list[CatalystRecord]]:
        mentions: list[ThemeMention] = []
        catalysts: list[CatalystRecord] = []
        for item in items:
            themes = list(dict.fromkeys([*self.extractor.extract(item.headline), *self.keyword_expander.match(item.headline)]))
            if not themes:
                continue
            sentiment_score = self.sentiment.score(item.headline)
            for theme in themes:
                mentions.append(
                    ThemeMention(
                        theme_name=theme,
                        source=item.source,
                        symbol=item.symbol,
                        headline=item.headline,
                        mention_time=item.published_at,
                        sentiment=sentiment_score,
                    )
                )
                catalysts.extend(self._extract_catalysts(theme, item, sentiment_score))
        return mentions, catalysts

    @staticmethod
    def _extract_catalysts(theme: str, item: CollectorItem, sentiment_score: float) -> list[CatalystRecord]:
        lower = item.headline.lower()
        catalysts: list[CatalystRecord] = []
        for pattern, name, catalyst_type in CATALYST_PATTERNS:
            if pattern in lower:
                catalysts.append(
                    CatalystRecord(
                        theme_name=theme,
                        catalyst_name=name,
                        catalyst_type=catalyst_type,
                        source=item.source,
                        impact_score=clamp_score(55.0 + abs(sentiment_score - 50.0) * 0.8),
                        confidence_score=clamp_score(62.0 + (10.0 if item.source in {"finnhub", "fmp", "sec_filings"} else 0.0)),
                    )
                )
        return catalysts
