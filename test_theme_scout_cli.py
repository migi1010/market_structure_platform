from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_scout_cli import main
from test_theme_scout_manifest import _seed_graph
from test_theme_scout_providers import proposal_payload
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_cli_exports_and_validates_dry_run(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "cli.sqlite3"
    repository = ThemeRepository(db_path)
    _seed_graph(repository)
    manifest_path = tmp_path / "manifest.json"
    assert main([
        "--db", str(db_path), "export-evidence", "--output", str(manifest_path)
    ]) == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    proposal = proposal_payload(mode="dry_run", candidates=[])
    proposal["graph_build_version"] = manifest["graph_build_version"]
    proposal["evidence_bundle_checksum"] = manifest["evidence_bundle_checksum"]
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
    assert main([
        "--db", str(db_path), "validate-proposal",
        "--manifest", str(manifest_path), "--proposal", str(proposal_path),
    ]) == 0
    assert '"valid": true' in capsys.readouterr().out.lower()


def test_cli_refuses_to_activate_empty_dry_run(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.sqlite3"
    repository = ThemeRepository(db_path)
    _seed_graph(repository)
    manifest_path = tmp_path / "manifest.json"
    assert main([
        "--db", str(db_path), "export-evidence", "--output", str(manifest_path)
    ]) == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    proposal = proposal_payload(mode="dry_run", candidates=[])
    proposal["graph_build_version"] = manifest["graph_build_version"]
    proposal["evidence_bundle_checksum"] = manifest["evidence_bundle_checksum"]
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
    with pytest.raises(ValueError, match="production"):
        main([
            "--db", str(db_path), "activate",
            "--manifest", str(manifest_path),
            "--proposal", str(proposal_path),
        ])


def test_cli_dry_run_accepts_reviewed_production_proposal(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "production-dry-run.sqlite3"
    repository = ThemeRepository(db_path)
    _seed_graph(repository)
    manifest_path = tmp_path / "manifest.json"
    assert main([
        "--db", str(db_path), "export-evidence", "--output", str(manifest_path)
    ]) == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    proposal = proposal_payload()
    proposal["graph_build_version"] = manifest["graph_build_version"]
    proposal["evidence_bundle_checksum"] = manifest["evidence_bundle_checksum"]
    proposal["candidates"][0]["evidence_ids"] = [manifest["evidence"][0]["evidence_id"]]
    proposal_path = tmp_path / "production.json"
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
    assert main([
        "--db", str(db_path), "dry-run",
        "--manifest", str(manifest_path), "--proposal", str(proposal_path),
    ]) == 0
    assert '"mode": "production"' in capsys.readouterr().out
