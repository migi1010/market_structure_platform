from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from theme_intelligence.storage.theme_repository import ThemeRepository
from settings import get_settings

from .theme_scout_engine import ThemeScoutEngine
from .theme_scout_isolation import downstream_fingerprint
from .theme_scout_llm_clients import (
    AnthropicThemeScoutClient,
    GeminiThemeScoutClient,
    OpenAIThemeScoutClient,
    StaticLLMThemeScoutClient,
)
from .theme_scout_llm_provider import ThemeScoutLLMProvider
from .theme_scout_manifest import (
    ThemeScoutEvidenceManifest,
    export_active_graph_evidence_manifest,
    load_evidence_manifest,
    write_evidence_manifest,
)
from .theme_scout_providers import OfflineFileThemeScoutProposalProvider


def _write(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _assert_manifest_is_current(
    repository: ThemeRepository, manifest: ThemeScoutEvidenceManifest
) -> None:
    current = export_active_graph_evidence_manifest(repository)
    if current.graph_build_version != manifest.graph_build_version:
        raise ValueError("manifest graph build version is not active")
    if current.graph_checksum != manifest.graph_checksum:
        raise ValueError("manifest graph checksum mismatch")
    if current.evidence_bundle_checksum != manifest.evidence_bundle_checksum:
        raise ValueError("manifest evidence checksum mismatch")


def _load_build(
    repository: ThemeRepository,
    manifest_path: str,
    proposal_path: str,
):
    manifest = load_evidence_manifest(manifest_path)
    _assert_manifest_is_current(repository, manifest)
    provider = OfflineFileThemeScoutProposalProvider(proposal_path)
    engine = ThemeScoutEngine(repository, provider=provider)
    build = engine.build(manifest=manifest)
    return manifest, provider, engine, build


def _audit(manifest, provider, build) -> dict:
    return {
        "valid": True,
        "mode": provider.document.mode,
        "reviewed": provider.document.review.reviewed,
        "graph_build_version": manifest.graph_build_version,
        "graph_checksum": manifest.graph_checksum,
        "source_watermark": manifest.source_watermark,
        "evidence_count": len(manifest.evidence),
        "evidence_bundle_checksum": build.evidence_bundle_checksum,
        "proposal_file_checksum": provider.file_checksum,
        "proposal_checksum": build.proposal_checksum,
        "build_checksum": build.checksum,
        "candidate_count": len(build.candidates),
        "candidate_keys": [row.candidate_key for row in build.candidates],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Theme Scout offline proposal workflow")
    parser.add_argument("--db", default=None, help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export-evidence")
    export.add_argument("--output", required=True)

    generate = subparsers.add_parser("generate-llm-proposal")
    generate.add_argument("--manifest", required=True)
    generate.add_argument("--output", required=True)
    generate.add_argument("--provider", default=None, choices=("openai", "anthropic", "gemini", "static"))
    generate.add_argument("--model", default=None)
    generate.add_argument("--static-response", default=None)

    for command in ("validate-proposal", "build", "dry-run", "activate"):
        child = subparsers.add_parser(command)
        child.add_argument("--manifest", required=True)
        child.add_argument("--proposal", required=True)

    subparsers.add_parser("verify-isolation")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository = ThemeRepository(Path(args.db).resolve()) if args.db else ThemeRepository()

    if args.command == "export-evidence":
        manifest = export_active_graph_evidence_manifest(repository)
        write_evidence_manifest(manifest, args.output)
        _write({
            "exported": True,
            "output": str(Path(args.output).resolve()),
            "graph_build_version": manifest.graph_build_version,
            "graph_checksum": manifest.graph_checksum,
            "evidence_count": len(manifest.evidence),
            "evidence_bundle_checksum": manifest.evidence_bundle_checksum,
        })
        return 0

    if args.command == "verify-isolation":
        fingerprint = downstream_fingerprint(repository)
        _write({"isolated": True, "tables": fingerprint})
        return 0

    if args.command == "generate-llm-proposal":
        manifest = load_evidence_manifest(args.manifest)
        _assert_manifest_is_current(repository, manifest)
        provider_name = (args.provider or get_settings().theme_scout_llm_provider).strip().lower()
        model = args.model or get_settings().theme_scout_llm_model
        if provider_name == "static":
            if not args.static_response:
                raise ValueError("--static-response is required for static LLM provider")
            client = StaticLLMThemeScoutClient(json.loads(args.static_response))
        elif provider_name == "openai":
            client = OpenAIThemeScoutClient(
                api_key=get_settings().openai_api_key,
                model=model or "gpt-4.1",
                timeout=get_settings().provider_timeout_seconds,
            )
        elif provider_name == "anthropic":
            client = AnthropicThemeScoutClient(
                api_key=get_settings().anthropic_api_key,
                model=model or "claude-3-5-sonnet-latest",
                timeout=get_settings().provider_timeout_seconds,
            )
        elif provider_name == "gemini":
            client = GeminiThemeScoutClient(
                api_key=get_settings().gemini_api_key,
                model=model or "gemini-1.5-pro",
                timeout=get_settings().provider_timeout_seconds,
            )
        else:
            raise ValueError(f"unsupported LLM Scout provider: {provider_name}")
        document = ThemeScoutLLMProvider(client).build_proposal(manifest)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(document.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write({
            "generated": True,
            "output": str(output.resolve()),
            "provider": document.proposal.provider_name,
            "model": document.proposal.provider_model,
            "prompt_version": document.proposal.prompt_version,
            "mode": document.mode,
            "candidate_count": len(document.proposal.candidates),
            "proposal_checksum": document.checksum,
            "activated": False,
        })
        return 0

    manifest, provider, engine, build = _load_build(
        repository, args.manifest, args.proposal
    )
    audit = _audit(manifest, provider, build)

    if args.command in {"validate-proposal", "build", "dry-run"}:
        _write(audit)
        return 0

    if provider.document.mode != "production":
        raise ValueError("activation requires a production proposal")
    if not provider.document.is_production_ready:
        raise ValueError("activation requires a reviewed non-empty proposal")
    staged = engine.repository.stage(build)
    active = engine.repository.activate_guarded(staged.scout_version)
    _write({
        **audit,
        "activated": True,
        "scout_version": active.scout_version,
        "status": active.status,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
