from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_builder import ThemeScoutBuilder
from theme_intelligence.industrial_graph.theme_scout_llm_provider import ThemeScoutLLMProvider
from theme_intelligence.industrial_graph.theme_scout_manifest import ThemeScoutEvidenceManifest
from theme_intelligence.industrial_graph.theme_scout_models import ScoutEvidence


class PayloadClient:
    provider_name = "mock-llm"
    provider_model = "mock-model"

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def generate_json(self, prompt: str, evidence_manifest: ThemeScoutEvidenceManifest) -> dict[str, Any]:
        del prompt, evidence_manifest
        return self.payload


def _manifest(*, citation: str = "Approved evidence") -> ThemeScoutEvidenceManifest:
    evidence = ScoutEvidence(
        evidence_id="graph_evidence:1",
        source_table="graph_evidence",
        source_record_id="1",
        source_type="research",
        source_timestamp="2026-06-20T00:00:00+00:00",
        source_identifier="record-1",
        citation=citation,
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


def _payload(**candidate_updates: Any) -> dict[str, Any]:
    candidate = {
        "name": "AI Power Grid",
        "description": "Hypothesis generated from frozen evidence only.",
        "status": "DISCOVERED",
        "evidence_ids": ["graph_evidence:1"],
        "signal_clusters": [],
        "paths": [],
        "influence_map": [],
        "bottleneck_evidence_ids": [],
        "generated_summary": "",
    }
    candidate.update(candidate_updates)
    return {
        "schema_version": "theme-scout-proposal-v1",
        "mode": "dry_run",
        "provider": {"name": "mock-llm", "model": "mock-model", "prompt_version": "theme-scout-llm-v1"},
        "graph_build_version": "industrial-active",
        "evidence_bundle_checksum": "bundle-checksum",
        "review": {"reviewed": False, "reviewed_by": "", "reviewed_at": "", "reason": ""},
        "candidates": [candidate],
    }


def test_unknown_evidence_id_is_rejected_by_existing_builder() -> None:
    document = ThemeScoutLLMProvider(PayloadClient(_payload(evidence_ids=["graph_evidence:999"]))).build_proposal(_manifest())
    with pytest.raises(ValueError, match="unknown proposal evidence reference"):
        ThemeScoutBuilder().build(_manifest().evidence, document.proposal, _manifest().source_watermark)


@pytest.mark.parametrize("field", ["evidence", "recommendation", "target_price", "rating", "buy_sell_hold"])
def test_forbidden_or_unsupported_candidate_fields_are_rejected(field: str) -> None:
    with pytest.raises(ValueError, match="unsupported proposal fields"):
        ThemeScoutLLMProvider(PayloadClient(_payload(**{field: "forbidden"}))).build_proposal(_manifest())


def test_invalid_lifecycle_is_rejected() -> None:
    with pytest.raises(ValueError, match="DISCOVERED"):
        ThemeScoutLLMProvider(PayloadClient(_payload(status="APPROVED"))).build_proposal(_manifest())


def test_empty_citation_is_rejected_before_llm_generation() -> None:
    with pytest.raises(ValueError, match="citation is required"):
        _manifest(citation="")
