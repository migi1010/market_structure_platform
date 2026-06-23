from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_providers import (
    ManualThemeScoutProposalProvider,
    OfflineFileThemeScoutProposalProvider,
    parse_proposal_document,
)


def proposal_payload(*, mode: str = "production", candidates: list[dict] | None = None) -> dict:
    return {
        "schema_version": "theme-scout-proposal-v1",
        "mode": mode,
        "provider": {
            "name": "manual-curated",
            "model": "offline",
            "prompt_version": "manual-v1",
        },
        "graph_build_version": "industrial-test",
        "evidence_bundle_checksum": "a" * 64,
        "review": {
            "reviewed": mode == "production",
            "reviewed_by": "research-reviewer" if mode == "production" else "",
            "reviewed_at": "2026-06-14T00:00:00+00:00" if mode == "production" else "",
            "reason": "Reviewed for deterministic Scout admission." if mode == "production" else "",
        },
        "candidates": candidates if candidates is not None else [{
            "name": "Reviewed Candidate",
            "description": "A reviewed research candidate.",
            "status": "DISCOVERED",
            "evidence_ids": ["graph_evidence:1"],
            "signal_clusters": [],
            "paths": [],
            "influence_map": [],
            "bottleneck_evidence_ids": [],
            "generated_summary": "",
        }],
    }


def test_empty_dry_run_proposal_is_valid() -> None:
    document = parse_proposal_document(proposal_payload(mode="dry_run", candidates=[]))
    assert document.mode == "dry_run"
    assert document.proposal.candidates == ()


def test_empty_production_proposal_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        parse_proposal_document(proposal_payload(candidates=[]))


def test_inline_evidence_is_rejected() -> None:
    payload = proposal_payload()
    payload["candidates"][0]["evidence"] = [{"citation": "not allowed"}]
    with pytest.raises(ValueError, match="unsupported proposal fields"):
        parse_proposal_document(payload)


def test_unknown_nested_field_is_rejected() -> None:
    payload = proposal_payload()
    payload["provider"]["temperature"] = 0
    with pytest.raises(ValueError, match="unsupported provider fields"):
        parse_proposal_document(payload)


def test_unknown_path_step_field_is_rejected() -> None:
    payload = proposal_payload()
    payload["candidates"][0]["paths"] = [{
        "path_type": "THEME_EVOLUTION",
        "label": "Evolution",
        "evidence_ids": ["graph_evidence:1"],
        "steps": [{"label": "Observed", "invented_fact": "not allowed"}],
    }]
    with pytest.raises(ValueError, match="unsupported path step fields"):
        parse_proposal_document(payload)


def test_production_review_metadata_is_required() -> None:
    payload = proposal_payload()
    payload["review"]["reviewed_by"] = ""
    with pytest.raises(ValueError, match="review metadata"):
        parse_proposal_document(payload)


def test_manual_provider_returns_frozen_proposal() -> None:
    document = parse_proposal_document(proposal_payload())
    provider = ManualThemeScoutProposalProvider(document)
    assert provider.propose(()) is provider.propose(())
    assert provider.provider_name == "manual-curated"
    assert len(document.checksum) == 64


def test_offline_provider_freezes_file_and_checksum(tmp_path: Path) -> None:
    path = tmp_path / "proposal.json"
    path.write_text(json.dumps(proposal_payload()), encoding="utf-8")
    provider = OfflineFileThemeScoutProposalProvider(path)
    first = provider.propose(())
    path.write_text(json.dumps(proposal_payload(mode="dry_run", candidates=[])), encoding="utf-8")
    assert provider.propose(()) is first
    assert len(provider.file_checksum) == 64
