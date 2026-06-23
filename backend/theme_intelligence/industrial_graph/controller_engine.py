from __future__ import annotations

import uuid

from theme_intelligence.storage.theme_repository import ThemeRepository

from .controller_builder import ControllerBuilder
from .controller_models import (
    ControllerBuild,
    ControllerIntelligence,
    ControllerSnapshot,
    controller_build_checksum,
)
from .controller_validator import ControllerValidator
from .graph_models import NodeKey, normalize_canonical_key, utc_now
from .graph_repository import IndustrialGraphRepository


class ControllerEngine:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        theme_repository = repository or ThemeRepository()
        self.repository = IndustrialGraphRepository(theme_repository)
        self.builder = ControllerBuilder(theme_repository)
        self.validator = ControllerValidator()

    def build(self, graph_build_version: str | None = None) -> ControllerBuild:
        return self.builder.build(graph_build_version)

    def build_and_activate(
        self, graph_build_version: str | None = None
    ) -> ControllerSnapshot:
        build = self.build(graph_build_version)
        self.validator.validate(build, self.repository)
        staged = self.stage(build)
        return self.activate(staged.controller_version)

    def stage(self, build: ControllerBuild) -> ControllerSnapshot:
        self.validator.validate(build, self.repository)
        created_at = utc_now()
        snapshot = ControllerSnapshot(
            controller_version=f"controller-{uuid.uuid4().hex}",
            graph_snapshot_id=build.graph_snapshot_id,
            graph_build_version=build.graph_build_version,
            algorithm_version=build.algorithm_version,
            status="building",
            checksum=controller_build_checksum(build),
            company_count=len(build.controllers),
            metric_count=len(build.metrics),
            created_at=created_at,
        )
        keys = {row.company_key for row in build.controllers}
        with self.repository.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                node_ids = self.repository.node_ids_for_keys(conn, keys)
                if set(node_ids) != keys:
                    raise ValueError("orphan controller company node")
                snapshot_id = self.repository.insert_controller_snapshot(conn, snapshot)
                metric_count = self.repository.insert_graph_metrics(
                    conn, snapshot_id, snapshot.controller_version,
                    build.graph_snapshot_id, build.algorithm_version,
                    build.metrics, node_ids,
                )
                company_count = self.repository.insert_controller_metrics(
                    conn, snapshot_id, snapshot.controller_version,
                    build.graph_snapshot_id, build.algorithm_version,
                    build.controllers, node_ids,
                )
                if metric_count != snapshot.metric_count or company_count != snapshot.company_count:
                    raise RuntimeError("staged controller counts do not match snapshot")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return snapshot

    def activate(self, controller_version: str) -> ControllerSnapshot:
        staged = self.repository.get_controller_snapshot(controller_version)
        if staged is None:
            raise KeyError(f"Unknown controller build: {controller_version}")
        stored_build = ControllerBuild(
            graph_snapshot_id=staged.graph_snapshot_id,
            graph_build_version=staged.graph_build_version,
            algorithm_version=staged.algorithm_version,
            metrics=tuple(self.repository.get_graph_metrics(controller_version)),
            controllers=tuple(self.repository.get_controller_metrics(controller_version)),
        )
        if controller_build_checksum(stored_build) != staged.checksum:
            raise ValueError(f"controller checksum mismatch: {controller_version}")
        with self.repository.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._activate_in_transaction(conn, controller_version)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        snapshot = self.repository.get_controller_snapshot(controller_version)
        if snapshot is None:
            raise KeyError(f"Unknown controller build: {controller_version}")
        return snapshot

    @staticmethod
    def _activate_in_transaction(conn, controller_version: str) -> None:
        row = conn.execute(
            "SELECT status FROM controller_snapshots WHERE controller_version=?",
            (controller_version,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown controller build: {controller_version}")
        if str(row[0]) not in {"building", "active"}:
            raise ValueError(f"Controller build is not activatable: {controller_version}")
        activated_at = utc_now()
        conn.execute(
            "UPDATE controller_snapshots SET status='superseded' WHERE status='active' AND controller_version<>?",
            (controller_version,),
        )
        conn.execute(
            """
            UPDATE controller_snapshots
            SET status='active', activated_at=?
            WHERE controller_version=?
            """,
            (activated_at, controller_version),
        )

    def get_ranked_controllers(
        self, *, limit: int | None = None
    ) -> list[ControllerIntelligence]:
        rows = self.repository.get_controller_metrics()
        return rows if limit is None else rows[:max(0, limit)]

    def get_controller_intelligence(
        self, company: NodeKey
    ) -> ControllerIntelligence | None:
        key = (company[0], normalize_canonical_key(company[1], node_type=company[0]))
        return next((row for row in self.get_ranked_controllers() if row.company_key == key), None)
