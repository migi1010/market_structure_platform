from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from theme_intelligence.industrial_graph.graph_models import content_hash


PIPELINE_STATUSES = (
    "DISCOVERED",
    "OBSERVING",
    "RESEARCHING",
    "VALIDATING",
    "REVIEW_READY",
    "APPROVED_RESEARCH",
    "MONITORING",
    "ARCHIVED",
)
PIPELINE_BOARD_STATUSES = (
    "DISCOVERED",
    "OBSERVING",
    "RESEARCHING",
    "VALIDATING",
    "REVIEW_READY",
    "MONITORING",
)
ALLOWED_SOURCE_TYPES = {"SCOUT_CANDIDATE", "THEME"}
ALLOWED_LINK_TYPES = {
    "SCOUT_CANDIDATE",
    "THEME",
    "SUPPLY_CHAIN_VALIDATION",
    "GRAPH_SNAPSHOT",
    "CONTROLLER",
    "OPPORTUNITY",
    "DECISION_PACKET",
}
PROGRESS_LINK_TYPES = {
    "theme_narrative": {"THEME"},
    "supply_chain_validation": {"SUPPLY_CHAIN_VALIDATION", "GRAPH_SNAPSHOT"},
    "controller_review": {"CONTROLLER"},
    "opportunity_review": {"OPPORTUNITY"},
    "decision_packet_link": {"DECISION_PACKET"},
}


class PipelineValidationError(ValueError):
    pass


class PipelineTransitionError(PipelineValidationError):
    pass


@dataclass(frozen=True)
class ResearchPipelineCase:
    case_id: str
    source_type: str
    source_id: str
    theme_id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    activated_at: str | None
    archived_at: str | None
    lineage_checksum: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ResearchPipelineEvent:
    event_id: str
    case_id: str
    previous_status: str | None
    new_status: str
    reason: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ResearchPipelineLink:
    link_id: str
    case_id: str
    linked_type: str
    linked_id: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ResearchPipelineProgress:
    percent: int
    sections: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {"percent": self.percent, "sections": dict(self.sections)}


@dataclass(frozen=True)
class ResearchPipelineCaseDetail:
    case: ResearchPipelineCase
    events: tuple[ResearchPipelineEvent, ...]
    links: tuple[ResearchPipelineLink, ...]
    progress: ResearchPipelineProgress

    def to_dict(self) -> dict[str, Any]:
        return {
            "case": self.case.to_dict(),
            "timeline": [event.to_dict() for event in self.events],
            "links": [link.to_dict() for link in self.links],
            "progress": self.progress.to_dict(),
        }


def validate_status(status: str) -> str:
    normalized = status.strip().upper()
    if normalized not in PIPELINE_STATUSES:
        raise PipelineValidationError(f"Unknown research pipeline status: {status}")
    return normalized


def validate_source_type(source_type: str) -> str:
    normalized = source_type.strip().upper()
    if normalized not in ALLOWED_SOURCE_TYPES:
        raise PipelineValidationError(f"Unsupported research source type: {source_type}")
    return normalized


def validate_link_type(linked_type: str) -> str:
    normalized = linked_type.strip().upper()
    if normalized not in ALLOWED_LINK_TYPES:
        raise PipelineValidationError(f"Unsupported research link type: {linked_type}")
    return normalized


def calculate_progress_from_link_types(linked_types: set[str]) -> ResearchPipelineProgress:
    sections = {
        section: bool(accepted & linked_types)
        for section, accepted in PROGRESS_LINK_TYPES.items()
    }
    return ResearchPipelineProgress(
        percent=sum(20 for complete in sections.values() if complete),
        sections=sections,
    )


def validate_transition(
    previous_status: str,
    new_status: str,
    *,
    linked_types: set[str],
    progress: int,
    reason: str,
) -> None:
    previous = validate_status(previous_status)
    target = validate_status(new_status)
    if previous == target:
        return
    if target == "ARCHIVED":
        return
    previous_index = PIPELINE_STATUSES.index(previous)
    expected_index = previous_index + 1
    if expected_index >= len(PIPELINE_STATUSES) or PIPELINE_STATUSES[expected_index] != target:
        raise PipelineTransitionError(f"Illegal research transition: {previous} -> {target}")
    evidence_linked_types = linked_types - {"SCOUT_CANDIDATE"}
    if target == "VALIDATING" and not evidence_linked_types:
        raise PipelineTransitionError("VALIDATING requires at least one linked evidence-bearing artifact")
    if target == "REVIEW_READY" and progress < 100:
        raise PipelineTransitionError("REVIEW_READY requires all research progress sections complete")
    if target == "APPROVED_RESEARCH" and not reason.strip():
        raise PipelineTransitionError("APPROVED_RESEARCH requires a manual approval reason")


def lineage_checksum(source_type: str, source_id: str, theme_id: str, title: str) -> str:
    return content_hash({
        "source_type": source_type,
        "source_id": source_id,
        "theme_id": theme_id,
        "title": title,
    })
