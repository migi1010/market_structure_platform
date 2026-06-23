from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_llm_provider import (
    LLM_SCOUT_PROMPT_VERSION,
    ThemeScoutLLMProvider,
)
from theme_intelligence.industrial_graph.theme_scout_manifest import ThemeScoutEvidenceManifest
from theme_intelligence.industrial_graph.theme_scout_models import ScoutEvidence


class CapturingClient:
    provider_name = "mock-llm"
    provider_model = "mock-model"

    def __init__(self) -> None:
        self.prompt = ""
        self.manifest: ThemeScoutEvidenceManifest | None = None

    def generate_json(self, prompt: str, evidence_manifest: ThemeScoutEvidenceManifest) -> dict[str, Any]:
        self.prompt = prompt
        self.manifest = evidence_manifest
        evidence_id = evidence_manifest.evidence[0].evidence_id
        return {
            "schema_version": "theme-scout-proposal-v1",
            "mode": "dry_run",
            "provider": {
                "name": self.provider_name,
                "model": self.provider_model,
                "prompt_version": LLM_SCOUT_PROMPT_VERSION,
            },
            "graph_build_version": evidence_manifest.graph_build_version,
            "evidence_bundle_checksum": evidence_manifest.evidence_bundle_checksum,
            "review": {"reviewed": False, "reviewed_by": "", "reviewed_at": "", "reason": ""},
            "candidates": [{
                "name": "AI Power Grid",
                "description": "Hypothesis generated from frozen evidence only.",
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


def _manifest() -> ThemeScoutEvidenceManifest:
    evidence = ScoutEvidence(
        evidence_id="graph_evidence:1",
        source_table="graph_evidence",
        source_record_id="1",
        source_type="research",
        source_timestamp="2026-06-20T00:00:00+00:00",
        source_identifier="record-1",
        citation="Approved evidence",
        domain_type="Constraint",
        cluster_key="constraint",
        source_value={"endpoint": "constraint:test"},
        content_hash="hash-1",
    )
    return ThemeScoutEvidenceManifest(
        schema_version="theme-scout-evidence-manifest-v1",
        graph_build_version="industrial-active",
        graph_checksum="graph-checksum",
        source_watermark="2026-06-20T00:00:00+00:00",
        evidence_bundle_checksum="bundle-checksum",
        evidence=(evidence,),
    )


def test_llm_provider_receives_only_frozen_manifest_evidence() -> None:
    client = CapturingClient()
    document = ThemeScoutLLMProvider(client).build_proposal(_manifest())
    assert client.manifest is not None
    assert [row.evidence_id for row in client.manifest.evidence] == ["graph_evidence:1"]
    assert "graph-checksum" not in client.prompt
    assert "previous snapshot" not in client.prompt.lower()
    assert document.schema_version == "theme-scout-proposal-v1"


def test_llm_provider_emits_existing_schema_with_discovered_candidates() -> None:
    document = ThemeScoutLLMProvider(CapturingClient()).build_proposal(_manifest())
    assert document.proposal.provider_name == "mock-llm"
    assert document.proposal.provider_model == "mock-model"
    assert document.proposal.prompt_version == LLM_SCOUT_PROMPT_VERSION
    assert document.proposal.candidates[0].name == "AI Power Grid"
    assert document.proposal.candidates[0].status == "DISCOVERED"
