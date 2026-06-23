from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.storage.theme_repository import ThemeRepository
from theme_intelligence.theme_registry.theme_registry_repository import ThemeRegistryRepository


def _seed_graph_theme(repository: ThemeRepository, theme_id: str, name: str, *, status: str = "active") -> None:
    repository.initialize()
    with repository._connect() as conn:
        conn.execute(
            """
            INSERT INTO graph_nodes (
                node_type, canonical_key, display_name, aliases_json, external_ids_json,
                status, valid_from, valid_to, created_at, updated_at
            )
            VALUES ('Theme', ?, ?, ?, '{}', ?, '2026-06-20T00:00:00+00:00', NULL,
                    '2026-06-20T00:00:00+00:00', '2026-06-20T00:00:00+00:00')
            """,
            (theme_id, name, json.dumps((name,), ensure_ascii=False), status),
        )
        conn.execute(
            """
            INSERT INTO graph_snapshots (
                build_version, status, source_watermark, node_count, edge_count,
                checksum, activated_at, created_at
            )
            VALUES ('registry-test-graph', 'active', 'seed', 1, 0, 'checksum',
                    '2026-06-20T00:00:00+00:00', '2026-06-20T00:00:00+00:00')
            ON CONFLICT(build_version) DO NOTHING
            """
        )
        conn.commit()


def _seed_scout_candidate(repository: ThemeRepository, candidate_key: str, name: str, rank: int = 1) -> None:
    repository.initialize()
    with repository._connect() as conn:
        conn.execute(
            """
            INSERT INTO theme_scout_snapshots (
                scout_version, algorithm_version, prompt_version, provider_name,
                provider_model, weights_json, source_watermark, evidence_bundle_checksum,
                proposal_checksum, checksum, candidate_count, status, activated_at, created_at
            )
            VALUES ('registry-test-scout', 'v1', 'manual-v1', 'manual', 'offline',
                    '{}', 'seed', 'evidence-checksum', 'proposal-checksum', 'checksum',
                    1, 'active', '2026-06-20T01:00:00+00:00', '2026-06-20T01:00:00+00:00')
            ON CONFLICT(scout_version) DO NOTHING
            """
        )
        snapshot_id = int(conn.execute("SELECT id FROM theme_scout_snapshots WHERE scout_version='registry-test-scout'").fetchone()[0])
        conn.execute(
            """
            INSERT INTO theme_candidates (
                snapshot_id, candidate_key, name, description, status, status_actor,
                status_reason, status_changed_at, confidence_score, novelty_score,
                velocity_score, breadth_score, capital_score, bottleneck_score,
                serendipity_score, theme_score, coverage, raw_values_json,
                normalized_values_json, applied_weights_json, readiness_json,
                signal_count, evidence_count, source_count, source_types_json,
                generated_summary, rank, checksum, created_at, updated_at
            )
            VALUES (?, ?, ?, 'candidate', 'DISCOVERED', 'manual', 'seed',
                    '2026-06-20T01:00:00+00:00', 50, 0, 50, 50, 50, 80, 50,
                    60, 75, '{}', '{}', '{}', '{}', 2, 3, 1, '[]', '',
                    ?, 'candidate-checksum', '2026-06-20T01:00:00+00:00',
                    '2026-06-20T01:00:00+00:00')
            """,
            (snapshot_id, candidate_key, name, rank),
        )
        conn.commit()


def test_repository_reads_sources_without_creating_registry_tables(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "registry.sqlite3")
    _seed_graph_theme(repository, "hbm", "HBM")
    _seed_scout_candidate(repository, "candidate:ai-power-grid", "AI Power Grid")

    registry = ThemeRegistryRepository(repository)
    assert [row.theme_id for row in registry.graph_themes()] == ["hbm"]
    assert [row.theme_id for row in registry.scout_themes()] == ["ai_power_grid"]

    with repository._connect() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "theme_registry" not in tables
    assert "theme_registry_entries" not in tables


def test_repository_reads_approved_pipeline_theme_counts(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "registry.sqlite3")
    repository.initialize()
    with repository._connect() as conn:
        conn.execute(
            """
            INSERT INTO research_pipeline_cases (
                case_id, source_type, source_id, theme_id, title, status,
                created_at, updated_at, activated_at, archived_at, lineage_checksum
            )
            VALUES ('case-1', 'SCOUT_CANDIDATE', 'candidate:optical-interconnect',
                    'optical_interconnect', 'Optical Interconnect', 'APPROVED_RESEARCH',
                    '2026-06-20T02:00:00+00:00', '2026-06-20T02:00:00+00:00',
                    NULL, NULL, 'checksum')
            """
        )
        conn.commit()

    rows = ThemeRegistryRepository(repository).pipeline_themes()
    assert [(row.theme_id, row.research_case_count, row.status) for row in rows] == [
        ("optical_interconnect", 1, "ACTIVE")
    ]
