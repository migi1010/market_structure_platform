from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from theme_intelligence.industrial_graph.graph_models import content_hash


REQUIRED_SECTION_KEYS = (
    "summary",
    "bull_case",
    "bear_case",
    "evidence_strength",
    "research_gaps",
    "monitoring_triggers",
    "scenario_matrix",
    "open_questions",
    "lineage",
)

FORBIDDEN_FIELD_TOKENS = (
    "buy",
    "sell",
    "hold",
    "target_price",
    "target price",
    "price_target",
    "price target",
    "allocation",
    "portfolio_weight",
    "portfolio weight",
    "recommendation",
    "valuation_model",
    "valuation model",
    "fair_value",
    "fair value",
    "generated_explanation",
    "generated explanation",
    "llm_narrative",
    "llm narrative",
    "conviction_text",
    "conviction text",
)


class DecisionIntelligenceValidationError(ValueError):
    pass


def validate_no_forbidden_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            spaced = normalized.replace("_", " ")
            if normalized in FORBIDDEN_FIELD_TOKENS or spaced in FORBIDDEN_FIELD_TOKENS:
                raise DecisionIntelligenceValidationError(f"Forbidden decision intelligence field at {path}.{key}")
            validate_no_forbidden_fields(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            validate_no_forbidden_fields(item, f"{path}[{index}]")


@dataclass(frozen=True)
class DecisionIntelligenceSection:
    key: str
    rows: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        if self.key not in REQUIRED_SECTION_KEYS:
            raise DecisionIntelligenceValidationError(f"Unknown decision intelligence section: {self.key}")
        normalized_rows = tuple(dict(row) for row in self.rows)
        validate_no_forbidden_fields({self.key: list(normalized_rows)})
        object.__setattr__(self, "rows", normalized_rows)

    def to_dict(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.rows]


@dataclass(frozen=True)
class DecisionIntelligenceLineage:
    scout_candidate_id: str | None
    research_case_id: str
    theme_id: str
    graph_snapshot_id: int | None
    controller_snapshot_id: int | str | None
    opportunity_snapshot_id: int | str | None
    decision_packet_family_version: str | None
    decision_packet_family_revision: int | None
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.research_case_id.strip():
            raise DecisionIntelligenceValidationError("research_case_id is required")
        if not self.theme_id.strip():
            raise DecisionIntelligenceValidationError("theme_id is required")
        object.__setattr__(
            self,
            "evidence_ids",
            tuple(sorted({str(item).strip() for item in self.evidence_ids if str(item).strip()})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scout_candidate_id": self.scout_candidate_id,
            "research_case_id": self.research_case_id,
            "theme_id": self.theme_id,
            "graph_snapshot_id": self.graph_snapshot_id,
            "controller_snapshot_id": self.controller_snapshot_id,
            "opportunity_snapshot_id": self.opportunity_snapshot_id,
            "decision_packet_family_version": self.decision_packet_family_version,
            "decision_packet_family_revision": self.decision_packet_family_revision,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class DecisionIntelligencePacket:
    packet_id: str
    title: str
    theme_id: str
    status: str
    sections: tuple[DecisionIntelligenceSection, ...]
    lineage: DecisionIntelligenceLineage

    def __post_init__(self) -> None:
        if not self.packet_id.strip():
            raise DecisionIntelligenceValidationError("packet_id is required")
        section_keys = tuple(section.key for section in self.sections)
        missing = [key for key in REQUIRED_SECTION_KEYS if key not in section_keys]
        if missing:
            raise DecisionIntelligenceValidationError(f"Missing decision intelligence sections: {', '.join(missing)}")
        duplicate = {key for key in section_keys if section_keys.count(key) > 1}
        if duplicate:
            raise DecisionIntelligenceValidationError(f"Duplicate decision intelligence sections: {', '.join(sorted(duplicate))}")
        ordered = tuple(next(section for section in self.sections if section.key == key) for key in REQUIRED_SECTION_KEYS)
        object.__setattr__(self, "sections", ordered)
        validate_no_forbidden_fields(self.to_dict(include_checksum=False))

    @property
    def checksum(self) -> str:
        return content_hash(self.to_dict(include_checksum=False))

    def to_dict(self, *, include_checksum: bool = True) -> dict[str, Any]:
        payload = {
            "packet_id": self.packet_id,
            "title": self.title,
            "theme_id": self.theme_id,
            "status": self.status,
            "sections": {section.key: section.to_dict() for section in self.sections},
            "lineage": self.lineage.to_dict(),
            "answers": {
                "currently_known": self._section_values("summary"),
                "still_unknown": self._section_values("research_gaps") + self._section_values("open_questions"),
                "supporting_evidence": self._section_values("evidence_strength"),
                "invalidation_conditions": self._section_values("monitoring_triggers"),
            },
        }
        if include_checksum:
            payload["checksum"] = self.checksum
        return payload

    def _section_values(self, key: str) -> list[dict[str, Any]]:
        section = next(section for section in self.sections if section.key == key)
        return section.to_dict()
