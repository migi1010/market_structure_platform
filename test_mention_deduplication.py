from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.models import ThemeMention
from theme_intelligence.processors.mention_deduplicator import MentionDeduplicator


def test_stable_mention_hash_collapses_provider_duplicates() -> None:
    deduper = MentionDeduplicator()
    first = ThemeMention("HBM", "finnhub", "NVDA", "NVDA: NVIDIA Blackwell drives HBM3E demand - Finnhub", "2026-06-05T00:00:00+00:00", 72)
    second = ThemeMention("HBM", "fmp", "NVDA", "NVIDIA Blackwell drives HBM3E demand", "2026-06-05T00:03:00+00:00", 72)

    unique = deduper.deduplicate([first, second])

    assert len(unique) == 1
    assert unique[0].mention_hash == deduper.stable_hash(second)
    assert unique[0].canonical_headline == "nvidia blackwell drives hbm3e demand"


def test_different_theme_keeps_separate_hash() -> None:
    deduper = MentionDeduplicator()
    hbm = ThemeMention("HBM", "finnhub", "NVDA", "NVIDIA Blackwell drives HBM3E demand", "2026-06-05T00:00:00+00:00", 72)
    ai = ThemeMention("AI Infrastructure", "finnhub", "NVDA", "NVIDIA Blackwell drives HBM3E demand", "2026-06-05T00:00:00+00:00", 72)

    assert deduper.stable_hash(hbm) != deduper.stable_hash(ai)
