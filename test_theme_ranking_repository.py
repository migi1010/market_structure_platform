from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.storage.theme_repository import ThemeRepository
from theme_intelligence.theme_ranking.theme_ranking_repository import (
    ThemeRankingRepository,
)


def _seed_graph_theme(repository: ThemeRepository, theme_id: str, name: str) -> None:
    repository.initialize()
    with repository._connect() as conn:
        conn.execute(
            """
            INSERT INTO graph_nodes (
                node_type, canonical_key, display_name, aliases_json, external_ids_json,
                status, valid_from, valid_to, created_at, updated_at
            )
            VALUES ('Theme', ?, ?, ?, '{}', 'active',
                    '2026-06-20T00:00:00+00:00', NULL,
                    '2026-06-20T00:00:00+00:00', '2026-06-20T00:00:00+00:00')
            """,
            (theme_id, name, json.dumps((name,))),
        )
        conn.execute(
            """
            INSERT INTO graph_snapshots (
                build_version, status, source_watermark, node_count, edge_count,
                checksum, activated_at, created_at
            )
            VALUES ('ranking-graph', 'active', 'seed', 1, 0, 'checksum',
                    '2026-06-20T00:00:00+00:00', '2026-06-20T00:00:00+00:00')
            ON CONFLICT(build_version) DO NOTHING
            """
        )
        conn.commit()


def _seed_scout_candidate(repository: ThemeRepository, candidate_key: str, name: str) -> None:
    repository.initialize()
    with repository._connect() as conn:
        conn.execute(
            """
            INSERT INTO theme_scout_snapshots (
                scout_version, algorithm_version, prompt_version, provider_name,
                provider_model, weights_json, source_watermark, evidence_bundle_checksum,
                proposal_checksum, checksum, candidate_count, status, activated_at, created_at
            )
            VALUES ('ranking-scout', 'v1', 'manual-v1', 'manual', 'offline',
                    '{}', 'seed', 'evidence-checksum', 'proposal-checksum',
                    'checksum', 1, 'active', '2026-06-20T01:00:00+00:00',
                    '2026-06-20T01:00:00+00:00')
            ON CONFLICT(scout_version) DO NOTHING
            """
        )
        snapshot_id = int(conn.execute("SELECT id FROM theme_scout_snapshots WHERE scout_version='ranking-scout'").fetchone()[0])
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
                    '2026-06-20T01:00:00+00:00', 85, 0, 80, 60, 50, 90,
                    50, 82, 75, '{}', '{}', '{}', '{}', 4, 5, 2, '[]',
                    '', 1, 'candidate-checksum', '2026-06-20T01:00:00+00:00',
                    '2026-06-20T01:00:00+00:00')
            """,
            (snapshot_id, candidate_key, name),
        )
        conn.commit()


def test_repository_collects_existing_theme_sources_without_creating_tables(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "ranking.sqlite3")
    _seed_graph_theme(repository, "hbm", "HBM")
    _seed_scout_candidate(repository, "candidate:ai-infrastructure-watch", "AI Infrastructure Watch")

    source_rows = ThemeRankingRepository(repository).load_theme_sources()

    assert [row.theme_id for row in source_rows] == ["ai_infrastructure_watch", "hbm"]
    scout = next(row for row in source_rows if row.theme_id == "ai_infrastructure_watch")
    assert scout.has_scout_signal is True
    assert scout.scout_evidence_count == 5
    graph = next(row for row in source_rows if row.theme_id == "hbm")
    assert graph.has_active_graph is True

    with repository._connect() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "theme_ranking" not in tables
    assert "theme_ranking_entries" not in tables
