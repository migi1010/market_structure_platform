from __future__ import annotations

from theme_intelligence.catalysts.catalyst_classifier import CatalystClassifier
from theme_intelligence.models import CatalystRecord, ThemeMention


CATALYST_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("product_launch", ("product launch", "launch", "blackwell", "hbm3e", "new platform"), "Product Launch"),
    ("capex", ("capex", "capital expenditure", "datacenter expansion", "data center expansion", "capacity expansion"), "Capex"),
    ("earnings_call", ("earnings call", "conference call", "management commentary", "guidance"), "Earnings Call"),
    ("supply_shortage", ("supply shortage", "shortage", "capacity constraint", "bottleneck", "tight supply"), "Supply Shortage"),
    ("policy", ("policy", "subsidy", "regulation", "government", "tax credit"), "Policy"),
    ("technology_breakthrough", ("breakthrough", "silicon photonics", "panel level packaging", "glass core substrate"), "Technology Breakthrough"),
    ("customer_adoption", ("customer adoption", "customer demand", "design win", "order", "contract"), "Customer Adoption"),
)


class CatalystExtractor:
    def __init__(self, classifier: CatalystClassifier | None = None) -> None:
        self.classifier = classifier or CatalystClassifier()

    def extract(self, mentions: list[ThemeMention]) -> list[CatalystRecord]:
        catalysts: list[CatalystRecord] = []
        seen: set[tuple[str, str, str]] = set()
        for mention in mentions:
            lower = mention.headline.lower()
            for catalyst_type, terms, label in CATALYST_RULES:
                if not any(term in lower for term in terms):
                    continue
                name = self._name_for(label, mention)
                key = (mention.theme_name, catalyst_type, name)
                if key in seen:
                    continue
                seen.add(key)
                classified = self.classifier.classify(
                    mention.theme_name,
                    mention.headline,
                    mention.source,
                    mention.symbol,
                    mention.sentiment,
                    mention.mention_time,
                )
                catalysts.append(
                    CatalystRecord(
                        theme_name=mention.theme_name,
                        catalyst_name=classified.catalyst_name or name,
                        catalyst_type=classified.catalyst_type,
                        source=mention.source,
                        impact_score=classified.impact_score,
                        confidence_score=classified.confidence_score,
                        description=classified.description,
                        polarity=classified.polarity,
                        created_at=mention.mention_time,
                        updated_at=mention.mention_time,
                    )
                )
        return catalysts

    @staticmethod
    def _name_for(label: str, mention: ThemeMention) -> str:
        symbol = f"{mention.symbol} " if mention.symbol else ""
        return f"{symbol}{label}".strip()
