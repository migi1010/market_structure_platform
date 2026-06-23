from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from typing import Iterator

from theme_intelligence.storage.theme_repository import ThemeRepository

from .graph_models import content_hash, utc_now
from .theme_scout_models import (
    ScoutEvidence,
    ThemeCandidateInfluence,
    ThemeScoutBuild,
    ThemeScoutCandidate,
    ThemeScoutMetrics,
    ThemeScoutPath,
    ThemeScoutReadiness,
    ThemeScoutSignalCluster,
    ThemeScoutSnapshot,
    candidate_checksum,
)
from .theme_scout_isolation import (
    connection_downstream_fingerprint,
    verify_connection_isolation,
)


class ThemeScoutRepository:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = repository or ThemeRepository()

    def initialize(self) -> None:
        self.repository.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.initialize()
        conn = self.repository._connect()
        try:
            yield conn
        finally:
            conn.close()

    def stage(self, build: ThemeScoutBuild) -> ThemeScoutSnapshot:
        now = utc_now()
        snapshot = ThemeScoutSnapshot(
            scout_version=f"scout-{uuid.uuid4().hex}",
            algorithm_version=build.algorithm_version,
            provider_name=build.provider_name,
            provider_model=build.provider_model,
            prompt_version=build.prompt_version,
            source_watermark=build.source_watermark,
            evidence_bundle_checksum=build.evidence_bundle_checksum,
            proposal_checksum=build.proposal_checksum,
            checksum=build.checksum,
            candidate_count=len(build.candidates),
            status="validated",
            created_at=now,
        )
        with self.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    """
                    INSERT INTO theme_scout_snapshots (
                        scout_version, algorithm_version, prompt_version,
                        provider_name, provider_model, weights_json,
                        source_watermark, evidence_bundle_checksum,
                        proposal_checksum, checksum, candidate_count, status,
                        activated_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.scout_version, snapshot.algorithm_version,
                        snapshot.prompt_version, snapshot.provider_name,
                        snapshot.provider_model,
                        json.dumps(dict(build.weights), sort_keys=True),
                        snapshot.source_watermark,
                        snapshot.evidence_bundle_checksum,
                        snapshot.proposal_checksum, snapshot.checksum,
                        snapshot.candidate_count, snapshot.status, None, now,
                    ),
                )
                snapshot_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
                for candidate in build.candidates:
                    self._insert_candidate(conn, snapshot_id, candidate, now)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return snapshot

    @staticmethod
    def _insert_candidate(
        conn: sqlite3.Connection,
        snapshot_id: int,
        candidate: ThemeScoutCandidate,
        now: str,
    ) -> None:
        metrics = candidate.metrics
        conn.execute(
            """
            INSERT INTO theme_candidates (
                snapshot_id, candidate_key, name, description, status,
                status_actor, status_reason, status_changed_at,
                confidence_score, novelty_score, velocity_score, breadth_score,
                capital_score, bottleneck_score, serendipity_score, theme_score,
                coverage, raw_values_json, normalized_values_json,
                applied_weights_json, readiness_json, signal_count,
                evidence_count, source_count, source_types_json,
                generated_summary, rank, checksum, created_at
                , updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id, candidate.candidate_key, candidate.name,
                candidate.description, candidate.status, candidate.status_actor,
                candidate.status_reason, candidate.status_changed_at or now,
                metrics.confidence, metrics.novelty, metrics.velocity,
                metrics.breadth, metrics.capital, metrics.bottleneck,
                metrics.serendipity, metrics.theme_score, metrics.coverage,
                json.dumps(metrics.raw_values, sort_keys=True),
                json.dumps(metrics.normalized_values, sort_keys=True),
                json.dumps(metrics.applied_weights, sort_keys=True),
                json.dumps(candidate.readiness.to_dict(), sort_keys=True),
                candidate.signal_count, candidate.evidence_count,
                candidate.source_count,
                json.dumps(sorted({row.source_type for row in candidate.evidence})),
                candidate.generated_summary, candidate.rank,
                candidate_checksum(candidate), now, now,
            ),
        )
        candidate_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        for index, row in enumerate(candidate.evidence, 1):
            conn.execute(
                """
                INSERT INTO theme_candidate_evidence (
                    candidate_id, evidence_order, evidence_key, source_table,
                    source_record_id, source_type, source_timestamp,
                    source_identifier, citation, content_hash, domain_type,
                    cluster_key, source_value_json, availability_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id, index, row.evidence_id, row.source_table,
                    row.source_record_id, row.source_type, row.source_timestamp,
                    row.source_identifier, row.citation, row.content_hash,
                    row.domain_type, row.cluster_key,
                    json.dumps(row.source_value, sort_keys=True),
                    row.availability_state, now,
                ),
            )
        combined_paths = [
            ThemeScoutPath(
                path_type="SIGNAL_CLUSTER",
                label=row.label,
                evidence_ids=row.evidence_ids,
                steps=({"cluster_key": row.cluster_key},),
            )
            for row in candidate.signal_clusters
        ] + list(candidate.paths)
        for index, row in enumerate(combined_paths, 1):
            payload = row.to_dict()
            conn.execute(
                """
                INSERT INTO theme_candidate_paths (
                    candidate_id, path_order, path_type, label,
                    path_payload_json, evidence_keys_json, checksum, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id, index, row.path_type, row.label,
                    json.dumps(payload, sort_keys=True),
                    json.dumps(row.evidence_ids), content_hash(payload), now,
                ),
            )
        for index, row in enumerate(candidate.influence_map, 1):
            payload = row.to_dict()
            conn.execute(
                """
                INSERT INTO theme_candidate_influence_maps (
                    candidate_id, influence_order, target_type, target_label,
                    hypothesis_state, evidence_keys_json,
                    source_cluster_keys_json, checksum, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id, index, row.target_type, row.target_label,
                    row.hypothesis_state, json.dumps(row.evidence_ids),
                    json.dumps(row.cluster_keys), content_hash(payload), now,
                ),
            )

    def activate(self, scout_version: str) -> ThemeScoutSnapshot:
        with self.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT status FROM theme_scout_snapshots WHERE scout_version=?",
                    (scout_version,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Unknown Scout snapshot: {scout_version}")
                if str(row["status"]) not in {"validated", "active"}:
                    raise ValueError("Scout snapshot is not activatable")
                conn.execute(
                    "UPDATE theme_scout_snapshots SET status='superseded' WHERE status='active' AND scout_version<>?",
                    (scout_version,),
                )
                conn.execute(
                    "UPDATE theme_scout_snapshots SET status='active', activated_at=? WHERE scout_version=?",
                    (utc_now(), scout_version),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        snapshot = self.get_snapshot(scout_version)
        if snapshot is None:
            raise KeyError(f"Unknown Scout snapshot: {scout_version}")
        return snapshot

    def activate_guarded(self, scout_version: str) -> ThemeScoutSnapshot:
        with self.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                before = connection_downstream_fingerprint(conn)
                row = conn.execute(
                    "SELECT status FROM theme_scout_snapshots WHERE scout_version=?",
                    (scout_version,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Unknown Scout snapshot: {scout_version}")
                if str(row["status"]) not in {"validated", "active"}:
                    raise ValueError("Scout snapshot is not activatable")
                conn.execute(
                    "UPDATE theme_scout_snapshots SET status='superseded' WHERE status='active' AND scout_version<>?",
                    (scout_version,),
                )
                conn.execute(
                    "UPDATE theme_scout_snapshots SET status='active', activated_at=? WHERE scout_version=?",
                    (utc_now(), scout_version),
                )
                verify_connection_isolation(conn, before)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        snapshot = self.get_snapshot(scout_version)
        if snapshot is None:
            raise KeyError(f"Unknown Scout snapshot: {scout_version}")
        return snapshot

    def rollback(self, scout_version: str) -> ThemeScoutSnapshot:
        with self.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                current = conn.execute(
                    "SELECT id FROM theme_scout_snapshots WHERE scout_version=? AND status='active'",
                    (scout_version,),
                ).fetchone()
                if current is None:
                    raise ValueError("rollback target must be active")
                previous = conn.execute(
                    """
                    SELECT id, scout_version FROM theme_scout_snapshots
                    WHERE id < ? AND status='superseded'
                    ORDER BY id DESC LIMIT 1
                    """,
                    (int(current["id"]),),
                ).fetchone()
                if previous is None:
                    raise ValueError("no previous Scout snapshot")
                conn.execute(
                    "UPDATE theme_scout_snapshots SET status='superseded' WHERE id=?",
                    (int(current["id"]),),
                )
                conn.execute(
                    "UPDATE theme_scout_snapshots SET status='active', activated_at=? WHERE id=?",
                    (utc_now(), int(previous["id"])),
                )
                conn.commit()
                previous_version = str(previous["scout_version"])
            except Exception:
                conn.rollback()
                raise
        snapshot = self.get_snapshot(previous_version)
        if snapshot is None:
            raise RuntimeError("rollback did not restore a Scout snapshot")
        return snapshot

    def get_snapshot(self, scout_version: str) -> ThemeScoutSnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM theme_scout_snapshots WHERE scout_version=?",
                (scout_version,),
            ).fetchone()
        return self._snapshot(row)

    def get_active_snapshot(self) -> ThemeScoutSnapshot | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM theme_scout_snapshots WHERE status='active' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return self._snapshot(row)

    @staticmethod
    def _snapshot(row: sqlite3.Row | None) -> ThemeScoutSnapshot | None:
        if row is None:
            return None
        return ThemeScoutSnapshot(
            id=int(row["id"]),
            scout_version=str(row["scout_version"]),
            algorithm_version=str(row["algorithm_version"]),
            provider_name=str(row["provider_name"]),
            provider_model=str(row["provider_model"]),
            prompt_version=str(row["prompt_version"]),
            source_watermark=str(row["source_watermark"]),
            evidence_bundle_checksum=str(row["evidence_bundle_checksum"]),
            proposal_checksum=str(row["proposal_checksum"]),
            checksum=str(row["checksum"]),
            candidate_count=int(row["candidate_count"]),
            status=str(row["status"]),
            activated_at=row["activated_at"],
            created_at=str(row["created_at"]),
        )

    def list_candidates(self, scout_version: str | None = None) -> list[ThemeScoutCandidate]:
        snapshot = self.get_snapshot(scout_version) if scout_version else self.get_active_snapshot()
        if snapshot is None:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM theme_candidates WHERE snapshot_id=? ORDER BY rank, candidate_key",
                (snapshot.id,),
            ).fetchall()
            return [self._candidate(conn, row) for row in rows]

    def get_candidate(
        self, candidate_key: str, scout_version: str | None = None
    ) -> ThemeScoutCandidate | None:
        return next(
            (row for row in self.list_candidates(scout_version) if row.candidate_key == candidate_key),
            None,
        )

    @staticmethod
    def _candidate(conn: sqlite3.Connection, row: sqlite3.Row) -> ThemeScoutCandidate:
        candidate_id = int(row["id"])
        evidence = tuple(
            ScoutEvidence(
                evidence_id=str(item["evidence_key"]),
                source_table=str(item["source_table"]),
                source_record_id=str(item["source_record_id"]),
                source_type=str(item["source_type"]),
                source_timestamp=str(item["source_timestamp"]),
                source_identifier=str(item["source_identifier"]),
                citation=str(item["citation"]),
                domain_type=str(item["domain_type"]),
                cluster_key=str(item["cluster_key"]),
                source_value=json.loads(item["source_value_json"]),
                content_hash=str(item["content_hash"]),
                availability_state=str(item["availability_state"]),
            )
            for item in conn.execute(
                "SELECT * FROM theme_candidate_evidence WHERE candidate_id=? ORDER BY evidence_order",
                (candidate_id,),
            ).fetchall()
        )
        path_rows = conn.execute(
            "SELECT * FROM theme_candidate_paths WHERE candidate_id=? ORDER BY path_order",
            (candidate_id,),
        ).fetchall()
        clusters: list[ThemeScoutSignalCluster] = []
        paths: list[ThemeScoutPath] = []
        for item in path_rows:
            payload = json.loads(item["path_payload_json"])
            path = ThemeScoutPath(
                path_type=str(item["path_type"]),
                label=str(item["label"]),
                evidence_ids=tuple(json.loads(item["evidence_keys_json"])),
                steps=tuple(payload.get("steps", ())),
            )
            if path.path_type == "SIGNAL_CLUSTER":
                clusters.append(ThemeScoutSignalCluster(
                    cluster_key=str(path.steps[0].get("cluster_key", path.label)),
                    label=path.label,
                    evidence_ids=path.evidence_ids,
                ))
            else:
                paths.append(path)
        influence = tuple(
            ThemeCandidateInfluence(
                target_type=str(item["target_type"]),
                target_label=str(item["target_label"]),
                hypothesis_state=str(item["hypothesis_state"]),
                evidence_ids=tuple(json.loads(item["evidence_keys_json"])),
                cluster_keys=tuple(json.loads(item["source_cluster_keys_json"])),
            )
            for item in conn.execute(
                "SELECT * FROM theme_candidate_influence_maps WHERE candidate_id=? ORDER BY influence_order",
                (candidate_id,),
            ).fetchall()
        )
        readiness = ThemeScoutReadiness(**json.loads(row["readiness_json"]))
        metrics = ThemeScoutMetrics(
            confidence=float(row["confidence_score"]),
            novelty=float(row["novelty_score"]),
            velocity=float(row["velocity_score"]),
            breadth=float(row["breadth_score"]),
            capital=float(row["capital_score"]),
            bottleneck=float(row["bottleneck_score"]),
            serendipity=float(row["serendipity_score"]),
            theme_score=float(row["theme_score"]),
            coverage=float(row["coverage"]),
            raw_values=json.loads(row["raw_values_json"]),
            normalized_values=json.loads(row["normalized_values_json"]),
            applied_weights=json.loads(row["applied_weights_json"]),
        )
        return ThemeScoutCandidate(
            id=candidate_id,
            candidate_key=str(row["candidate_key"]),
            name=str(row["name"]),
            description=str(row["description"]),
            status=str(row["status"]),
            metrics=metrics,
            readiness=readiness,
            evidence=evidence,
            signal_clusters=tuple(clusters),
            paths=tuple(paths),
            influence_map=influence,
            rank=int(row["rank"]),
            generated_summary=str(row["generated_summary"]),
            status_actor=str(row["status_actor"]),
            status_reason=str(row["status_reason"]),
            status_changed_at=str(row["status_changed_at"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
