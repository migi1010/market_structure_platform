from __future__ import annotations

import hashlib
import re
from dataclasses import replace

from theme_intelligence.models import ThemeMention


PROVIDER_SUFFIXES = ("finnhub", "financial modeling prep", "fmp", "yahoo finance", "sec")


class MentionDeduplicator:
    def deduplicate(self, mentions: list[ThemeMention]) -> list[ThemeMention]:
        unique: dict[str, ThemeMention] = {}
        for mention in mentions:
            mention_hash = self.stable_hash(mention)
            enriched = replace(
                mention,
                mention_hash=mention_hash,
                canonical_headline=self.canonical_headline(mention.headline),
            )
            unique.setdefault(mention_hash, enriched)
        return list(unique.values())

    def stable_hash(self, mention: ThemeMention) -> str:
        canonical = self.canonical_headline(mention.headline)
        symbol = (mention.symbol or "").strip().upper()
        raw = f"{mention.theme_name.strip().lower()}|{symbol}|{canonical}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def canonical_headline(headline: str) -> str:
        text = headline.lower()
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"^[a-z]{1,6}\s*:\s*", " ", text)
        for suffix in PROVIDER_SUFFIXES:
            text = re.sub(rf"\s*[-|]\s*{re.escape(suffix)}\s*$", " ", text)
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()
