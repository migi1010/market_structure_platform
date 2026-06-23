from __future__ import annotations

import math
from collections.abc import Iterable

from .opportunity_models import (
    OPPORTUNITY_WEIGHTS,
    OpportunityBuild,
    opportunity_build_checksum,
)
from .graph_repository import IndustrialGraphRepository


class OpportunityValidationError(ValueError):
    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = tuple(sorted(set(errors)))
        super().__init__("; ".join(self.errors))


class OpportunityValidator:
    def validate(
        self,
        build: OpportunityBuild,
        repository: IndustrialGraphRepository,
    ) -> None:
        errors: list[str] = []
        controller = repository.get_controller_snapshot(build.controller_version)
        graph = repository.get_snapshot(build.graph_build_version)
        if (
            build.controller_snapshot_id <= 0
            or controller is None
            or controller.id != build.controller_snapshot_id
        ):
            errors.append("missing controller snapshot reference")
        if (
            build.graph_snapshot_id <= 0
            or graph is None
            or graph.id != build.graph_snapshot_id
        ):
            errors.append("missing graph snapshot reference")
        if (
            controller is not None
            and (
                controller.graph_snapshot_id != build.graph_snapshot_id
                or controller.graph_build_version != build.graph_build_version
            )
        ):
            errors.append("snapshot reference mismatch")
        companies = [row.company_key for row in build.opportunities]
        ranks = [row.rank for row in build.opportunities]
        if len(companies) != len(set(companies)):
            errors.append("duplicate opportunity record")
        if len(ranks) != len(set(ranks)):
            errors.append("duplicate opportunity rank")
        valid_evidence = (
            repository.get_evidence_ids_for_build(build.graph_build_version)
            if graph is not None
            else set()
        )
        controllers = {
            row.company_key: row
            for row in repository.get_controller_metrics(build.controller_version)
        }
        for row in build.opportunities:
            if not row.evidence_ids:
                errors.append(f"missing evidence: {row.company_key}")
            if not set(row.evidence_ids) <= valid_evidence:
                errors.append(f"orphan evidence: {row.company_key}")
            source_controller = controllers.get(row.company_key)
            if source_controller is None:
                errors.append(f"orphan opportunity: {row.company_key}")
            else:
                allowed_paths = set(source_controller.reasoning_paths)
                for path in source_controller.reasoning_paths:
                    theme_indexes = [
                        index for index, node in enumerate(path)
                        if node[0] == "Theme"
                    ]
                    if theme_indexes:
                        allowed_paths.add(
                            tuple(reversed(path[: theme_indexes[-1] + 1]))
                        )
                if any(path not in allowed_paths for path in row.reasoning_paths):
                    errors.append(f"invalid reasoning path: {row.company_key}")
                if not set(row.evidence_ids) <= set(source_controller.evidence_ids):
                    errors.append(f"invalid evidence reference: {row.company_key}")
            if dict(row.configured_weights) != OPPORTUNITY_WEIGHTS:
                errors.append(f"invalid configured weights: {row.company_key}")
            if not math.isclose(
                sum(row.applied_weights.values()), 1.0, abs_tol=1e-6
            ):
                errors.append(f"invalid applied weights: {row.company_key}")
            market = (row.market_attention, row.valuation, row.bubble_risk)
            for component in market:
                if component.availability_state == "unavailable":
                    if (
                        component.raw_value is not None
                        or component.normalized_value is not None
                        or component.applied_weight != 0
                    ):
                        errors.append(
                            f"unavailable component treated as favorable: {row.company_key}"
                        )
                else:
                    if not component.source_records:
                        errors.append(
                            f"missing market source: {row.company_key}"
                        )
            available_weight = sum(
                weight
                for name, weight in OPPORTUNITY_WEIGHTS.items()
                if name not in {
                    component.name
                    for component in market
                    if component.availability_state == "unavailable"
                }
            )
            if not math.isclose(
                row.coverage_component, available_weight * 100.0, abs_tol=1e-6
            ):
                errors.append(f"invalid coverage component: {row.company_key}")
        checksum = opportunity_build_checksum(build)
        if checksum != opportunity_build_checksum(build):
            errors.append("non-deterministic output")
        if errors:
            raise OpportunityValidationError(errors)
