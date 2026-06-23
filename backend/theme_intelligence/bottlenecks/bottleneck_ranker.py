from __future__ import annotations

from typing import Any

from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord


class BottleneckRanker:
    def rank(self, records: list[BottleneckRecord]) -> dict[str, Any]:
        ranked = sorted(records, key=lambda row: row.bottleneck_strength, reverse=True)
        primary = ranked[0] if ranked else None
        controllers = self._dedupe_entities([item for row in ranked for item in row.controller_entities])
        beneficiaries = self._dedupe_entities([item for row in ranked for item in row.beneficiaries])
        if primary is None:
            return {
                "primary_bottleneck": None,
                "secondary_bottlenecks": [],
                "controllers": [],
                "beneficiaries": [],
                "resolution_probability": 0.0,
                "why_it_matters": "",
                "what_fixes_it": [],
                "who_controls_it": [],
                "who_benefits": [],
                "what_to_monitor": [],
            }
        primary_payload = primary.to_api()
        return {
            "primary_bottleneck": primary_payload,
            "secondary_bottlenecks": [row.to_api() for row in ranked[1:5]],
            "controllers": controllers[:8],
            "beneficiaries": beneficiaries[:8],
            "resolution_probability": primary.resolution_probability,
            "why_it_matters": self._why_it_matters(primary),
            "what_fixes_it": primary_payload["what_fixes_it"],
            "who_controls_it": controllers[:8],
            "who_benefits": beneficiaries[:8],
            "what_to_monitor": primary_payload["what_to_monitor"],
        }

    @staticmethod
    def _dedupe_entities(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            key = str(row.get("ticker") or row.get("company_name") or row)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped

    @staticmethod
    def _why_it_matters(record: BottleneckRecord) -> str:
        return (
            f"{record.bottleneck_name} is the strongest identified constraint for {record.theme_name}; "
            "it may limit scaling until resolution evidence improves."
        )
