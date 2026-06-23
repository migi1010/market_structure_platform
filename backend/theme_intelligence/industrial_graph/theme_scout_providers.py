from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .theme_scout_models import (
    ScoutEvidence,
    ThemeCandidateInfluence,
    ThemeScoutPath,
    ThemeScoutProposal,
    ThemeScoutProposalCandidate,
    ThemeScoutSignalCluster,
)
from .graph_models import content_hash


PROPOSAL_SCHEMA_VERSION = "theme-scout-proposal-v1"
PROPOSAL_MODES = frozenset({"production", "dry_run"})


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _strict(value: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"unsupported {label} fields: {', '.join(unknown)}")


def _text(value: Any, label: str, *, required: bool = True) -> str:
    parsed = str(value or "").strip()
    if required and not parsed:
        raise ValueError(f"{label} is required")
    return parsed


@dataclass(frozen=True)
class ProposalReview:
    reviewed: bool
    reviewed_by: str
    reviewed_at: str
    reason: str


@dataclass(frozen=True)
class ThemeScoutProposalDocument:
    schema_version: str
    mode: str
    graph_build_version: str
    evidence_bundle_checksum: str
    review: ProposalReview
    proposal: ThemeScoutProposal

    @property
    def is_production_ready(self) -> bool:
        return (
            self.mode == "production"
            and self.review.reviewed
            and bool(self.proposal.candidates)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "provider": {
                "name": self.proposal.provider_name,
                "model": self.proposal.provider_model,
                "prompt_version": self.proposal.prompt_version,
            },
            "graph_build_version": self.graph_build_version,
            "evidence_bundle_checksum": self.evidence_bundle_checksum,
            "review": {
                "reviewed": self.review.reviewed,
                "reviewed_by": self.review.reviewed_by,
                "reviewed_at": self.review.reviewed_at,
                "reason": self.review.reason,
            },
            "candidates": self.proposal.to_dict()["candidates"],
        }

    @property
    def checksum(self) -> str:
        return content_hash(self.to_dict())


def _parse_cluster(value: Any) -> ThemeScoutSignalCluster:
    row = _object(value, "signal cluster")
    _strict(row, {"cluster_key", "label", "evidence_ids"}, "signal cluster")
    return ThemeScoutSignalCluster(
        cluster_key=_text(row.get("cluster_key"), "cluster_key"),
        label=_text(row.get("label"), "cluster label"),
        evidence_ids=tuple(_text(item, "cluster evidence id") for item in _list(row.get("evidence_ids", []), "cluster evidence_ids")),
    )


def _parse_path(value: Any) -> ThemeScoutPath:
    row = _object(value, "path")
    _strict(row, {"path_type", "label", "evidence_ids", "steps"}, "path")
    parsed_steps = []
    for item in _list(row.get("steps", []), "path steps"):
        step = _object(item, "path step")
        _strict(
            step,
            {
                "label", "timestamp", "evidence_ids", "state", "target_type",
                "target_label", "action", "cluster_key",
            },
            "path step",
        )
        parsed_steps.append(step)
    steps = tuple(parsed_steps)
    return ThemeScoutPath(
        path_type=_text(row.get("path_type"), "path_type"),
        label=_text(row.get("label"), "path label"),
        evidence_ids=tuple(_text(item, "path evidence id") for item in _list(row.get("evidence_ids", []), "path evidence_ids")),
        steps=steps,
    )


def _parse_influence(value: Any) -> ThemeCandidateInfluence:
    row = _object(value, "influence")
    _strict(
        row,
        {"target_type", "target_label", "evidence_ids", "cluster_keys", "hypothesis_state"},
        "influence",
    )
    return ThemeCandidateInfluence(
        target_type=_text(row.get("target_type"), "influence target_type"),
        target_label=_text(row.get("target_label"), "influence target_label"),
        evidence_ids=tuple(_text(item, "influence evidence id") for item in _list(row.get("evidence_ids", []), "influence evidence_ids")),
        cluster_keys=tuple(_text(item, "influence cluster key") for item in _list(row.get("cluster_keys", []), "influence cluster_keys")),
        hypothesis_state=_text(row.get("hypothesis_state", "hypothesis"), "hypothesis_state"),
    )


def _parse_candidate(value: Any) -> ThemeScoutProposalCandidate:
    row = _object(value, "proposal")
    _strict(
        row,
        {
            "name", "description", "status", "evidence_ids", "signal_clusters",
            "paths", "influence_map", "bottleneck_evidence_ids",
            "generated_summary",
        },
        "proposal",
    )
    return ThemeScoutProposalCandidate(
        name=_text(row.get("name"), "candidate name"),
        description=_text(row.get("description"), "candidate description"),
        status=_text(row.get("status", "DISCOVERED"), "candidate status"),
        evidence_ids=tuple(_text(item, "candidate evidence id") for item in _list(row.get("evidence_ids", []), "candidate evidence_ids")),
        signal_clusters=tuple(_parse_cluster(item) for item in _list(row.get("signal_clusters", []), "signal_clusters")),
        paths=tuple(_parse_path(item) for item in _list(row.get("paths", []), "paths")),
        influence_map=tuple(_parse_influence(item) for item in _list(row.get("influence_map", []), "influence_map")),
        bottleneck_evidence_ids=tuple(_text(item, "bottleneck evidence id") for item in _list(row.get("bottleneck_evidence_ids", []), "bottleneck_evidence_ids")),
        generated_summary=_text(row.get("generated_summary", ""), "generated_summary", required=False),
    )


def parse_proposal_document(value: Mapping[str, Any]) -> ThemeScoutProposalDocument:
    row = _object(value, "proposal document")
    _strict(
        row,
        {
            "schema_version", "mode", "provider", "graph_build_version",
            "evidence_bundle_checksum", "review", "candidates",
        },
        "document",
    )
    schema_version = _text(row.get("schema_version"), "schema_version")
    if schema_version != PROPOSAL_SCHEMA_VERSION:
        raise ValueError(f"unsupported proposal schema: {schema_version}")
    mode = _text(row.get("mode"), "mode")
    if mode not in PROPOSAL_MODES:
        raise ValueError(f"unsupported proposal mode: {mode}")

    provider = _object(row.get("provider"), "provider")
    _strict(provider, {"name", "model", "prompt_version"}, "provider")
    review_row = _object(row.get("review"), "review")
    _strict(review_row, {"reviewed", "reviewed_by", "reviewed_at", "reason"}, "review")
    review = ProposalReview(
        reviewed=review_row.get("reviewed") is True,
        reviewed_by=_text(review_row.get("reviewed_by"), "reviewed_by", required=False),
        reviewed_at=_text(review_row.get("reviewed_at"), "reviewed_at", required=False),
        reason=_text(review_row.get("reason"), "review reason", required=False),
    )
    candidates = tuple(_parse_candidate(item) for item in _list(row.get("candidates"), "candidates"))
    if mode == "production":
        if not candidates:
            raise ValueError("production proposal must be non-empty")
        if not review.reviewed or not all(
            (review.reviewed_by, review.reviewed_at, review.reason)
        ):
            raise ValueError("production proposal review metadata is required")

    return ThemeScoutProposalDocument(
        schema_version=schema_version,
        mode=mode,
        graph_build_version=_text(row.get("graph_build_version"), "graph_build_version"),
        evidence_bundle_checksum=_text(row.get("evidence_bundle_checksum"), "evidence_bundle_checksum"),
        review=review,
        proposal=ThemeScoutProposal(
            provider_name=_text(provider.get("name"), "provider name"),
            provider_model=_text(provider.get("model"), "provider model"),
            prompt_version=_text(provider.get("prompt_version"), "prompt_version"),
            candidates=candidates,
        ),
    )


def load_proposal_document(path: Path | str) -> ThemeScoutProposalDocument:
    raw = Path(path).read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid proposal JSON: {exc}") from exc
    return parse_proposal_document(_object(payload, "proposal document"))


class ManualThemeScoutProposalProvider:
    def __init__(self, document: ThemeScoutProposalDocument) -> None:
        self.document = document
        self.provider_name = document.proposal.provider_name
        self.provider_model = document.proposal.provider_model
        self.prompt_version = document.proposal.prompt_version

    def propose(self, evidence: tuple[ScoutEvidence, ...]) -> ThemeScoutProposal:
        del evidence
        return self.document.proposal


class OfflineFileThemeScoutProposalProvider(ManualThemeScoutProposalProvider):
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).resolve()
        self.file_bytes = self.path.read_bytes()
        self.file_checksum = hashlib.sha256(self.file_bytes).hexdigest()
        try:
            payload = json.loads(self.file_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid proposal JSON: {exc}") from exc
        super().__init__(parse_proposal_document(_object(payload, "proposal document")))
