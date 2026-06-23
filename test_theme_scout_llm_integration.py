from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from test_theme_scout_manifest import _seed_graph

from theme_intelligence.industrial_graph.theme_scout_cli import main
from theme_intelligence.industrial_graph.theme_scout_isolation import downstream_fingerprint
from theme_intelligence.industrial_graph.theme_scout_llm_clients import StaticLLMThemeScoutClient
from theme_intelligence.industrial_graph.theme_scout_llm_provider import ThemeScoutLLMProvider
from theme_intelligence.industrial_graph.theme_scout_manifest import export_active_graph_evidence_manifest
from theme_intelligence.industrial_graph.theme_scout_repository import ThemeScoutRepository
from theme_intelligence.storage.theme_repository import ThemeRepository


def _llm_payload(evidence_id: str, graph_build_version: str, checksum: str, *, mode: str = "dry_run") -> dict[str, Any]:
    return {
        "schema_version": "theme-scout-proposal-v1",
        "mode": mode,
        "provider": {"name": "mock-llm", "model": "mock-model", "prompt_version": "theme-scout-llm-v1"},
        "graph_build_version": graph_build_version,
        "evidence_bundle_checksum": checksum,
        "review": {
            "reviewed": mode == "production",
            "reviewed_by": "research-reviewer" if mode == "production" else "",
            "reviewed_at": "2026-06-20T00:00:00+00:00" if mode == "production" else "",
            "reason": "Reviewed live LLM proposal." if mode == "production" else "",
        },
        "candidates": [{
            "name": "AI Power Grid",
            "description": "Constraint-watch candidate generated from frozen graph evidence.",
            "status": "DISCOVERED",
            "evidence_ids": [evidence_id],
            "signal_clusters": [{
                "cluster_key": "power-infrastructure",
                "label": "Power Infrastructure",
                "evidence_ids": [evidence_id],
            }],
            "paths": [],
            "influence_map": [],
            "bottleneck_evidence_ids": [evidence_id],
            "generated_summary": "",
        }],
    }


def test_llm_proposal_builds_and_activation_requires_reviewed_production_json(tmp_path: Path) -> None:
    db_path = tmp_path / "llm-integration.sqlite3"
    repository = ThemeRepository(db_path)
    _seed_graph(repository)
    manifest = export_active_graph_evidence_manifest(repository)
    evidence_id = manifest.evidence[0].evidence_id
    proposal_document = ThemeScoutLLMProvider(
        StaticLLMThemeScoutClient(_llm_payload(evidence_id, manifest.graph_build_version, manifest.evidence_bundle_checksum))
    ).build_proposal(manifest)

    from theme_intelligence.industrial_graph.theme_scout_engine import ThemeScoutEngine

    engine = ThemeScoutEngine(repository, provider=ThemeScoutLLMProvider(
        StaticLLMThemeScoutClient(proposal_document.to_dict())
    ))
    build = engine.build(manifest=manifest)
    assert build.candidates[0].name == "AI Power Grid"

    manifest_path = tmp_path / "manifest.json"
    proposal_path = tmp_path / "proposal.json"
    manifest_path.write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
    proposal_path.write_text(json.dumps(proposal_document.to_dict()), encoding="utf-8")
    with pytest.raises(ValueError, match="production"):
        main(["--db", str(db_path), "activate", "--manifest", str(manifest_path), "--proposal", str(proposal_path)])

    production = _llm_payload(evidence_id, manifest.graph_build_version, manifest.evidence_bundle_checksum, mode="production")
    proposal_path.write_text(json.dumps(production), encoding="utf-8")
    before = downstream_fingerprint(repository)
    assert main(["--db", str(db_path), "activate", "--manifest", str(manifest_path), "--proposal", str(proposal_path)]) == 0
    after = downstream_fingerprint(repository)
    assert after == before
    active = ThemeScoutRepository(repository).get_active_snapshot()
    assert active is not None
    assert active.candidate_count == 1


def test_cli_generate_llm_proposal_writes_json_without_activation(tmp_path: Path) -> None:
    db_path = tmp_path / "llm-cli.sqlite3"
    repository = ThemeRepository(db_path)
    _seed_graph(repository)
    manifest = export_active_graph_evidence_manifest(repository)
    manifest_path = tmp_path / "manifest.json"
    output_path = tmp_path / "llm-proposal.json"
    manifest_path.write_text(json.dumps(manifest.to_dict()), encoding="utf-8")

    assert main([
        "--db", str(db_path),
        "generate-llm-proposal",
        "--manifest", str(manifest_path),
        "--provider", "static",
        "--static-response", json.dumps(_llm_payload(
            manifest.evidence[0].evidence_id,
            manifest.graph_build_version,
            manifest.evidence_bundle_checksum,
        )),
        "--output", str(output_path),
    ]) == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["candidates"][0]["name"] == "AI Power Grid"
    assert ThemeScoutRepository(repository).get_active_snapshot() is None
