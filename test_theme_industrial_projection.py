from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_industrial_projection import (
    ThemeIndustrialProjectionService,
)
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


@pytest.fixture(scope="module")
def projection(tmp_path_factory: pytest.TempPathFactory) -> ThemeIndustrialProjectionService:
    repository = ThemeRepository(tmp_path_factory.mktemp("projection") / "theme.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False)
    return ThemeIndustrialProjectionService(repository)


def test_projection_exposes_active_lineage_and_evidenced_paths(
    projection: ThemeIndustrialProjectionService,
) -> None:
    payload = projection.get_theme("glass_substrate")

    assert payload["identity"]["canonical_theme_key"] == "glass_substrate"
    assert payload["lineage"]["lineage_state"] == "complete"
    assert payload["lineage"]["graph_snapshot_id"] > 0
    assert payload["lineage"]["controller_snapshot_id"] > 0
    assert payload["lineage"]["opportunity_snapshot_id"] > 0
    assert payload["lineage"]["packet_family_revision"] > 0
    assert payload["graph"]["nodes"]
    assert payload["graph"]["edges"]
    assert payload["graph"]["evidence_count"] > 0
    assert payload["graph"]["dependency_paths"]
    assert all(path["nodes"][0]["canonical_key"] == "glass_substrate" for path in payload["graph"]["dependency_paths"])
    assert all(edge["evidence_count"] > 0 for edge in payload["graph"]["edges"])


def test_projection_filters_metrics_and_packets_through_theme_paths(
    projection: ThemeIndustrialProjectionService,
) -> None:
    payload = projection.get_theme("cpo")

    assert payload["identity"]["canonical_theme_key"] == "cpo_photonics"
    assert {row["company_key"] for row in payload["controllers"]} >= {
        "company:COHR",
        "company:TER",
    }
    assert {row["company_key"] for row in payload["opportunities"]} >= {
        "company:COHR",
        "company:TER",
    }
    assert payload["decision_packets"]["theme_packet"]["subject_key"] == "cpo_photonics"
    assert all(
        any(node["canonical_key"] == "cpo_photonics" for node in path["nodes"])
        for row in payload["controllers"]
        for path in row["reasoning_paths"]
    )


def test_ai_infrastructure_reports_truthful_downstream_gaps(
    projection: ThemeIndustrialProjectionService,
) -> None:
    payload = projection.get_theme("ai_infrastructure")
    codes = {gap["code"] for gap in payload["research_gaps"]}

    assert payload["graph"]["nodes"]
    assert payload["constraints"]
    assert payload["controllers"] == []
    assert payload["opportunities"] == []
    assert payload["decision_packets"]["theme_packet"] is None
    assert {
        "NO_CONTROLLER_EVIDENCE",
        "NO_OPPORTUNITY_EVIDENCE",
        "NO_DECISION_PACKET_EVIDENCE",
    } <= codes
    assert "NO_GRAPH_PATH" not in codes


def test_coverage_uses_reachable_observations_without_invented_targets(
    projection: ThemeIndustrialProjectionService,
) -> None:
    coverage = projection.get_theme("hbm")["coverage"]
    for name in (
        "Technology",
        "Process",
        "Material",
        "Equipment",
        "Constraint",
        "Company",
        "Evidence",
    ):
        component = coverage["components"][name]
        assert component["denominator"] >= component["numerator"] >= 0
        if component["denominator"] == 0:
            assert component["coverage"] is None
            assert component["availability_state"] == "not_applicable"
        else:
            assert component["coverage"] == pytest.approx(
                component["numerator"] / component["denominator"] * 100
            )


def test_projection_is_deterministic(
    projection: ThemeIndustrialProjectionService,
) -> None:
    assert projection.get_theme("hbm") == projection.get_theme("hbm")
