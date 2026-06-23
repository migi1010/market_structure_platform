from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_manifest import (
    ThemeScoutEvidenceManifest,
    derive_evidence_domain,
    export_active_graph_evidence_manifest,
)
from theme_intelligence.storage.theme_repository import ThemeRepository


def _seed_graph(repository: ThemeRepository) -> None:
    repository.initialize()
    with repository._connect() as conn:
        conn.execute(
            """INSERT INTO graph_nodes
               (node_type, canonical_key, display_name, aliases_json,
                external_ids_json, status, valid_from, valid_to, created_at, updated_at)
               VALUES ('Theme','theme:test','Test Theme','[]','{}','active','now',NULL,'now','now')"""
        )
        theme_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """INSERT INTO graph_nodes
               (node_type, canonical_key, display_name, aliases_json,
                external_ids_json, status, valid_from, valid_to, created_at, updated_at)
               VALUES ('Constraint','constraint:test','Test Constraint','[]','{}','active','now',NULL,'now','now')"""
        )
        constraint_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """INSERT INTO graph_evidence
               (source_type, source_record_id, content_hash, citation,
                observed_date, review_status, created_at)
               VALUES ('research','record-1','hash-1','Persisted citation',
                       '2026-06-10T00:00:00+00:00','approved','now')"""
        )
        evidence_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """INSERT INTO graph_edges
               (source_node_id, relationship_type, target_node_id,
                confidence_score, dependency_strength, status, valid_from,
                valid_to, build_version, created_at, updated_at)
               VALUES (?, 'THEME_LIMITED_BY_CONSTRAINT', ?, 1, 1, 'active',
                       'now', NULL, 'industrial-active', 'now', 'now')""",
            (theme_id, constraint_id),
        )
        edge_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO graph_edge_evidence (edge_id, evidence_id) VALUES (?, ?)",
            (edge_id, evidence_id),
        )
        conn.execute(
            """INSERT INTO graph_snapshots
               (build_version,status,source_watermark,node_count,edge_count,
                checksum,activated_at,created_at)
               VALUES ('industrial-active','active','watermark',2,1,
                       'graph-checksum','now','2026-06-10T00:00:00+00:00')"""
        )
        conn.commit()


def test_domain_derivation_uses_endpoint_precedence() -> None:
    assert derive_evidence_domain({"Theme", "Company", "Constraint"}) == "Constraint"
    assert derive_evidence_domain({"Theme", "Technology"}) == "Technology"
    assert derive_evidence_domain({"Theme"}) == "Other"


def test_manifest_is_scoped_to_active_graph(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "manifest.sqlite3")
    _seed_graph(repository)
    manifest = export_active_graph_evidence_manifest(repository)
    assert isinstance(manifest, ThemeScoutEvidenceManifest)
    assert manifest.graph_build_version == "industrial-active"
    assert len(manifest.evidence) == 1
    assert manifest.evidence[0].domain_type == "Constraint"
    assert manifest.evidence[0].evidence_id.startswith("graph_evidence:")
    assert manifest.evidence_bundle_checksum == manifest.recalculate_checksum()

