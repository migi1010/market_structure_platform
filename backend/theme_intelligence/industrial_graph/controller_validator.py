from __future__ import annotations

from collections.abc import Iterable

from .controller_builder import ControllerBuilder
from .controller_models import (
    EXCLUDED_CONTROLLER_RELATIONSHIPS,
    ControllerBuild,
    controller_build_checksum,
)
from .graph_repository import IndustrialGraphRepository


class ControllerValidationError(ValueError):
    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = tuple(sorted(set(errors)))
        super().__init__("; ".join(self.errors))


class ControllerValidator:
    def validate(
        self, build: ControllerBuild, repository: IndustrialGraphRepository
    ) -> None:
        errors: list[str] = []
        snapshot = repository.get_snapshot(build.graph_build_version) if build.graph_build_version else None
        if build.graph_snapshot_id <= 0 or snapshot is None:
            errors.append("missing snapshot reference")
        elif snapshot.id != build.graph_snapshot_id:
            errors.append("graph snapshot reference mismatch")
        companies = [row.company_key for row in build.controllers]
        if len(companies) != len(set(companies)):
            errors.append("duplicate controller record")
        metric_keys = [row.identity_key for row in build.metrics]
        if len(metric_keys) != len(set(metric_keys)):
            errors.append("duplicate controller metric")
        controller_companies = set(companies)
        for metric in build.metrics:
            if metric.company_key not in controller_companies:
                errors.append(f"orphan metric: {metric.identity_key}")
        valid_evidence = (
            repository.get_evidence_ids_for_build(build.graph_build_version)
            if snapshot is not None else set()
        )
        projection = None
        if snapshot is not None:
            projection = ControllerBuilder(repository.repository).build_projection(build.graph_build_version)
        for row in build.controllers:
            if not row.evidence_ids:
                errors.append(f"missing evidence: {row.company_key}")
            if not set(row.evidence_ids) <= valid_evidence:
                errors.append(f"orphan evidence: {row.company_key}")
            for path in row.reasoning_paths:
                if not path or path[0] != row.company_key:
                    errors.append(f"invalid reasoning path: {row.company_key}")
                    continue
                if projection is None:
                    continue
                for source, target in zip(path, path[1:]):
                    if not projection.has_edge(source, target):
                        errors.append(f"unreproducible reasoning path: {row.company_key}")
                        break
                    if EXCLUDED_CONTROLLER_RELATIONSHIPS & set(
                        projection[source][target]["relationship_types"]
                    ):
                        errors.append(f"excluded relationship in reasoning path: {row.company_key}")
        checksum = controller_build_checksum(build)
        if checksum != controller_build_checksum(build):
            errors.append("non-deterministic checksum")
        if errors:
            raise ControllerValidationError(errors)
