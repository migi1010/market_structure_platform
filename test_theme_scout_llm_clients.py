from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_llm_clients import (
    AnthropicThemeScoutClient,
    GeminiThemeScoutClient,
    LLMThemeScoutClient,
    OpenAIThemeScoutClient,
)
from theme_intelligence.industrial_graph.theme_scout_manifest import ThemeScoutEvidenceManifest
from theme_intelligence.industrial_graph.theme_scout_models import ScoutEvidence


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


def test_clients_share_common_interface() -> None:
    assert issubclass(OpenAIThemeScoutClient, LLMThemeScoutClient)
    assert issubclass(AnthropicThemeScoutClient, LLMThemeScoutClient)
    assert issubclass(GeminiThemeScoutClient, LLMThemeScoutClient)


def test_missing_api_key_fails_clearly() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIThemeScoutClient(api_key="")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicThemeScoutClient(api_key="")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiThemeScoutClient(api_key="")


def test_openai_mock_transport_returns_deterministic_json() -> None:
    calls: list[dict] = []

    def transport(url: str, headers: dict, payload: dict, timeout: float) -> dict:
        calls.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        return {"choices": [{"message": {"content": json.dumps({"ok": True, "vendor": "openai"})}}]}

    client = OpenAIThemeScoutClient(api_key="key", model="gpt-test", transport=transport)
    result = client.generate_json("Return JSON", _manifest())
    assert result == {"ok": True, "vendor": "openai"}
    assert calls[0]["payload"]["model"] == "gpt-test"
    assert calls[0]["payload"]["evidence"] == [_manifest().evidence[0].to_dict()]


def test_anthropic_and_gemini_mock_transports_parse_vendor_shapes() -> None:
    anthropic = AnthropicThemeScoutClient(
        api_key="key",
        model="claude-test",
        transport=lambda *_: {"content": [{"type": "text", "text": json.dumps({"vendor": "anthropic"})}]},
    )
    gemini = GeminiThemeScoutClient(
        api_key="key",
        model="gemini-test",
        transport=lambda *_: {"candidates": [{"content": {"parts": [{"text": json.dumps({"vendor": "gemini"})}]}}]},
    )

    assert anthropic.generate_json("Return JSON", _manifest()) == {"vendor": "anthropic"}
    assert gemini.generate_json("Return JSON", _manifest()) == {"vendor": "gemini"}
