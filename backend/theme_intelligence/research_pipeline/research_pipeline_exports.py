from __future__ import annotations

from .research_pipeline_engine import ResearchPipelineEngine
from .research_pipeline_models import ResearchPipelineCaseDetail


def export_pipeline_case(detail: ResearchPipelineCaseDetail) -> dict:
    return detail.to_dict()


def export_pipeline_cases(engine: ResearchPipelineEngine) -> dict:
    cases = [export_pipeline_case(detail) for detail in engine.list_cases()]
    return {
        "available": True,
        "cases": [
            {
                **row["case"],
                "progress": row["progress"],
                "linked_artifact_count": len(row["links"]),
                "event_count": len(row["timeline"]),
            }
            for row in cases
        ],
        "details": cases,
    }


def export_pipeline_case_detail(engine: ResearchPipelineEngine, case_id: str) -> dict:
    return export_pipeline_case(engine.get_case(case_id))
