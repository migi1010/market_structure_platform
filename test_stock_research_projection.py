from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import main
from settings import get_settings
from theme_intelligence.storage.theme_repository import ThemeRepository


FORBIDDEN = (
    "buy",
    "sell",
    "hold",
    "target price",
    "allocation",
    "portfolio weight",
    "position size",
    "price prediction",
    "fair value",
    "intrinsic value",
    "llm conviction",
    "generated recommendation",
)


def test_stock_research_api_projects_memo_from_persisted_graph(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "stock-research.sqlite3"
    monkeypatch.setattr(main, "settings", replace(get_settings(), sqlite_cache_path=db_path))
    repository = ThemeRepository(db_path)
    repository.initialize()
    _seed_minimal_stock_research_graph(repository)

    response = TestClient(main.app).get("/api/stock-research/AMAT")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["ticker"] == "AMAT"
    assert payload["company_header"]["company_name"] == "Applied Materials"
    assert payload["company_header"]["primary_theme"] == "CoWoS"
    assert payload["company_header"]["theme_rank"] == 1
    assert payload["company_header"]["theme_lifecycle"] == "ACTIVE"
    assert payload["supply_chain_roles"][0]["role_type"] == "Constraint Resolver"
    assert payload["theme_exposure"][0]["theme_id"] == "cowos"
    assert payload["theme_exposure"][0]["rank"] == 1
    assert payload["theme_exposure"][0]["evidence_count"] >= 1
    assert [step["step_type"] for step in payload["evidence_chain"]] == [
        "Theme",
        "Bottleneck",
        "Constraint Resolver",
        "Company",
    ]
    assert payload["research_completeness"]["coverage"] > 0
    assert payload["decision_support"]["research_state"] in {"Research Incomplete", "Evidence Available"}
    assert all(term not in json.dumps(payload).lower() for term in FORBIDDEN)


def test_stock_research_api_is_read_only(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "stock-research-readonly.sqlite3"
    monkeypatch.setattr(main, "settings", replace(get_settings(), sqlite_cache_path=db_path))
    repository = ThemeRepository(db_path)
    repository.initialize()
    _seed_minimal_stock_research_graph(repository)
    before = _table_counts(repository)

    response = TestClient(main.app).get("/api/stock-research/NVDA")

    assert response.status_code == 200
    assert before == _table_counts(repository)


def _seed_minimal_stock_research_graph(repository: ThemeRepository) -> None:
    with repository._connect() as conn:
        now = "2026-06-22T00:00:00+00:00"
        nodes = [
            ("Theme", "cowos", "CoWoS"),
            ("Constraint", "cowos_capacity", "CoWoS Capacity"),
            ("Company", "AMAT", "Applied Materials"),
            ("Company", "NVDA", "NVIDIA"),
        ]
        for node_type, key, name in nodes:
            conn.execute(
                """
                INSERT INTO graph_nodes (
                    node_type, canonical_key, display_name, aliases_json,
                    external_ids_json, status, valid_from, valid_to, created_at,
                    updated_at
                ) VALUES (?, ?, ?, '[]', '{}', 'active', ?, NULL, ?, ?)
                """,
                (node_type, key, name, now, now, now),
            )
        node_ids = {
            row["canonical_key"]: int(row["id"])
            for row in conn.execute("SELECT id, canonical_key FROM graph_nodes")
        }
        conn.execute(
            """
            INSERT INTO graph_snapshots (
                build_version, status, source_watermark, node_count, edge_count,
                checksum, activated_at, created_at
            ) VALUES ('stock-research-build', 'active', 'seed', 4, 3,
                      'checksum', ?, ?)
            """,
            (now, now),
        )
        evidence_rows = [
            ("theme_constraint", "cowos_capacity", "citation-cowos", "CoWoS capacity curated evidence"),
            ("resolver", "amat_cowos", "citation-amat", "Applied Materials resolver evidence"),
            ("exposure", "nvda_cowos", "citation-nvda", "NVIDIA beneficiary evidence"),
        ]
        for source_type, source_record_id, content_hash, citation in evidence_rows:
            conn.execute(
                """
                INSERT INTO graph_evidence (
                    source_type, source_record_id, content_hash, citation,
                    observed_date, review_status, created_at
                ) VALUES (?, ?, ?, ?, NULL, 'reviewed', ?)
                """,
                (source_type, source_record_id, content_hash, citation, now),
            )
        evidence_ids = {
            row["source_record_id"]: int(row["id"])
            for row in conn.execute("SELECT id, source_record_id FROM graph_evidence")
        }
        edges = [
            ("cowos", "THEME_LIMITED_BY_CONSTRAINT", "cowos_capacity", "cowos_capacity"),
            ("cowos_capacity", "CONSTRAINT_RESOLVED_BY_COMPANY", "AMAT", "amat_cowos"),
            ("NVDA", "COMPANY_EXPOSED_TO_CONSTRAINT", "cowos_capacity", "nvda_cowos"),
        ]
        for source, rel, target, evidence_key in edges:
            conn.execute(
                """
                INSERT INTO graph_edges (
                    source_node_id, relationship_type, target_node_id,
                    confidence_score, dependency_strength, status, valid_from,
                    valid_to, build_version, created_at, updated_at
                ) VALUES (?, ?, ?, 80, 80, 'active', ?, NULL,
                          'stock-research-build', ?, ?)
                """,
                (node_ids[source], rel, node_ids[target], now, now, now),
            )
            edge_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            conn.execute(
                "INSERT INTO graph_edge_evidence (edge_id, evidence_id) VALUES (?, ?)",
                (edge_id, evidence_ids[evidence_key]),
            )
        conn.execute(
            """
            INSERT INTO controller_snapshots (
                controller_version, graph_snapshot_id, graph_build_version,
                algorithm_version, status, checksum, company_count, metric_count,
                activated_at, created_at
            ) VALUES ('controller-v', 1, 'stock-research-build',
                      'controller-test', 'active', 'checksum', 1, 1, ?, ?)
            """,
            (now, now),
        )
        conn.execute(
            """
            INSERT INTO controller_metrics (
                controller_snapshot_id, controller_version, graph_snapshot_id,
                company_node_id, dependency_score, controller_score, base_score,
                constraint_influence, material_control, equipment_control,
                process_control, technology_control, resolution_influence,
                supply_chain_influence, coverage, coverage_confidence, rank,
                company_name, controller_types_json, evidence_ids_json,
                reasoning_paths_json, algorithm_version, created_at
            ) VALUES (
                1, 'controller-v', 1, ?, 80, 82, 80, 90, 0, 0, 0, 0, 95,
                0, 88, 88, 1, 'Applied Materials',
                '["Constraint Controller"]', '[2]',
                '[[["Theme","cowos"],["Constraint","cowos_capacity"],["Company","AMAT"]]]',
                'controller-test', ?
            )
            """,
            (node_ids["AMAT"], now),
        )
        conn.execute(
            """
            INSERT INTO opportunity_snapshots (
                opportunity_version, controller_snapshot_id, controller_version,
                graph_snapshot_id, graph_build_version, algorithm_version, status,
                checksum, company_count, path_count, activated_at, created_at
            ) VALUES ('opportunity-v', 1, 'controller-v', 1,
                      'stock-research-build', 'opportunity-test', 'active',
                      'checksum', 1, 1, ?, ?)
            """,
            (now, now),
        )
        conn.execute(
            """
            INSERT INTO opportunity_metrics (
                opportunity_snapshot_id, opportunity_version,
                controller_snapshot_id, graph_snapshot_id, company_node_id,
                company_name, controller_component_raw, controller_component,
                constraint_component_raw, constraint_component,
                dependency_component_raw, dependency_component,
                resolution_component_raw, resolution_component,
                criticality_component_raw, criticality_component,
                market_attention_raw, market_attention_component,
                valuation_penalty_raw, valuation_component,
                bubble_penalty_raw, bubble_risk_component,
                coverage_component, coverage_confidence, base_score,
                opportunity_score, rank, opportunity_types_json,
                configured_weights_json, applied_weights_json,
                availability_states_json, source_records_json,
                evidence_ids_json, algorithm_version, created_at
            ) VALUES (
                1, 'opportunity-v', 1, 1, ?, 'Applied Materials',
                82, 82, 75, 75, 50, 50, 80, 80, 70, 70,
                NULL, NULL, NULL, NULL, NULL, NULL,
                80, 80, 78, 79, 1, '["Constraint Opportunity"]',
                '{}', '{}', '{}',
                '{"market_attention_component":{"name":"market_attention","raw_value":null,"normalized_value":null,"availability_state":"unavailable","configured_weight":0,"applied_weight":0,"source_records":[],"unavailable_reason":"unavailable"},"valuation_component":{"name":"valuation","raw_value":null,"normalized_value":null,"availability_state":"unavailable","configured_weight":0,"applied_weight":0,"source_records":[],"unavailable_reason":"unavailable"},"bubble_risk_component":{"name":"bubble_risk","raw_value":null,"normalized_value":null,"availability_state":"unavailable","configured_weight":0,"applied_weight":0,"source_records":[],"unavailable_reason":"unavailable"}}',
                '[2]', 'opportunity-test', ?
            )
            """,
            (node_ids["AMAT"], now),
        )
        conn.commit()


def _table_counts(repository: ThemeRepository) -> dict[str, int]:
    with repository._connect() as conn:
        return {
            row["name"]: int(conn.execute(f"SELECT COUNT(*) FROM {row['name']}").fetchone()[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        }
