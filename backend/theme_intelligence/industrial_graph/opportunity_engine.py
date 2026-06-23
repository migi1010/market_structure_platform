from __future__ import annotations

import uuid

from theme_intelligence.storage.theme_repository import ThemeRepository

from .graph_models import NodeKey, normalize_canonical_key, utc_now
from .graph_repository import IndustrialGraphRepository
from .opportunity_builder import OpportunityBuilder
from .opportunity_models import (
    OpportunityBuild,
    OpportunityIntelligence,
    OpportunitySnapshot,
    opportunity_build_checksum,
)
from .opportunity_validator import OpportunityValidator


class OpportunityEngine:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        theme_repository = repository or ThemeRepository()
        self.repository = IndustrialGraphRepository(theme_repository)
        self.builder = OpportunityBuilder(theme_repository)
        self.validator = OpportunityValidator()

    def build(self, controller_version: str | None = None) -> OpportunityBuild:
        return self.builder.build(controller_version)

    def build_and_activate(
        self, controller_version: str | None = None
    ) -> OpportunitySnapshot:
        build = self.build(controller_version)
        self.validator.validate(build, self.repository)
        staged = self.stage(build)
        return self.activate(staged.opportunity_version)

    def stage(self, build: OpportunityBuild) -> OpportunitySnapshot:
        self.validator.validate(build, self.repository)
        snapshot = OpportunitySnapshot(
            opportunity_version=f"opportunity-{uuid.uuid4().hex}",
            controller_snapshot_id=build.controller_snapshot_id,
            controller_version=build.controller_version,
            graph_snapshot_id=build.graph_snapshot_id,
            graph_build_version=build.graph_build_version,
            algorithm_version=build.algorithm_version,
            status="building",
            checksum=opportunity_build_checksum(build),
            company_count=len(build.opportunities),
            path_count=sum(
                len(row.reasoning_paths) for row in build.opportunities
            ),
            created_at=utc_now(),
        )
        keys = {row.company_key for row in build.opportunities}
        with self.repository.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                node_ids = self.repository.node_ids_for_keys(conn, keys)
                if set(node_ids) != keys:
                    raise ValueError("orphan opportunity company node")
                snapshot_id = self.repository.insert_opportunity_snapshot(
                    conn, snapshot
                )
                company_count = self.repository.insert_opportunity_metrics(
                    conn,
                    snapshot_id,
                    snapshot,
                    build.opportunities,
                    node_ids,
                )
                path_count = self.repository.insert_opportunity_reasoning_paths(
                    conn,
                    snapshot_id,
                    snapshot,
                    build.opportunities,
                    node_ids,
                )
                if (
                    company_count != snapshot.company_count
                    or path_count != snapshot.path_count
                ):
                    raise RuntimeError(
                        "staged opportunity counts do not match snapshot"
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return snapshot

    def activate(self, opportunity_version: str) -> OpportunitySnapshot:
        staged = self.repository.get_opportunity_snapshot(opportunity_version)
        if staged is None:
            raise KeyError(f"Unknown opportunity build: {opportunity_version}")
        stored = OpportunityBuild(
            controller_snapshot_id=staged.controller_snapshot_id,
            controller_version=staged.controller_version,
            graph_snapshot_id=staged.graph_snapshot_id,
            graph_build_version=staged.graph_build_version,
            algorithm_version=staged.algorithm_version,
            opportunities=tuple(
                self.repository.get_opportunity_metrics(opportunity_version)
            ),
        )
        self.validator.validate(stored, self.repository)
        if opportunity_build_checksum(stored) != staged.checksum:
            raise ValueError(
                f"opportunity checksum mismatch: {opportunity_version}"
            )
        with self.repository.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._activate_in_transaction(conn, opportunity_version)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        snapshot = self.repository.get_opportunity_snapshot(opportunity_version)
        if snapshot is None:
            raise KeyError(f"Unknown opportunity build: {opportunity_version}")
        return snapshot

    @staticmethod
    def _activate_in_transaction(conn, opportunity_version: str) -> None:
        row = conn.execute(
            """
            SELECT status FROM opportunity_snapshots
            WHERE opportunity_version=?
            """,
            (opportunity_version,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown opportunity build: {opportunity_version}")
        if str(row[0]) not in {"building", "active"}:
            raise ValueError(
                f"Opportunity build is not activatable: {opportunity_version}"
            )
        conn.execute(
            """
            UPDATE opportunity_snapshots
            SET status='superseded'
            WHERE status='active' AND opportunity_version<>?
            """,
            (opportunity_version,),
        )
        conn.execute(
            """
            UPDATE opportunity_snapshots
            SET status='active', activated_at=?
            WHERE opportunity_version=?
            """,
            (utc_now(), opportunity_version),
        )

    def get_ranked_opportunities(
        self, *, limit: int | None = None
    ) -> list[OpportunityIntelligence]:
        rows = self.repository.get_opportunity_metrics()
        return rows if limit is None else rows[: max(0, limit)]

    def get_opportunity_intelligence(
        self, company: NodeKey
    ) -> OpportunityIntelligence | None:
        key = (
            company[0],
            normalize_canonical_key(company[1], node_type=company[0]),
        )
        return next(
            (
                row
                for row in self.get_ranked_opportunities()
                if row.company_key == key
            ),
            None,
        )
