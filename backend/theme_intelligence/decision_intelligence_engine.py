from __future__ import annotations

from typing import Any

from theme_intelligence.aggregate import ThemeIntelligenceAggregateService
from theme_intelligence.decision_intelligence_models import (
    DecisionIntelligenceLineage,
    DecisionIntelligencePacket,
    DecisionIntelligenceSection,
)
from theme_intelligence.decision_intelligence_repository import DecisionIntelligenceRepository
from theme_intelligence.research_pipeline.research_pipeline_models import (
    PROGRESS_LINK_TYPES,
    ResearchPipelineCaseDetail,
)
from theme_intelligence.storage.theme_repository import ThemeRepository


class DecisionIntelligenceEngine:
    def __init__(
        self,
        repository: ThemeRepository | None = None,
        *,
        aggregate_service: ThemeIntelligenceAggregateService | None = None,
    ) -> None:
        self.repository = DecisionIntelligenceRepository(repository or ThemeRepository())
        self.aggregate_service = aggregate_service or ThemeIntelligenceAggregateService(self.repository.repository)

    def list_packets(self) -> tuple[DecisionIntelligencePacket, ...]:
        return tuple(self.build_packet(detail.case.case_id) for detail in self.repository.list_research_cases())

    def get_packet(self, packet_id: str) -> DecisionIntelligencePacket | None:
        case_id = packet_id.removeprefix("decision-intelligence:")
        detail = self.repository.get_research_case(case_id)
        if detail is None:
            return None
        return self._build_from_detail(detail)

    def build_packet(self, case_id: str) -> DecisionIntelligencePacket:
        detail = self.repository.get_research_case(case_id)
        if detail is None:
            raise KeyError(f"Unknown research pipeline case: {case_id}")
        return self._build_from_detail(detail)

    def _build_from_detail(self, detail: ResearchPipelineCaseDetail) -> DecisionIntelligencePacket:
        aggregate = self._aggregate(detail.case.theme_id)
        industrial = _dict(aggregate.get("industrial_intelligence"))
        lineage = self._lineage(detail, industrial)
        sections = (
            DecisionIntelligenceSection("summary", tuple(self._summary_rows(detail, aggregate, industrial))),
            DecisionIntelligenceSection("bull_case", tuple(self._bull_rows(detail, aggregate, industrial))),
            DecisionIntelligenceSection("bear_case", tuple(self._bear_rows(detail, aggregate, industrial))),
            DecisionIntelligenceSection("evidence_strength", tuple(self._evidence_rows(detail, aggregate, industrial, lineage))),
            DecisionIntelligenceSection("research_gaps", tuple(self._gap_rows(detail, aggregate, industrial))),
            DecisionIntelligenceSection("monitoring_triggers", tuple(self._monitoring_rows(detail, aggregate, industrial))),
            DecisionIntelligenceSection("scenario_matrix", tuple(self._scenario_rows(detail, aggregate, industrial))),
            DecisionIntelligenceSection("open_questions", tuple(self._question_rows(detail, aggregate, industrial))),
            DecisionIntelligenceSection("lineage", (lineage.to_dict(),)),
        )
        return DecisionIntelligencePacket(
            packet_id=f"decision-intelligence:{detail.case.case_id}",
            title=detail.case.title,
            theme_id=detail.case.theme_id,
            status=detail.case.status,
            sections=sections,
            lineage=lineage,
        )

    def _aggregate(self, theme_id: str) -> dict[str, Any]:
        try:
            return self.aggregate_service.get_theme(theme_id)
        except Exception:
            return {
                "theme_id": theme_id,
                "name": theme_id.replace("_", " ").title(),
                "catalysts": {"top_catalysts": []},
                "bottlenecks": {"primary_bottleneck": None, "what_to_monitor": []},
                "beneficiaries": {"top_beneficiaries": []},
                "industrial_intelligence": {},
            }

    @staticmethod
    def _lineage(detail: ResearchPipelineCaseDetail, industrial: dict[str, Any]) -> DecisionIntelligenceLineage:
        links = _links_by_type(detail)
        lineage = _dict(industrial.get("lineage"))
        evidence_ids = _collect_evidence_ids(industrial)
        return DecisionIntelligenceLineage(
            scout_candidate_id=detail.case.source_id if detail.case.source_type == "SCOUT_CANDIDATE" else _first(links, "SCOUT_CANDIDATE"),
            research_case_id=detail.case.case_id,
            theme_id=detail.case.theme_id,
            graph_snapshot_id=_int_or_none(_first(links, "GRAPH_SNAPSHOT") or lineage.get("graph_snapshot_id")),
            controller_snapshot_id=_first(links, "CONTROLLER") or lineage.get("controller_snapshot_id"),
            opportunity_snapshot_id=_first(links, "OPPORTUNITY") or lineage.get("opportunity_snapshot_id"),
            decision_packet_family_version=_first(links, "DECISION_PACKET") or lineage.get("packet_family_version"),
            decision_packet_family_revision=_int_or_none(lineage.get("packet_family_revision")),
            evidence_ids=tuple(evidence_ids),
        )

    @staticmethod
    def _summary_rows(
        detail: ResearchPipelineCaseDetail,
        aggregate: dict[str, Any],
        industrial: dict[str, Any],
    ) -> list[dict[str, Any]]:
        constraints = _list(industrial.get("constraints"))
        controllers = _list(industrial.get("controllers"))
        opportunities = _list(industrial.get("opportunities"))
        beneficiaries = _list(_dict(aggregate.get("beneficiaries")).get("top_beneficiaries"))
        return [
            {"label": "Theme", "value": aggregate.get("name") or detail.case.title, "source": "theme_aggregate"},
            {"label": "Pipeline case", "value": detail.case.case_id, "state": detail.case.status, "source": "research_pipeline"},
            {"label": "Coverage state", "value": _coverage_value(industrial), "source": "industrial_intelligence.coverage"},
            {"label": "Primary bottleneck", "value": _display(_first_row(constraints)) or _bottleneck_name(aggregate) or "Unavailable", "source": "constraint_graph"},
            {"label": "Primary controller", "value": _company(_first_row(controllers)) or "Unavailable", "source": "controller_metrics"},
            {"label": "Primary beneficiary", "value": _beneficiary(_first_row(beneficiaries)) or _company(_first_row(opportunities)) or "Unavailable", "source": "theme_beneficiaries"},
            {"label": "Primary opportunity", "value": _company(_first_row(opportunities)) or "Unavailable", "source": "opportunity_metrics"},
        ]

    @staticmethod
    def _bull_rows(
        detail: ResearchPipelineCaseDetail,
        aggregate: dict[str, Any],
        industrial: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for catalyst in _list(_dict(aggregate.get("catalysts")).get("top_catalysts"))[:3]:
            rows.append({"label": _name(catalyst, "catalyst_name"), "source": "theme_catalysts", "evidence_ids": _evidence_ids(catalyst)})
        for controller in _list(industrial.get("controllers"))[:3]:
            rows.append({"label": _company(controller), "source": "controller_metrics", "evidence_ids": _evidence_ids(controller), "types": _list(controller.get("controller_types"))})
        for opportunity in _list(industrial.get("opportunities"))[:3]:
            rows.append({"label": _company(opportunity), "source": "opportunity_metrics", "evidence_ids": _evidence_ids(opportunity), "types": _list(opportunity.get("opportunity_types"))})
        if not rows:
            rows.append({"label": "No validated positive research rows yet", "state": "unavailable", "source": "research_pipeline"})
        return rows

    @staticmethod
    def _bear_rows(
        detail: ResearchPipelineCaseDetail,
        aggregate: dict[str, Any],
        industrial: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for constraint in _list(industrial.get("constraints"))[:4]:
            if str(constraint.get("resolution_state") or "").lower() != "resolved":
                rows.append({
                    "label": _display(constraint),
                    "state": constraint.get("resolution_state") or "unresolved",
                    "source": "constraint_graph",
                    "evidence_ids": _evidence_ids(constraint),
                })
        for gap in _list(industrial.get("research_gaps"))[:5]:
            rows.append({"label": str(gap.get("label") or gap.get("code") or "Research gap"), "state": gap.get("state") or "open", "source": "industrial_intelligence.research_gaps"})
        if detail.progress.percent < 100:
            rows.append({"label": "Incomplete research pipeline sections", "state": f"{detail.progress.percent}% complete", "source": "research_pipeline.progress"})
        return rows or [{"label": "No unresolved negative rows in current projection", "state": "clear", "source": "decision_intelligence"}]

    @staticmethod
    def _evidence_rows(
        detail: ResearchPipelineCaseDetail,
        aggregate: dict[str, Any],
        industrial: dict[str, Any],
        lineage: DecisionIntelligenceLineage,
    ) -> list[dict[str, Any]]:
        completed = [key for key, value in detail.progress.sections.items() if value]
        return [
            {"label": "Evidence references", "value": len(lineage.evidence_ids), "evidence_ids": list(lineage.evidence_ids), "source": "industrial_graph"},
            {"label": "Linked artifacts", "value": len(detail.links), "artifacts": [link.to_dict() for link in detail.links], "source": "research_pipeline_links"},
            {"label": "Completed pipeline sections", "value": detail.progress.percent, "sections": completed, "source": "research_pipeline.progress"},
            {"label": "Graph evidence count", "value": _int_or_none(_dict(industrial.get("graph")).get("evidence_count")) or 0, "source": "industrial_intelligence.graph"},
        ]

    @staticmethod
    def _gap_rows(
        detail: ResearchPipelineCaseDetail,
        aggregate: dict[str, Any],
        industrial: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows = [
            {"label": str(gap.get("label") or gap.get("code") or "Research gap"), "code": gap.get("code"), "state": gap.get("state") or "open", "source": "industrial_intelligence.research_gaps"}
            for gap in _list(industrial.get("research_gaps"))
        ]
        linked_types = {link.linked_type for link in detail.links}
        for section, accepted_types in PROGRESS_LINK_TYPES.items():
            if not (accepted_types & linked_types):
                rows.append({"label": f"Missing {section}", "state": "incomplete", "source": "research_pipeline.progress"})
        return rows or [{"label": "No explicit research gaps in current projection", "state": "none", "source": "decision_intelligence"}]

    @staticmethod
    def _monitoring_rows(
        detail: ResearchPipelineCaseDetail,
        aggregate: dict[str, Any],
        industrial: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in _list(_dict(aggregate.get("bottlenecks")).get("what_to_monitor")):
            rows.append({"label": str(item), "source": "theme_bottlenecks"})
        rows.extend([
            {"label": "Constraint removed or resolution state changes", "source": "constraint_graph"},
            {"label": "Primary controller path changes", "source": "controller_metrics"},
            {"label": "Opportunity reasoning path invalidated", "source": "opportunity_metrics"},
            {"label": "Coverage falls below completed research threshold", "source": "research_pipeline.progress"},
            {"label": "Theme archived in research pipeline", "source": "research_pipeline"},
        ])
        return rows

    @staticmethod
    def _scenario_rows(
        detail: ResearchPipelineCaseDetail,
        aggregate: dict[str, Any],
        industrial: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            {"scenario": "BASE", "condition": "Current evidence, coverage, and lineage remain unchanged", "source": "decision_intelligence"},
            {"scenario": "UPSIDE", "condition": "Open gaps close and resolver/controller evidence strengthens", "source": "decision_intelligence"},
            {"scenario": "DOWNSIDE", "condition": "Constraint remains unresolved or evidence paths break", "source": "decision_intelligence"},
        ]

    @staticmethod
    def _question_rows(
        detail: ResearchPipelineCaseDetail,
        aggregate: dict[str, Any],
        industrial: dict[str, Any],
    ) -> list[dict[str, Any]]:
        questions = []
        if not _list(industrial.get("controllers")):
            questions.append({"question": "Which company has persisted controller evidence?", "source": "controller_metrics"})
        if not _list(industrial.get("opportunities")):
            questions.append({"question": "Which opportunity record is supported by evidence paths?", "source": "opportunity_metrics"})
        for row in DecisionIntelligenceEngine._gap_rows(detail, aggregate, industrial)[:4]:
            questions.append({"question": f"What evidence closes this gap: {row['label']}?", "source": row.get("source")})
        return questions or [{"question": "What new evidence would alter the current research state?", "source": "decision_intelligence"}]


def _links_by_type(detail: ResearchPipelineCaseDetail) -> dict[str, list[str]]:
    links: dict[str, list[str]] = {}
    for link in detail.links:
        links.setdefault(link.linked_type, []).append(link.linked_id)
    return links


def _first(links: dict[str, list[str]], key: str) -> str | None:
    values = links.get(key) or []
    return values[0] if values else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_row(rows: list[Any]) -> dict[str, Any]:
    first = rows[0] if rows else {}
    return first if isinstance(first, dict) else {}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _display(row: dict[str, Any]) -> str:
    return str(row.get("display_name") or row.get("name") or row.get("label") or "").strip()


def _company(row: dict[str, Any]) -> str:
    return str(row.get("company_name") or row.get("company") or row.get("display_name") or row.get("company_key") or "").strip()


def _beneficiary(row: dict[str, Any]) -> str:
    return str(row.get("company_name") or row.get("company") or row.get("ticker") or "").strip()


def _name(row: dict[str, Any], fallback_key: str) -> str:
    return str(row.get("name") or row.get(fallback_key) or row.get("label") or "").strip()


def _bottleneck_name(aggregate: dict[str, Any]) -> str:
    primary = _dict(_dict(aggregate.get("bottlenecks")).get("primary_bottleneck"))
    return str(primary.get("bottleneck_name") or primary.get("name") or "").strip()


def _coverage_value(industrial: dict[str, Any]) -> Any:
    coverage = _dict(industrial.get("coverage"))
    if "overall_coverage" in coverage:
        return coverage.get("overall_coverage")
    if "overall" in coverage:
        return coverage.get("overall")
    return "Unavailable"


def _evidence_ids(row: dict[str, Any]) -> list[str]:
    ids = row.get("evidence_ids")
    if not isinstance(ids, list):
        evidence = row.get("evidence")
        if isinstance(evidence, list):
            ids = [item.get("id") or item.get("evidence_id") for item in evidence if isinstance(item, dict)]
        else:
            ids = []
    return [f"graph_evidence:{item}" if isinstance(item, int) else str(item) for item in ids if str(item).strip()]


def _collect_evidence_ids(industrial: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    graph = _dict(industrial.get("graph"))
    for collection in (
        _list(graph.get("edges")),
        _list(graph.get("dependency_paths")),
        _list(industrial.get("constraints")),
        _list(industrial.get("controllers")),
        _list(industrial.get("opportunities")),
    ):
        for row in collection:
            if isinstance(row, dict):
                ids.extend(_evidence_ids(row))
    return sorted(set(ids))
