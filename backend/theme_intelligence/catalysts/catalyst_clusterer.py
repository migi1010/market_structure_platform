from __future__ import annotations

import re
from statistics import mean

from theme_intelligence.catalysts.catalyst_models import CatalystEvent
from theme_intelligence.models import clamp_score


ENTITY_ALIASES: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("intel", "intc"), "intel", "Intel"),
    (("nvidia", "nvda"), "nvidia", "NVIDIA"),
    (("tsmc", "tsm"), "tsmc", "TSMC"),
    (("micron", "mu"), "micron", "Micron"),
    (("apple", "aapl"), "apple", "Apple"),
    (("hyperscaler", "datacenter", "data center"), "hyperscaler", "Hyperscaler"),
)

ACTION_ALIASES: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("expansion", "investment", "capacity increase", "capacity expansion", "capex"), "expansion", "Expansion"),
    (("launch", "ramp", "blackwell", "hbm4", "mi400"), "launch", "Launch"),
    (("shortage", "tight supply", "constraint", "bottleneck"), "shortage", "Shortage"),
    (("adoption", "deployment", "design win", "customer demand"), "adoption", "Adoption"),
    (("guidance", "earnings call", "management commentary"), "guidance", "Guidance"),
    (("subsidy", "policy", "regulation", "tax credit"), "policy", "Policy"),
    (("yield", "breakthrough", "process"), "breakthrough", "Breakthrough"),
    (("demand", "orders"), "demand", "Demand"),
)

OBJECT_ALIASES: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("packaging", "substrate", "advanced packaging", "glass substrate"), "packaging", "Packaging"),
    (("hbm", "hbm3e", "hbm4", "memory"), "hbm", "HBM"),
    (("power", "grid", "transformer"), "power_grid", "Power Grid"),
    (("robot", "robotics", "humanoid"), "robotics", "Robotics"),
    (("photonics", "optical", "cpo"), "photonics", "Photonics"),
    (("datacenter", "data center", "ai server"), "datacenter", "Datacenter"),
)


class CatalystClusterer:
    def cluster(self, events: list[CatalystEvent]) -> list[CatalystEvent]:
        groups: dict[str, list[CatalystEvent]] = {}
        for event in events:
            key = event.cluster_key or self.cluster_key(event)
            groups.setdefault(key, []).append(event.with_updates(cluster_key=key, catalyst_name=self.cluster_name(event)))
        return [self._merge(rows) for rows in groups.values()]

    def cluster_key(self, event: CatalystEvent) -> str:
        text = f"{event.catalyst_name} {event.description}".lower()
        theme = re.sub(r"[^a-z0-9]+", "_", event.theme_name.lower()).strip("_")
        entity, _ = self._match(text, ENTITY_ALIASES, "unknown", "")
        action, _ = self._match(text, ACTION_ALIASES, self._action_from_type(event.catalyst_type), "")
        obj, _ = self._match(text, OBJECT_ALIASES, self._object_from_theme(event.theme_name), "")
        return f"{theme}:{entity}:{obj}_{action}"

    def cluster_name(self, event: CatalystEvent) -> str:
        text = f"{event.catalyst_name} {event.description}".lower()
        _, entity_label = self._match(text, ENTITY_ALIASES, "", "")
        _, action_label = self._match(text, ACTION_ALIASES, "", self._label_from_type(event.catalyst_type))
        _, object_label = self._match(text, OBJECT_ALIASES, "", self._label_from_theme(event.theme_name))
        parts = [part for part in (entity_label, object_label, action_label) if part]
        return " ".join(dict.fromkeys(parts)) or event.catalyst_name

    @staticmethod
    def _match(text: str, aliases: tuple[tuple[tuple[str, ...], str, str], ...], default_key: str, default_label: str) -> tuple[str, str]:
        for terms, key, label in aliases:
            if any(term in text for term in terms):
                return key, label
        return default_key, default_label

    @staticmethod
    def _action_from_type(catalyst_type: str) -> str:
        return {
            "Product Launch": "launch",
            "CapEx Expansion": "expansion",
            "Earnings Call Signal": "guidance",
            "Supply Shortage": "shortage",
            "Technology Breakthrough": "breakthrough",
            "Customer Adoption": "adoption",
            "Policy / Regulation": "policy",
            "Industry Demand": "demand",
        }.get(catalyst_type, "signal")

    @staticmethod
    def _object_from_theme(theme_name: str) -> str:
        lower = theme_name.lower()
        if "glass" in lower or "packaging" in lower or "cowos" in lower:
            return "packaging"
        if "hbm" in lower:
            return "hbm"
        if "power" in lower:
            return "power_grid"
        return "theme"

    @staticmethod
    def _label_from_type(catalyst_type: str) -> str:
        return catalyst_type.replace("CapEx", "CapEx").replace(" / Regulation", "")

    @staticmethod
    def _label_from_theme(theme_name: str) -> str:
        if theme_name in {"Glass Substrate", "Advanced Packaging", "CoWoS"}:
            return "Packaging"
        return theme_name

    @staticmethod
    def _merge(rows: list[CatalystEvent]) -> CatalystEvent:
        ordered_sources = list(dict.fromkeys(source for row in rows for source in row.source.split(",") if source))
        best = sorted(rows, key=lambda row: row.impact_score + row.confidence_score, reverse=True)[0]
        strengths = [row.catalyst_strength for row in rows if row.catalyst_strength > 0]
        return best.with_updates(
            source=",".join(ordered_sources),
            description=best.description,
            impact_score=clamp_score(max(row.impact_score for row in rows)),
            confidence_score=clamp_score(mean(row.confidence_score for row in rows) + min(12.0, (len(rows) - 1) * 4.0)),
            novelty_score=clamp_score(max(row.novelty_score for row in rows)),
            duration_score=clamp_score(max(row.duration_score for row in rows)),
            stage_relevance=clamp_score(max(row.stage_relevance for row in rows)),
            catalyst_strength=clamp_score(max(strengths) if strengths else 0.0),
            created_at=min(row.created_at for row in rows),
            updated_at=max(row.updated_at for row in rows),
            polarity="risk" if any(row.polarity == "risk" for row in rows) else "positive",
        )
