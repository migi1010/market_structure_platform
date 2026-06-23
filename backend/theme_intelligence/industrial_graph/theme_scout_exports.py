from __future__ import annotations

from .theme_scout_repository import ThemeScoutRepository


def export_theme_scout_snapshot(
    repository: ThemeScoutRepository,
    scout_version: str | None = None,
) -> dict:
    snapshot = (
        repository.get_snapshot(scout_version)
        if scout_version
        else repository.get_active_snapshot()
    )
    if snapshot is None:
        return {"available": False, "snapshot": None, "candidates": []}
    return {
        "available": True,
        "snapshot": {
            "scout_version": snapshot.scout_version,
            "algorithm_version": snapshot.algorithm_version,
            "provider_name": snapshot.provider_name,
            "provider_model": snapshot.provider_model,
            "prompt_version": snapshot.prompt_version,
            "source_watermark": snapshot.source_watermark,
            "evidence_bundle_checksum": snapshot.evidence_bundle_checksum,
            "proposal_checksum": snapshot.proposal_checksum,
            "checksum": snapshot.checksum,
            "candidate_count": snapshot.candidate_count,
            "status": snapshot.status,
            "activated_at": snapshot.activated_at,
            "created_at": snapshot.created_at,
        },
        "candidates": [row.to_dict() for row in repository.list_candidates(snapshot.scout_version)],
    }


def export_theme_candidate(
    repository: ThemeScoutRepository,
    candidate_key: str,
    scout_version: str | None = None,
) -> dict | None:
    candidate = repository.get_candidate(candidate_key, scout_version)
    return candidate.to_dict() if candidate else None
