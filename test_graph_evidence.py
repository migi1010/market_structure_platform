from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.graph_models import IndustrialGraphBuild, IndustrialGraphEvidence
from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository
from theme_intelligence.industrial_graph.graph_validator import GraphValidationError, GraphValidator
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_evidence_hash_and_identity_are_deterministic() -> None:
    first = IndustrialGraphEvidence.from_payload(
        source_type="phase10:bottleneck",
        source_record_id="hbm:stacking_yield",
        citation="Persisted bottleneck evidence.",
        payload={"strength": 68, "name": "Stacking Yield"},
    )
    second = IndustrialGraphEvidence.from_payload(
        source_type="phase10:bottleneck",
        source_record_id="hbm:stacking_yield",
        citation="Persisted bottleneck evidence.",
        payload={"name": "Stacking Yield", "strength": 68},
    )
    assert first.content_hash == second.content_hash
    assert first.identity_key == second.identity_key


def test_repository_reuses_evidence_and_validator_rejects_build_duplicates(tmp_path: Path) -> None:
    repository = IndustrialGraphRepository(ThemeRepository(tmp_path / "graph.sqlite3"))
    evidence = IndustrialGraphEvidence.from_payload(
        "seed:curated",
        "hbm:controller:MU",
        "Curated controller evidence.",
        {"ticker": "MU"},
    )
    with repository.connect() as conn:
        first = repository.resolve_evidence(conn, [evidence])
        second = repository.resolve_evidence(conn, [evidence])
        conn.commit()
    assert first[evidence.identity_key] == second[evidence.identity_key]

    with pytest.raises(GraphValidationError, match="duplicate evidence"):
        GraphValidator().validate(IndustrialGraphBuild(evidence=(evidence, evidence)))

