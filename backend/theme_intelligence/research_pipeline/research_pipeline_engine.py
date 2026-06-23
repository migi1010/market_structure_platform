from __future__ import annotations

from theme_intelligence.storage.theme_repository import ThemeRepository

from .research_pipeline_models import (
    ResearchPipelineCase,
    ResearchPipelineCaseDetail,
    ResearchPipelineLink,
    ResearchPipelineProgress,
    validate_transition,
)
from .research_pipeline_repository import ResearchPipelineRepository


class ResearchPipelineEngine:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = ResearchPipelineRepository(repository or ThemeRepository())

    def create_case(
        self,
        *,
        source_type: str,
        source_id: str,
        theme_id: str,
        title: str,
    ) -> ResearchPipelineCase:
        return self.repository.create_case(
            source_type=source_type,
            source_id=source_id,
            theme_id=theme_id,
            title=title,
        )

    def list_cases(self) -> tuple[ResearchPipelineCaseDetail, ...]:
        return self.repository.list_cases()

    def get_case(self, case_id: str) -> ResearchPipelineCaseDetail:
        detail = self.repository.get_case(case_id)
        if detail is None:
            raise KeyError(f"Unknown research pipeline case: {case_id}")
        return detail

    def link_artifact(self, case_id: str, linked_type: str, linked_id: str) -> ResearchPipelineLink:
        return self.repository.link_artifact(case_id, linked_type, linked_id)

    def calculate_progress(self, case_id: str) -> ResearchPipelineProgress:
        return self.get_case(case_id).progress

    def transition_case(
        self,
        case_id: str,
        new_status: str,
        *,
        reason: str = "",
    ) -> ResearchPipelineCase:
        detail = self.get_case(case_id)
        validate_transition(
            detail.case.status,
            new_status,
            linked_types={link.linked_type for link in detail.links},
            progress=detail.progress.percent,
            reason=reason,
        )
        return self.repository.update_status(case_id, new_status, reason)

    def audit_lineage(self, case_id: str) -> str:
        detail = self.get_case(case_id)
        return detail.case.lineage_checksum
