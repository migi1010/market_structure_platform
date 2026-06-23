from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from settings import get_settings
from theme_intelligence.lifecycle.lifecycle_history import append_lifecycle_snapshot, parse_score_history
from theme_intelligence.models import (
    CatalystRecord,
    ThemeBeneficiary,
    ThemeEntity,
    ThemeMention,
    ThemeScore,
    clamp_score,
    expected_next_stage,
    validate_lifecycle_stage,
)


class ThemeRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_settings().sqlite_cache_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=20, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_mentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    symbol TEXT,
                    headline TEXT NOT NULL,
                    mention_time TEXT NOT NULL,
                    sentiment REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    mention_hash TEXT,
                    canonical_headline TEXT,
                    provider_event_id TEXT,
                    url TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_name TEXT NOT NULL UNIQUE,
                    mention_count INTEGER NOT NULL,
                    news_velocity REAL NOT NULL,
                    capital_flow_score REAL NOT NULL,
                    attention_score REAL NOT NULL,
                    sentiment_score REAL NOT NULL,
                    total_score REAL NOT NULL,
                    lifecycle_stage TEXT NOT NULL,
                    lifecycle_confidence REAL NOT NULL,
                    expected_next_stage TEXT NOT NULL,
                    score_history_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    company TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    relationship_strength REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(theme_name, entity_type, ticker)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_catalysts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_name TEXT NOT NULL,
                    catalyst_name TEXT NOT NULL,
                    catalyst_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    impact_score REAL NOT NULL,
                    confidence_score REAL NOT NULL,
                    novelty_score REAL NOT NULL DEFAULT 0,
                    duration_score REAL NOT NULL DEFAULT 0,
                    stage_relevance REAL NOT NULL DEFAULT 0,
                    catalyst_strength REAL NOT NULL DEFAULT 0,
                    cluster_key TEXT NOT NULL DEFAULT '',
                    timeline_status TEXT NOT NULL DEFAULT 'current',
                    polarity TEXT NOT NULL DEFAULT 'positive',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_beneficiaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_name TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    beneficiary_score REAL NOT NULL,
                    relationship_strength REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(theme_name, ticker)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_beneficiary_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_name TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    beneficiary_type TEXT NOT NULL,
                    exposure_score REAL NOT NULL,
                    leverage_score REAL NOT NULL,
                    dependency_score REAL NOT NULL,
                    valuation_penalty REAL NOT NULL,
                    bubble_penalty REAL NOT NULL,
                    beneficiary_score REAL NOT NULL,
                    allocation_score REAL NOT NULL,
                    role TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_bottlenecks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_name TEXT NOT NULL,
                    bottleneck_name TEXT NOT NULL,
                    bottleneck_type TEXT NOT NULL,
                    severity_score REAL NOT NULL,
                    duration_score REAL NOT NULL,
                    resolution_probability REAL NOT NULL,
                    impact_score REAL NOT NULL,
                    bottleneck_strength REAL NOT NULL,
                    controller_entities_json TEXT NOT NULL,
                    beneficiaries_json TEXT NOT NULL,
                    timeline_status TEXT NOT NULL,
                    description TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_discovery_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_name TEXT NOT NULL UNIQUE,
                    theme_id TEXT NOT NULL,
                    name_zh TEXT NOT NULL,
                    discovery_score REAL NOT NULL,
                    emerging_score REAL NOT NULL,
                    catalyst_score REAL NOT NULL,
                    entity_strength_score REAL NOT NULL,
                    confidence_score REAL NOT NULL,
                    crowding_proxy REAL NOT NULL,
                    final_ai_score REAL NOT NULL,
                    lifecycle_stage TEXT NOT NULL,
                    lifecycle_confidence REAL NOT NULL DEFAULT 0,
                    expected_next_stage TEXT NOT NULL,
                    lifecycle_reason TEXT NOT NULL DEFAULT '',
                    time_window TEXT NOT NULL,
                    key_catalysts_json TEXT NOT NULL,
                    beneficiaries_json TEXT NOT NULL,
                    brief_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_final_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_name TEXT NOT NULL UNIQUE,
                    ai_potential_score REAL NOT NULL,
                    research_importance REAL NOT NULL,
                    allocation_readiness REAL NOT NULL,
                    risk_adjusted_score REAL NOT NULL,
                    conviction_level TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    score_components_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_name TEXT NOT NULL,
                    portfolio_type TEXT NOT NULL UNIQUE,
                    theme_weights_json TEXT NOT NULL,
                    risk_profile TEXT NOT NULL,
                    lifecycle_mix_json TEXT NOT NULL,
                    bubble_exposure REAL NOT NULL,
                    portfolio_score REAL NOT NULL,
                    allocation_quality REAL NOT NULL,
                    diversification_score REAL NOT NULL,
                    risk_score REAL NOT NULL,
                    constraints_json TEXT NOT NULL,
                    explanation_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    strength_score REAL NOT NULL,
                    evidence_source TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_type TEXT NOT NULL,
                    canonical_key TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    aliases_json TEXT NOT NULL,
                    external_ids_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(node_type, canonical_key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    citation TEXT NOT NULL,
                    observed_date TEXT,
                    review_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_type, source_record_id, content_hash)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_node_id INTEGER NOT NULL,
                    relationship_type TEXT NOT NULL,
                    target_node_id INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    dependency_strength REAL NOT NULL,
                    status TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    build_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_node_id, relationship_type, target_node_id, valid_from),
                    FOREIGN KEY(source_node_id) REFERENCES graph_nodes(id),
                    FOREIGN KEY(target_node_id) REFERENCES graph_nodes(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_edge_evidence (
                    edge_id INTEGER NOT NULL,
                    evidence_id INTEGER NOT NULL,
                    PRIMARY KEY(edge_id, evidence_id),
                    FOREIGN KEY(edge_id) REFERENCES graph_edges(id) ON DELETE CASCADE,
                    FOREIGN KEY(evidence_id) REFERENCES graph_evidence(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_version TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    source_watermark TEXT NOT NULL,
                    node_count INTEGER NOT NULL,
                    edge_count INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    activated_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS controller_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    controller_version TEXT NOT NULL UNIQUE,
                    graph_snapshot_id INTEGER NOT NULL,
                    graph_build_version TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    company_count INTEGER NOT NULL,
                    metric_count INTEGER NOT NULL,
                    activated_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    controller_snapshot_id INTEGER NOT NULL,
                    controller_version TEXT NOT NULL,
                    graph_snapshot_id INTEGER NOT NULL,
                    node_id INTEGER NOT NULL,
                    metric_name TEXT NOT NULL,
                    raw_value REAL NOT NULL,
                    normalized_value REAL NOT NULL,
                    coverage REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(controller_snapshot_id, node_id, metric_name),
                    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id) ON DELETE CASCADE,
                    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id),
                    FOREIGN KEY(node_id) REFERENCES graph_nodes(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS controller_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    controller_snapshot_id INTEGER NOT NULL,
                    controller_version TEXT NOT NULL,
                    graph_snapshot_id INTEGER NOT NULL,
                    company_node_id INTEGER NOT NULL,
                    dependency_score REAL NOT NULL,
                    controller_score REAL NOT NULL,
                    base_score REAL NOT NULL,
                    constraint_influence REAL NOT NULL,
                    material_control REAL NOT NULL,
                    equipment_control REAL NOT NULL,
                    process_control REAL NOT NULL,
                    technology_control REAL NOT NULL,
                    resolution_influence REAL NOT NULL,
                    supply_chain_influence REAL NOT NULL,
                    coverage REAL NOT NULL,
                    coverage_confidence REAL NOT NULL,
                    rank INTEGER NOT NULL,
                    company_name TEXT NOT NULL,
                    controller_types_json TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    reasoning_paths_json TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(controller_snapshot_id, company_node_id),
                    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id) ON DELETE CASCADE,
                    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id),
                    FOREIGN KEY(company_node_id) REFERENCES graph_nodes(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS opportunity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_version TEXT NOT NULL UNIQUE,
                    controller_snapshot_id INTEGER NOT NULL,
                    controller_version TEXT NOT NULL,
                    graph_snapshot_id INTEGER NOT NULL,
                    graph_build_version TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    company_count INTEGER NOT NULL,
                    path_count INTEGER NOT NULL,
                    activated_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id),
                    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS opportunity_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_snapshot_id INTEGER NOT NULL,
                    opportunity_version TEXT NOT NULL,
                    controller_snapshot_id INTEGER NOT NULL,
                    graph_snapshot_id INTEGER NOT NULL,
                    company_node_id INTEGER NOT NULL,
                    company_name TEXT NOT NULL,
                    controller_component_raw REAL NOT NULL,
                    controller_component REAL NOT NULL,
                    constraint_component_raw REAL NOT NULL,
                    constraint_component REAL NOT NULL,
                    dependency_component_raw REAL NOT NULL,
                    dependency_component REAL NOT NULL,
                    resolution_component_raw REAL NOT NULL,
                    resolution_component REAL NOT NULL,
                    criticality_component_raw REAL NOT NULL,
                    criticality_component REAL NOT NULL,
                    market_attention_raw REAL,
                    market_attention_component REAL,
                    valuation_penalty_raw REAL,
                    valuation_component REAL,
                    bubble_penalty_raw REAL,
                    bubble_risk_component REAL,
                    coverage_component REAL NOT NULL,
                    coverage_confidence REAL NOT NULL,
                    base_score REAL NOT NULL,
                    opportunity_score REAL NOT NULL,
                    rank INTEGER NOT NULL,
                    opportunity_types_json TEXT NOT NULL,
                    configured_weights_json TEXT NOT NULL,
                    applied_weights_json TEXT NOT NULL,
                    availability_states_json TEXT NOT NULL,
                    source_records_json TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(opportunity_snapshot_id, company_node_id),
                    UNIQUE(opportunity_snapshot_id, rank),
                    FOREIGN KEY(opportunity_snapshot_id) REFERENCES opportunity_snapshots(id) ON DELETE CASCADE,
                    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id),
                    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id),
                    FOREIGN KEY(company_node_id) REFERENCES graph_nodes(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS opportunity_reasoning_paths (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_snapshot_id INTEGER NOT NULL,
                    opportunity_version TEXT NOT NULL,
                    company_node_id INTEGER NOT NULL,
                    path_order INTEGER NOT NULL,
                    path_kind TEXT NOT NULL,
                    path_json TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(opportunity_snapshot_id, company_node_id, path_order),
                    FOREIGN KEY(opportunity_snapshot_id) REFERENCES opportunity_snapshots(id) ON DELETE CASCADE,
                    FOREIGN KEY(company_node_id) REFERENCES graph_nodes(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_packets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    packet_family_version TEXT NOT NULL,
                    packet_family_revision INTEGER NOT NULL,
                    packet_type TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    graph_snapshot_id INTEGER NOT NULL,
                    graph_build_version TEXT NOT NULL,
                    controller_snapshot_id INTEGER NOT NULL,
                    controller_version TEXT NOT NULL,
                    opportunity_snapshot_id INTEGER NOT NULL,
                    opportunity_version TEXT NOT NULL,
                    packet_algorithm_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    coverage REAL NOT NULL,
                    evidence_coverage REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    packet_checksum TEXT NOT NULL,
                    family_checksum TEXT NOT NULL,
                    activated_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(packet_family_version, packet_type, subject_key),
                    UNIQUE(opportunity_snapshot_id, packet_family_revision, packet_type, subject_key),
                    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id),
                    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id),
                    FOREIGN KEY(opportunity_snapshot_id) REFERENCES opportunity_snapshots(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_packet_paths (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    packet_id INTEGER NOT NULL,
                    path_order INTEGER NOT NULL,
                    path_kind TEXT NOT NULL,
                    source_opportunity_path_order INTEGER NOT NULL,
                    path_json TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(packet_id, path_order),
                    FOREIGN KEY(packet_id) REFERENCES decision_packets(id) ON DELETE RESTRICT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_packet_evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    packet_id INTEGER NOT NULL,
                    evidence_order INTEGER NOT NULL,
                    evidence_kind TEXT NOT NULL,
                    original_graph_evidence_id INTEGER,
                    source_table TEXT NOT NULL,
                    source_record_key_json TEXT NOT NULL,
                    source_timestamp TEXT,
                    source_value_json TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    citation TEXT,
                    review_status TEXT,
                    availability_state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(packet_id, evidence_order),
                    FOREIGN KEY(packet_id) REFERENCES decision_packets(id) ON DELETE RESTRICT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_packet_risks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    packet_id INTEGER NOT NULL,
                    risk_order INTEGER NOT NULL,
                    risk_category TEXT NOT NULL,
                    risk_code TEXT NOT NULL,
                    risk_state TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    constraint_key TEXT,
                    source_table TEXT,
                    source_record_key_json TEXT NOT NULL,
                    source_timestamp TEXT,
                    source_value_json TEXT NOT NULL,
                    path_orders_json TEXT NOT NULL,
                    evidence_orders_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(packet_id, risk_order),
                    FOREIGN KEY(packet_id) REFERENCES decision_packets(id) ON DELETE RESTRICT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_scout_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scout_version TEXT NOT NULL UNIQUE,
                    algorithm_version TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    provider_model TEXT NOT NULL,
                    weights_json TEXT NOT NULL,
                    source_watermark TEXT NOT NULL,
                    evidence_bundle_checksum TEXT NOT NULL,
                    proposal_checksum TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    candidate_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    activated_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    candidate_key TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_actor TEXT NOT NULL,
                    status_reason TEXT NOT NULL,
                    status_changed_at TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    novelty_score REAL NOT NULL,
                    velocity_score REAL NOT NULL,
                    breadth_score REAL NOT NULL,
                    capital_score REAL NOT NULL,
                    bottleneck_score REAL NOT NULL,
                    serendipity_score REAL NOT NULL,
                    theme_score REAL NOT NULL,
                    coverage REAL NOT NULL,
                    raw_values_json TEXT NOT NULL,
                    normalized_values_json TEXT NOT NULL,
                    applied_weights_json TEXT NOT NULL,
                    readiness_json TEXT NOT NULL,
                    signal_count INTEGER NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    source_count INTEGER NOT NULL,
                    source_types_json TEXT NOT NULL,
                    generated_summary TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(snapshot_id, candidate_key),
                    UNIQUE(snapshot_id, rank),
                    FOREIGN KEY(snapshot_id) REFERENCES theme_scout_snapshots(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_candidate_evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER NOT NULL,
                    evidence_order INTEGER NOT NULL,
                    evidence_key TEXT NOT NULL,
                    source_table TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_timestamp TEXT NOT NULL,
                    source_identifier TEXT NOT NULL,
                    citation TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    domain_type TEXT NOT NULL,
                    cluster_key TEXT NOT NULL,
                    source_value_json TEXT NOT NULL,
                    availability_state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(candidate_id, evidence_order),
                    UNIQUE(candidate_id, evidence_key),
                    FOREIGN KEY(candidate_id) REFERENCES theme_candidates(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_candidate_paths (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER NOT NULL,
                    path_order INTEGER NOT NULL,
                    path_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    path_payload_json TEXT NOT NULL,
                    evidence_keys_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(candidate_id, path_order),
                    FOREIGN KEY(candidate_id) REFERENCES theme_candidates(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS theme_candidate_influence_maps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER NOT NULL,
                    influence_order INTEGER NOT NULL,
                    target_type TEXT NOT NULL,
                    target_label TEXT NOT NULL,
                    hypothesis_state TEXT NOT NULL,
                    evidence_keys_json TEXT NOT NULL,
                    source_cluster_keys_json TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(candidate_id, influence_order),
                    FOREIGN KEY(candidate_id) REFERENCES theme_candidates(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_pipeline_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL UNIQUE,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    theme_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    activated_at TEXT,
                    archived_at TEXT,
                    lineage_checksum TEXT NOT NULL,
                    UNIQUE(source_type, source_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_pipeline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    case_id TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(case_id) REFERENCES research_pipeline_cases(case_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_pipeline_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_id TEXT NOT NULL UNIQUE,
                    case_id TEXT NOT NULL,
                    linked_type TEXT NOT NULL,
                    linked_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(case_id, linked_type, linked_id),
                    FOREIGN KEY(case_id) REFERENCES research_pipeline_cases(case_id) ON DELETE CASCADE
                )
                """
            )
            self._add_column_if_missing(conn, "theme_mentions", "mention_hash", "TEXT")
            self._add_column_if_missing(conn, "theme_candidates", "updated_at", "TEXT NOT NULL DEFAULT ''")
            self._add_column_if_missing(conn, "theme_mentions", "canonical_headline", "TEXT")
            self._add_column_if_missing(conn, "theme_mentions", "provider_event_id", "TEXT")
            self._add_column_if_missing(conn, "theme_mentions", "url", "TEXT")
            self._add_column_if_missing(conn, "theme_discovery_scores", "lifecycle_confidence", "REAL NOT NULL DEFAULT 0")
            self._add_column_if_missing(conn, "theme_discovery_scores", "lifecycle_reason", "TEXT NOT NULL DEFAULT ''")
            self._add_column_if_missing(conn, "theme_catalysts", "description", "TEXT NOT NULL DEFAULT ''")
            self._add_column_if_missing(conn, "theme_catalysts", "novelty_score", "REAL NOT NULL DEFAULT 0")
            self._add_column_if_missing(conn, "theme_catalysts", "duration_score", "REAL NOT NULL DEFAULT 0")
            self._add_column_if_missing(conn, "theme_catalysts", "stage_relevance", "REAL NOT NULL DEFAULT 0")
            self._add_column_if_missing(conn, "theme_catalysts", "catalyst_strength", "REAL NOT NULL DEFAULT 0")
            self._add_column_if_missing(conn, "theme_catalysts", "cluster_key", "TEXT NOT NULL DEFAULT ''")
            self._add_column_if_missing(conn, "theme_catalysts", "timeline_status", "TEXT NOT NULL DEFAULT 'current'")
            self._add_column_if_missing(conn, "theme_catalysts", "polarity", "TEXT NOT NULL DEFAULT 'positive'")
            self._add_column_if_missing(conn, "theme_catalysts", "updated_at", "TEXT")
            self._backfill_catalyst_migration(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_mentions_theme_time ON theme_mentions(theme_name, mention_time)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_theme_mentions_hash ON theme_mentions(mention_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_scores_total ON theme_scores(total_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_catalysts_theme ON theme_catalysts(theme_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_catalysts_theme_strength ON theme_catalysts(theme_name, catalyst_strength)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_catalysts_theme_cluster ON theme_catalysts(theme_name, cluster_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_catalysts_theme_timeline ON theme_catalysts(theme_name, timeline_status)")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_theme_catalysts_upsert
                ON theme_catalysts(theme_name, cluster_key, catalyst_type, source)
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_beneficiaries_theme ON theme_beneficiaries(theme_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_beneficiary_scores_theme_allocation ON theme_beneficiary_scores(theme_name, allocation_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_beneficiary_scores_theme_type ON theme_beneficiary_scores(theme_name, beneficiary_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_beneficiary_scores_ticker ON theme_beneficiary_scores(ticker)")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_theme_beneficiary_scores_upsert
                ON theme_beneficiary_scores(theme_name, ticker, beneficiary_type)
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_bottlenecks_theme_strength ON theme_bottlenecks(theme_name, bottleneck_strength)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_bottlenecks_theme_type ON theme_bottlenecks(theme_name, bottleneck_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_bottlenecks_theme_timeline ON theme_bottlenecks(theme_name, timeline_status)")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_theme_bottlenecks_upsert
                ON theme_bottlenecks(theme_name, bottleneck_name, bottleneck_type)
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_discovery_scores_final ON theme_discovery_scores(final_ai_score)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_theme_final_scores_theme ON theme_final_scores(theme_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_final_scores_risk_adjusted ON theme_final_scores(risk_adjusted_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_final_scores_research ON theme_final_scores(research_importance)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_final_scores_allocation ON theme_final_scores(allocation_readiness)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_final_scores_conviction ON theme_final_scores(conviction_level)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_theme_portfolios_type ON theme_portfolios(portfolio_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_portfolios_score ON theme_portfolios(portfolio_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_portfolios_risk_profile ON theme_portfolios(risk_profile)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_portfolios_bubble ON theme_portfolios(bubble_exposure)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_graph_edges_source ON theme_graph_edges(source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_graph_edges_target ON theme_graph_edges(target_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_graph_edges_relationship ON theme_graph_edges(relationship_type)")
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_theme_graph_edges_unique
                ON theme_graph_edges(source_type, source_id, target_type, target_id, relationship_type)
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_scout_snapshot_status ON theme_scout_snapshots(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_candidates_snapshot_rank ON theme_candidates(snapshot_id, rank)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_candidates_key ON theme_candidates(candidate_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_candidate_evidence_candidate ON theme_candidate_evidence(candidate_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_candidate_paths_candidate ON theme_candidate_paths(candidate_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_theme_candidate_influence_candidate ON theme_candidate_influence_maps(candidate_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_pipeline_cases_status ON research_pipeline_cases(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_pipeline_cases_source ON research_pipeline_cases(source_type, source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_pipeline_cases_theme ON research_pipeline_cases(theme_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_pipeline_events_case ON research_pipeline_events(case_id, created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_pipeline_links_case ON research_pipeline_links(case_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_pipeline_links_type ON research_pipeline_links(linked_type, linked_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_canonical_key ON graph_nodes(canonical_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_status ON graph_nodes(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_relationship ON graph_edges(relationship_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_build_status ON graph_edges(build_version, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_snapshots_build_version ON graph_snapshots(build_version)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_snapshots_status ON graph_snapshots(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_controller_snapshots_status ON controller_snapshots(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_controller_snapshots_graph ON controller_snapshots(graph_snapshot_id, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_metrics_snapshot_metric ON graph_metrics(controller_snapshot_id, metric_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_controller_metrics_snapshot_rank ON controller_metrics(controller_snapshot_id, rank)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_controller_metrics_company ON controller_metrics(company_node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunity_snapshots_status ON opportunity_snapshots(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunity_snapshots_controller ON opportunity_snapshots(controller_snapshot_id, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunity_metrics_snapshot_rank ON opportunity_metrics(opportunity_snapshot_id, rank)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunity_metrics_company ON opportunity_metrics(company_node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunity_paths_snapshot_company ON opportunity_reasoning_paths(opportunity_snapshot_id, company_node_id, path_order)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_packets_family_status ON decision_packets(packet_family_version, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_packets_active ON decision_packets(status, packet_type, subject_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_packets_opportunity_revision ON decision_packets(opportunity_snapshot_id, packet_family_revision)")
            conn.commit()

    @staticmethod
    def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _backfill_catalyst_migration(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT id, theme_name, catalyst_name, catalyst_type, source, created_at, updated_at, cluster_key
            FROM theme_catalysts
            """
        ).fetchall()
        for row in rows:
            cluster_key = str(row["cluster_key"] or "").strip() or self._legacy_catalyst_cluster_key(
                str(row["theme_name"]),
                str(row["catalyst_name"]),
                str(row["catalyst_type"]),
            )
            updated_at = row["updated_at"] or row["created_at"]
            conn.execute(
                "UPDATE theme_catalysts SET cluster_key = ?, updated_at = ? WHERE id = ?",
                (cluster_key, updated_at, row["id"]),
            )
        conn.execute(
            """
            DELETE FROM theme_catalysts
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM theme_catalysts
                GROUP BY theme_name, cluster_key, catalyst_type, source
            )
            """
        )

    @staticmethod
    def _legacy_catalyst_cluster_key(theme_name: str, catalyst_name: str, catalyst_type: str) -> str:
        raw = f"{theme_name}:{catalyst_name}:{catalyst_type}".lower()
        return re.sub(r"[^a-z0-9]+", "_", raw).strip("_")

    def save_mentions(self, mentions: Iterable[ThemeMention]) -> int:
        rows = list(mentions)
        if not rows:
            return 0
        with self._connect() as conn:
            before = int(conn.execute("SELECT COUNT(*) FROM theme_mentions").fetchone()[0])
            conn.executemany(
                """
                INSERT OR IGNORE INTO theme_mentions (
                    theme_name, source, symbol, headline, mention_time, sentiment, created_at,
                    mention_hash, canonical_headline, provider_event_id, url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row.theme_name,
                        row.source,
                        row.symbol,
                        row.headline,
                        row.mention_time,
                        clamp_score(row.sentiment, 50.0),
                        row.created_at,
                        row.mention_hash,
                        row.canonical_headline,
                        row.provider_event_id,
                        row.url,
                    )
                    for row in rows
                ],
            )
            conn.commit()
            after = int(conn.execute("SELECT COUNT(*) FROM theme_mentions").fetchone()[0])
            return max(0, after - before)

    def save_entities(self, entities: Iterable[ThemeEntity]) -> int:
        rows = list(entities)
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO theme_entities (theme_name, entity_type, company, ticker, relationship_strength, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(theme_name, entity_type, ticker) DO UPDATE SET
                    company = excluded.company,
                    relationship_strength = excluded.relationship_strength,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        row.theme_name,
                        row.entity_type,
                        row.company,
                        row.ticker,
                        clamp_score(row.relationship_strength),
                        row.updated_at,
                    )
                    for row in rows
                ],
            )
            conn.commit()
        return len(rows)

    def save_catalysts(self, catalysts: Iterable[CatalystRecord]) -> int:
        rows = list(catalysts)
        if not rows:
            return 0
        with self._connect() as conn:
            for row in rows:
                cluster_key = str(getattr(row, "cluster_key", "") or self._legacy_catalyst_cluster_key(row.theme_name, row.catalyst_name, row.catalyst_type))
                updated_at = str(getattr(row, "updated_at", "") or row.created_at)
                conn.execute(
                """
                INSERT INTO theme_catalysts (
                    theme_name, catalyst_name, catalyst_type, source, description, impact_score,
                    confidence_score, novelty_score, duration_score, stage_relevance, catalyst_strength,
                    cluster_key, timeline_status, polarity, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(theme_name, cluster_key, catalyst_type, source) DO UPDATE SET
                    catalyst_name = excluded.catalyst_name,
                    description = excluded.description,
                    impact_score = MAX(theme_catalysts.impact_score, excluded.impact_score),
                    confidence_score = MAX(theme_catalysts.confidence_score, excluded.confidence_score),
                    novelty_score = MAX(theme_catalysts.novelty_score, excluded.novelty_score),
                    duration_score = MAX(theme_catalysts.duration_score, excluded.duration_score),
                    stage_relevance = MAX(theme_catalysts.stage_relevance, excluded.stage_relevance),
                    catalyst_strength = MAX(theme_catalysts.catalyst_strength, excluded.catalyst_strength),
                    timeline_status = excluded.timeline_status,
                    polarity = CASE
                        WHEN theme_catalysts.polarity = 'risk' OR excluded.polarity = 'risk' THEN 'risk'
                        ELSE excluded.polarity
                    END,
                    updated_at = excluded.updated_at
                """,
                    (
                        row.theme_name,
                        row.catalyst_name,
                        row.catalyst_type,
                        row.source,
                        str(getattr(row, "description", "")),
                        clamp_score(row.impact_score),
                        clamp_score(row.confidence_score),
                        clamp_score(getattr(row, "novelty_score", 0.0)),
                        clamp_score(getattr(row, "duration_score", 0.0)),
                        clamp_score(getattr(row, "stage_relevance", 0.0)),
                        clamp_score(getattr(row, "catalyst_strength", 0.0)),
                        cluster_key,
                        str(getattr(row, "timeline_status", "current") or "current"),
                        str(getattr(row, "polarity", "positive") or "positive"),
                        row.created_at,
                        updated_at,
                    )
                )
            conn.commit()
        return len(rows)

    def save_beneficiaries(self, beneficiaries: Iterable[ThemeBeneficiary]) -> int:
        rows = list(beneficiaries)
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO theme_beneficiaries (
                    theme_name, ticker, company_name, beneficiary_score, relationship_strength, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(theme_name, ticker) DO UPDATE SET
                    company_name = excluded.company_name,
                    beneficiary_score = excluded.beneficiary_score,
                    relationship_strength = excluded.relationship_strength,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        row.theme_name,
                        row.ticker,
                        row.company_name,
                        clamp_score(row.beneficiary_score),
                        clamp_score(row.relationship_strength),
                        row.updated_at,
                    )
                    for row in rows
                ],
            )
            conn.commit()
        return len(rows)

    def save_bottlenecks(self, bottlenecks: Iterable[Any]) -> int:
        rows = list(bottlenecks)
        if not rows:
            return 0
        with self._connect() as conn:
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO theme_bottlenecks (
                        theme_name, bottleneck_name, bottleneck_type, severity_score, duration_score,
                        resolution_probability, impact_score, bottleneck_strength, controller_entities_json,
                        beneficiaries_json, timeline_status, description, evidence_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(theme_name, bottleneck_name, bottleneck_type) DO UPDATE SET
                        severity_score = MAX(theme_bottlenecks.severity_score, excluded.severity_score),
                        duration_score = MAX(theme_bottlenecks.duration_score, excluded.duration_score),
                        resolution_probability = excluded.resolution_probability,
                        impact_score = MAX(theme_bottlenecks.impact_score, excluded.impact_score),
                        bottleneck_strength = MAX(theme_bottlenecks.bottleneck_strength, excluded.bottleneck_strength),
                        controller_entities_json = excluded.controller_entities_json,
                        beneficiaries_json = excluded.beneficiaries_json,
                        timeline_status = excluded.timeline_status,
                        description = excluded.description,
                        evidence_json = excluded.evidence_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        row.theme_name,
                        row.bottleneck_name,
                        row.bottleneck_type,
                        clamp_score(row.severity_score),
                        clamp_score(row.duration_score),
                        clamp_score(row.resolution_probability),
                        clamp_score(row.impact_score),
                        clamp_score(row.bottleneck_strength),
                        json.dumps(row.controller_entities, ensure_ascii=False, allow_nan=False),
                        json.dumps(row.beneficiaries, ensure_ascii=False, allow_nan=False),
                        row.timeline_status,
                        row.description,
                        json.dumps(row.evidence, ensure_ascii=False, allow_nan=False),
                        row.updated_at,
                    ),
                )
            conn.commit()
        return len(rows)

    def save_beneficiary_scores(self, scores: Iterable[Any]) -> int:
        rows = list(scores)
        if not rows:
            return 0
        with self._connect() as conn:
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO theme_beneficiary_scores (
                        theme_name, ticker, company_name, beneficiary_type, exposure_score, leverage_score,
                        dependency_score, valuation_penalty, bubble_penalty, beneficiary_score,
                        allocation_score, role, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(theme_name, ticker, beneficiary_type) DO UPDATE SET
                        company_name = excluded.company_name,
                        exposure_score = excluded.exposure_score,
                        leverage_score = excluded.leverage_score,
                        dependency_score = excluded.dependency_score,
                        valuation_penalty = excluded.valuation_penalty,
                        bubble_penalty = excluded.bubble_penalty,
                        beneficiary_score = excluded.beneficiary_score,
                        allocation_score = excluded.allocation_score,
                        role = excluded.role,
                        updated_at = excluded.updated_at
                    """,
                    (
                        row.theme_name,
                        row.ticker,
                        row.company_name,
                        row.beneficiary_type,
                        clamp_score(row.exposure_score),
                        clamp_score(row.leverage_score),
                        clamp_score(row.dependency_score),
                        clamp_score(row.valuation_penalty),
                        clamp_score(row.bubble_penalty),
                        clamp_score(row.beneficiary_score),
                        clamp_score(row.allocation_score),
                        row.role,
                        row.updated_at,
                    ),
                )
            conn.commit()
        return len(rows)

    def upsert_scores(self, scores: Iterable[ThemeScore]) -> int:
        rows = list(scores)
        if not rows:
            return 0
        with self._connect() as conn:
            for row in rows:
                stage = validate_lifecycle_stage(row.lifecycle_stage)
                next_stage = expected_next_stage(row.expected_next_stage if row.expected_next_stage else stage)
                if row.expected_next_stage:
                    next_stage = validate_lifecycle_stage(row.expected_next_stage, next_stage)
                history = self._next_history(conn, row)
                conn.execute(
                    """
                    INSERT INTO theme_scores (
                        theme_name, mention_count, news_velocity, capital_flow_score, attention_score,
                        sentiment_score, total_score, lifecycle_stage, lifecycle_confidence,
                        expected_next_stage, score_history_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(theme_name) DO UPDATE SET
                        mention_count = excluded.mention_count,
                        news_velocity = excluded.news_velocity,
                        capital_flow_score = excluded.capital_flow_score,
                        attention_score = excluded.attention_score,
                        sentiment_score = excluded.sentiment_score,
                        total_score = excluded.total_score,
                        lifecycle_stage = excluded.lifecycle_stage,
                        lifecycle_confidence = excluded.lifecycle_confidence,
                        expected_next_stage = excluded.expected_next_stage,
                        score_history_json = excluded.score_history_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        row.theme_name,
                        int(max(0, row.mention_count)),
                        clamp_score(row.news_velocity),
                        clamp_score(row.capital_flow_score),
                        clamp_score(row.attention_score),
                        clamp_score(row.sentiment_score, 50.0),
                        clamp_score(row.total_score),
                        stage,
                        clamp_score(row.lifecycle_confidence),
                        next_stage,
                        history,
                        row.updated_at,
                    ),
                )
            conn.commit()
        return len(rows)

    def _next_history(self, conn: sqlite3.Connection, score: ThemeScore) -> str:
        current: list[dict] = []
        row = conn.execute(
            "SELECT score_history_json FROM theme_scores WHERE theme_name = ?",
            (score.theme_name,),
        ).fetchone()
        if row is not None:
            try:
                parsed = json.loads(str(row["score_history_json"] or "[]"))
                if isinstance(parsed, list):
                    current = [item for item in parsed if isinstance(item, dict)]
            except json.JSONDecodeError:
                current = []
        current.append(
            {
                "captured_at": score.updated_at,
                "mention_score": clamp_score(score.mention_count),
                "velocity_score": clamp_score(score.news_velocity),
                "sentiment_score": clamp_score(score.sentiment_score, 50.0),
                "attention_score": clamp_score(score.attention_score),
                "capital_flow_score": clamp_score(score.capital_flow_score),
                "total_score": clamp_score(score.total_score),
                "lifecycle_stage": validate_lifecycle_stage(score.lifecycle_stage),
            }
        )
        return json.dumps(current[-60:], ensure_ascii=False, allow_nan=False)

    def get_scores(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM theme_scores
                ORDER BY total_score DESC, theme_name ASC
                """
            ).fetchall()
        return [self._score_row(row) for row in rows]

    def get_top_scores(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM theme_scores
                ORDER BY total_score DESC, theme_name ASC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        return [self._score_row(row) for row in rows]

    def get_recent_mentions(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM theme_mentions ORDER BY mention_time DESC").fetchall()
        return [dict(row) for row in rows]

    def get_mentions(self) -> list[ThemeMention]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM theme_mentions ORDER BY mention_time DESC").fetchall()
        return [
            ThemeMention(
                theme_name=str(row["theme_name"]),
                source=str(row["source"]),
                symbol=row["symbol"],
                headline=str(row["headline"]),
                mention_time=str(row["mention_time"]),
                sentiment=clamp_score(row["sentiment"], 50.0),
                created_at=str(row["created_at"]),
                mention_hash=row["mention_hash"],
                canonical_headline=row["canonical_headline"],
                provider_event_id=row["provider_event_id"],
                url=row["url"],
            )
            for row in rows
        ]

    def get_catalysts(self, theme_name: str | None = None) -> list[CatalystRecord]:
        where = " WHERE theme_name = ?" if theme_name else ""
        values = (theme_name,) if theme_name else ()
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM theme_catalysts{where} ORDER BY created_at DESC",
                values,
            ).fetchall()
        return [
            CatalystRecord(
                theme_name=str(row["theme_name"]),
                catalyst_name=str(row["catalyst_name"]),
                catalyst_type=str(row["catalyst_type"]),
                source=str(row["source"]),
                impact_score=clamp_score(row["impact_score"]),
                confidence_score=clamp_score(row["confidence_score"]),
                description=str(row["description"] if "description" in row.keys() else ""),
                novelty_score=clamp_score(row["novelty_score"] if "novelty_score" in row.keys() else 0.0),
                duration_score=clamp_score(row["duration_score"] if "duration_score" in row.keys() else 0.0),
                stage_relevance=clamp_score(row["stage_relevance"] if "stage_relevance" in row.keys() else 0.0),
                catalyst_strength=clamp_score(row["catalyst_strength"] if "catalyst_strength" in row.keys() else 0.0),
                cluster_key=str(row["cluster_key"] if "cluster_key" in row.keys() else ""),
                timeline_status=str(row["timeline_status"] if "timeline_status" in row.keys() else "current"),
                polarity=str(row["polarity"] if "polarity" in row.keys() else "positive"),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"] if "updated_at" in row.keys() else row["created_at"]),
            )
            for row in rows
        ]

    def get_entities(self, theme_name: str | None = None) -> list[ThemeEntity]:
        where = " WHERE theme_name = ?" if theme_name else ""
        values = (theme_name,) if theme_name else ()
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM theme_entities{where} ORDER BY updated_at DESC",
                values,
            ).fetchall()
        return [
            ThemeEntity(
                theme_name=str(row["theme_name"]),
                entity_type=str(row["entity_type"]),
                company=str(row["company"]),
                ticker=str(row["ticker"]),
                relationship_strength=clamp_score(row["relationship_strength"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def get_beneficiaries(self) -> list[ThemeBeneficiary]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM theme_beneficiaries ORDER BY updated_at DESC").fetchall()
        return [
            ThemeBeneficiary(
                theme_name=str(row["theme_name"]),
                ticker=str(row["ticker"]),
                company_name=str(row["company_name"]),
                beneficiary_score=clamp_score(row["beneficiary_score"]),
                relationship_strength=clamp_score(row["relationship_strength"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def get_bottlenecks(self, theme_name: str | None = None) -> list[Any]:
        from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord

        where = " WHERE theme_name = ?" if theme_name else ""
        values = (theme_name,) if theme_name else ()
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM theme_bottlenecks{where} ORDER BY bottleneck_strength DESC, updated_at DESC",
                values,
            ).fetchall()
        return [
            BottleneckRecord(
                theme_name=str(row["theme_name"]),
                bottleneck_name=str(row["bottleneck_name"]),
                bottleneck_type=str(row["bottleneck_type"]),
                severity_score=clamp_score(row["severity_score"]),
                duration_score=clamp_score(row["duration_score"]),
                resolution_probability=clamp_score(row["resolution_probability"]),
                impact_score=clamp_score(row["impact_score"]),
                bottleneck_strength=clamp_score(row["bottleneck_strength"]),
                controller_entities=self._json_list(row["controller_entities_json"]),
                beneficiaries=self._json_list(row["beneficiaries_json"]),
                timeline_status=str(row["timeline_status"]),
                description=str(row["description"]),
                evidence=self._json_list(row["evidence_json"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def get_beneficiary_scores(self, theme_name: str | None = None) -> list[Any]:
        from theme_intelligence.beneficiaries.beneficiary_allocator import BeneficiaryAllocator
        from theme_intelligence.beneficiaries.beneficiary_models import BeneficiaryScoreRecord

        where = " WHERE theme_name = ?" if theme_name else ""
        values = (theme_name,) if theme_name else ()
        allocator = BeneficiaryAllocator()
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM theme_beneficiary_scores{where} ORDER BY allocation_score DESC, beneficiary_score DESC",
                values,
            ).fetchall()
        records: list[Any] = []
        for row in rows:
            record = BeneficiaryScoreRecord(
                theme_name=str(row["theme_name"]),
                ticker=str(row["ticker"]),
                company_name=str(row["company_name"]),
                beneficiary_type=str(row["beneficiary_type"]),
                exposure_score=clamp_score(row["exposure_score"]),
                leverage_score=clamp_score(row["leverage_score"]),
                dependency_score=clamp_score(row["dependency_score"]),
                valuation_penalty=clamp_score(row["valuation_penalty"]),
                bubble_penalty=clamp_score(row["bubble_penalty"]),
                beneficiary_score=clamp_score(row["beneficiary_score"]),
                allocation_score=clamp_score(row["allocation_score"]),
                role=str(row["role"]),
                updated_at=str(row["updated_at"]),
            )
            bucket = allocator.bucket(record)
            records.append(record.with_updates(allocation_bucket=bucket, allocation_reason=allocator.reason(record.with_updates(allocation_bucket=bucket))))
        return records

    def upsert_discovery_scores(self, rows: Iterable[dict]) -> int:
        payloads = list(rows)
        if not payloads:
            return 0
        with self._connect() as conn:
            for row in payloads:
                conn.execute(
                    """
                    INSERT INTO theme_discovery_scores (
                        theme_name, theme_id, name_zh, discovery_score, emerging_score, catalyst_score,
                        entity_strength_score, confidence_score, crowding_proxy, final_ai_score,
                        lifecycle_stage, lifecycle_confidence, expected_next_stage, lifecycle_reason,
                        time_window, key_catalysts_json, beneficiaries_json, brief_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(theme_name) DO UPDATE SET
                        theme_id = excluded.theme_id,
                        name_zh = excluded.name_zh,
                        discovery_score = excluded.discovery_score,
                        emerging_score = excluded.emerging_score,
                        catalyst_score = excluded.catalyst_score,
                        entity_strength_score = excluded.entity_strength_score,
                        confidence_score = excluded.confidence_score,
                        crowding_proxy = excluded.crowding_proxy,
                        final_ai_score = excluded.final_ai_score,
                        lifecycle_stage = excluded.lifecycle_stage,
                        lifecycle_confidence = excluded.lifecycle_confidence,
                        expected_next_stage = excluded.expected_next_stage,
                        lifecycle_reason = excluded.lifecycle_reason,
                        time_window = excluded.time_window,
                        key_catalysts_json = excluded.key_catalysts_json,
                        beneficiaries_json = excluded.beneficiaries_json,
                        brief_json = excluded.brief_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        row["name"],
                        row["theme_id"],
                        row["name_zh"],
                        clamp_score(row["discovery_score"]),
                        clamp_score(row["emerging_score"]),
                        clamp_score(row["catalyst_score"]),
                        clamp_score(row["entity_strength_score"]),
                        clamp_score(row["confidence_score"]),
                        clamp_score(row["crowding_proxy"]),
                        clamp_score(row["ai_score"]),
                        validate_lifecycle_stage(row["lifecycle_stage"]),
                        clamp_score(row.get("lifecycle_confidence", 0.0)),
                        validate_lifecycle_stage(row["expected_next_stage"]),
                        row.get("lifecycle_reason", ""),
                        row["time_window"],
                        json.dumps(row["key_catalysts"], ensure_ascii=False, allow_nan=False),
                        json.dumps(row["beneficiaries"], ensure_ascii=False, allow_nan=False),
                        json.dumps(row["brief"], ensure_ascii=False, allow_nan=False),
                        row["updated_at"],
                    ),
                )
            conn.commit()
        return len(payloads)

    def get_discovery_scores(self, limit: int = 20, theme_id: str | None = None) -> list[dict]:
        where = " WHERE theme_id = ?" if theme_id else ""
        values: tuple[Any, ...] = (theme_id, max(1, int(limit))) if theme_id else (max(1, int(limit)),)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM theme_discovery_scores
                {where}
                ORDER BY final_ai_score DESC, theme_name ASC
                LIMIT ?
                """,
                values,
            ).fetchall()
        return [
            {
                "theme_id": row["theme_id"],
                "name": row["theme_name"],
                "name_zh": row["name_zh"],
                "ai_score": clamp_score(row["final_ai_score"]),
                "discovery_score": clamp_score(row["discovery_score"]),
                "emerging_score": clamp_score(row["emerging_score"]),
                "catalyst_score": clamp_score(row["catalyst_score"]),
                "entity_strength_score": clamp_score(row["entity_strength_score"]),
                "confidence_score": clamp_score(row["confidence_score"]),
                "crowding_proxy": clamp_score(row["crowding_proxy"]),
                "lifecycle_stage": validate_lifecycle_stage(row["lifecycle_stage"]),
                "lifecycle_confidence": clamp_score(row["lifecycle_confidence"] if "lifecycle_confidence" in row.keys() else 0.0),
                "expected_next_stage": validate_lifecycle_stage(row["expected_next_stage"]),
                "lifecycle_reason": row["lifecycle_reason"] if "lifecycle_reason" in row.keys() else "",
                "time_window": row["time_window"],
                "key_catalysts": json.loads(row["key_catalysts_json"]),
                "beneficiaries": json.loads(row["beneficiaries_json"]),
                "brief": json.loads(row["brief_json"]),
            }
            for row in rows
        ]

    def save_final_scores(self, scores: Iterable[Any]) -> int:
        payloads = list(scores)
        if not payloads:
            return 0
        with self._connect() as conn:
            for row in payloads:
                conn.execute(
                    """
                    INSERT INTO theme_final_scores (
                        theme_name, ai_potential_score, research_importance, allocation_readiness,
                        risk_adjusted_score, conviction_level, updated_at, score_components_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(theme_name) DO UPDATE SET
                        ai_potential_score = excluded.ai_potential_score,
                        research_importance = excluded.research_importance,
                        allocation_readiness = excluded.allocation_readiness,
                        risk_adjusted_score = excluded.risk_adjusted_score,
                        conviction_level = excluded.conviction_level,
                        updated_at = excluded.updated_at,
                        score_components_json = excluded.score_components_json
                    """,
                    (
                        row.theme_name,
                        clamp_score(row.ai_potential_score),
                        clamp_score(row.research_importance),
                        clamp_score(row.allocation_readiness),
                        clamp_score(row.risk_adjusted_score),
                        row.conviction_level,
                        row.updated_at,
                        json.dumps(
                            {
                                "components": row.score_components,
                                "why_high_score": row.why_high_score,
                                "why_low_score": row.why_low_score,
                                "major_strengths": row.major_strengths,
                                "major_risks": row.major_risks,
                                "allocation_notes": row.allocation_notes,
                                "conviction_reason": row.conviction_reason,
                            },
                            ensure_ascii=False,
                            allow_nan=False,
                        ),
                    ),
                )
            conn.commit()
        return len(payloads)

    def get_final_scores(self, limit: int = 20, theme_name: str | None = None) -> list[Any]:
        from theme_intelligence.theme_score.theme_score_models import ThemeFinalScore

        where = " WHERE theme_name = ?" if theme_name else ""
        values: tuple[Any, ...] = (theme_name, max(1, int(limit))) if theme_name else (max(1, int(limit)),)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM theme_final_scores
                {where}
                ORDER BY risk_adjusted_score DESC, research_importance DESC
                LIMIT ?
                """,
                values,
            ).fetchall()
        records: list[Any] = []
        for row in rows:
            payload = self._json_dict(row["score_components_json"])
            records.append(
                ThemeFinalScore(
                    theme_name=str(row["theme_name"]),
                    ai_potential_score=clamp_score(row["ai_potential_score"]),
                    research_importance=clamp_score(row["research_importance"]),
                    allocation_readiness=clamp_score(row["allocation_readiness"]),
                    risk_adjusted_score=clamp_score(row["risk_adjusted_score"]),
                    conviction_level=str(row["conviction_level"]),
                    updated_at=str(row["updated_at"]),
                    score_components=payload.get("components", {}),
                    why_high_score=str(payload.get("why_high_score", "")),
                    why_low_score=str(payload.get("why_low_score", "")),
                    major_strengths=self._json_list(payload.get("major_strengths", [])),
                    major_risks=self._json_list(payload.get("major_risks", [])),
                    allocation_notes=self._json_list(payload.get("allocation_notes", [])),
                    conviction_reason=str(payload.get("conviction_reason", "")),
                )
            )
        return records

    def save_portfolios(self, portfolios: Iterable[Any]) -> int:
        payloads = list(portfolios)
        if not payloads:
            return 0
        with self._connect() as conn:
            for row in payloads:
                conn.execute(
                    """
                    INSERT INTO theme_portfolios (
                        portfolio_name, portfolio_type, theme_weights_json, risk_profile,
                        lifecycle_mix_json, bubble_exposure, portfolio_score, allocation_quality,
                        diversification_score, risk_score, constraints_json, explanation_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(portfolio_type) DO UPDATE SET
                        portfolio_name = excluded.portfolio_name,
                        theme_weights_json = excluded.theme_weights_json,
                        risk_profile = excluded.risk_profile,
                        lifecycle_mix_json = excluded.lifecycle_mix_json,
                        bubble_exposure = excluded.bubble_exposure,
                        portfolio_score = excluded.portfolio_score,
                        allocation_quality = excluded.allocation_quality,
                        diversification_score = excluded.diversification_score,
                        risk_score = excluded.risk_score,
                        constraints_json = excluded.constraints_json,
                        explanation_json = excluded.explanation_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        row.portfolio_name,
                        row.portfolio_type,
                        json.dumps([theme.to_api() for theme in row.themes], ensure_ascii=False, allow_nan=False),
                        row.risk_profile,
                        json.dumps(row.lifecycle_mix, ensure_ascii=False, allow_nan=False),
                        clamp_score(row.bubble_exposure),
                        clamp_score(row.portfolio_score),
                        clamp_score(row.allocation_quality),
                        clamp_score(row.diversification_score),
                        clamp_score(row.risk_score),
                        json.dumps(row.constraints, ensure_ascii=False, allow_nan=False),
                        json.dumps(
                            {
                                "why_selected": row.why_selected,
                                "why_excluded": row.why_excluded,
                                "risk_sources": row.risk_sources,
                                "bubble_sources": row.bubble_sources,
                                "diversification_notes": row.diversification_notes,
                                "lifecycle_balance": row.lifecycle_balance,
                            },
                            ensure_ascii=False,
                            allow_nan=False,
                        ),
                        row.updated_at,
                    ),
                )
            conn.commit()
        return len(payloads)

    def get_portfolios(self, limit: int = 20) -> list[Any]:
        from theme_intelligence.portfolio.portfolio_models import PortfolioAllocation, PortfolioResult

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM theme_portfolios
                ORDER BY portfolio_score DESC, portfolio_type ASC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        records: list[Any] = []
        for row in rows:
            explanation = self._json_dict(row["explanation_json"])
            records.append(
                PortfolioResult(
                    portfolio_name=str(row["portfolio_name"]),
                    portfolio_type=str(row["portfolio_type"]),
                    themes=[
                        PortfolioAllocation(
                            theme=str(item.get("theme", "")),
                            theme_id=str(item.get("theme_id", "")),
                            weight=clamp_score(item.get("weight", 0.0)),
                            allocation_rationale=str(item.get("allocation_rationale", "")),
                        )
                        for item in self._json_list(row["theme_weights_json"])
                    ],
                    risk_profile=str(row["risk_profile"]),
                    lifecycle_mix={key: clamp_score(value) for key, value in self._json_dict(row["lifecycle_mix_json"]).items() if isinstance(value, (int, float))},
                    bubble_exposure=clamp_score(row["bubble_exposure"]),
                    portfolio_score=clamp_score(row["portfolio_score"]),
                    allocation_quality=clamp_score(row["allocation_quality"]),
                    diversification_score=clamp_score(row["diversification_score"]),
                    risk_score=clamp_score(row["risk_score"]),
                    lifecycle_balance=clamp_score(explanation.get("lifecycle_balance", 0.0)),
                    constraints=self._json_dict(row["constraints_json"]),
                    why_selected=[str(item) for item in explanation.get("why_selected", []) if isinstance(item, str)],
                    why_excluded=[str(item) for item in explanation.get("why_excluded", []) if isinstance(item, str)],
                    risk_sources=[str(item) for item in explanation.get("risk_sources", []) if isinstance(item, str)],
                    bubble_sources=[str(item) for item in explanation.get("bubble_sources", []) if isinstance(item, str)],
                    diversification_notes=[str(item) for item in explanation.get("diversification_notes", []) if isinstance(item, str)],
                    updated_at=str(row["updated_at"]),
                )
            )
        return records

    def update_lifecycle(self, theme_name: str, lifecycle_result: dict[str, Any]) -> None:
        stage = validate_lifecycle_stage(lifecycle_result.get("lifecycle_stage"))
        next_stage = validate_lifecycle_stage(lifecycle_result.get("expected_next_stage"), expected_next_stage(stage))
        confidence = clamp_score(lifecycle_result.get("lifecycle_confidence"))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE theme_scores
                SET lifecycle_stage = ?,
                    lifecycle_confidence = ?,
                    expected_next_stage = ?,
                    updated_at = COALESCE(?, updated_at)
                WHERE theme_name = ?
                """,
                (stage, confidence, next_stage, lifecycle_result.get("updated_at"), theme_name),
            )
            conn.commit()

    def get_lifecycle(self, theme_name: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT theme_name, lifecycle_stage, lifecycle_confidence, expected_next_stage, score_history_json
                FROM theme_scores
                WHERE theme_name = ?
                """,
                (theme_name,),
            ).fetchone()
        if row is None:
            return None
        return {
            "theme_name": row["theme_name"],
            "lifecycle_stage": validate_lifecycle_stage(row["lifecycle_stage"]),
            "lifecycle_confidence": clamp_score(row["lifecycle_confidence"]),
            "expected_next_stage": validate_lifecycle_stage(row["expected_next_stage"]),
            "history": parse_score_history(row["score_history_json"]),
        }

    def append_score_history(self, theme_name: str, snapshot: dict[str, Any]) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT score_history_json FROM theme_scores WHERE theme_name = ?",
                (theme_name,),
            ).fetchone()
            current = str(row["score_history_json"] or "[]") if row else "[]"
            updated = append_lifecycle_snapshot(current, snapshot)
            conn.execute(
                """
                UPDATE theme_scores
                SET score_history_json = ?
                WHERE theme_name = ?
                """,
                (updated, theme_name),
            )
            conn.commit()
        return updated

    def get_score_history(self, theme_name: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT score_history_json FROM theme_scores WHERE theme_name = ?",
                (theme_name,),
            ).fetchone()
        return parse_score_history(str(row["score_history_json"] or "[]")) if row else []

    @staticmethod
    def _json_list(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        try:
            parsed = json.loads(str(value or "[]"))
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        return [item for item in parsed if isinstance(item, dict)]

    @staticmethod
    def _json_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        try:
            parsed = json.loads(str(value or "{}"))
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _score_row(row: sqlite3.Row) -> dict:
        mention_count = int(row["mention_count"])
        return {
            "name": row["theme_name"],
            "mention_score": clamp_score(mention_count),
            "velocity_score": clamp_score(row["news_velocity"]),
            "sentiment_score": clamp_score(row["sentiment_score"], 50.0),
            "attention_score": clamp_score(row["attention_score"]),
            "capital_flow_score": clamp_score(row["capital_flow_score"]),
            "lifecycle_stage": validate_lifecycle_stage(row["lifecycle_stage"]),
            "lifecycle_confidence": clamp_score(row["lifecycle_confidence"]),
            "expected_next_stage": validate_lifecycle_stage(row["expected_next_stage"]),
            "total_score": clamp_score(row["total_score"]),
            "updated_at": row["updated_at"],
        }
