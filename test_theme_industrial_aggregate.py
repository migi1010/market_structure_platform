from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.aggregate import ThemeIntelligenceAggregateService
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


@pytest.fixture(scope="module")
def aggregate(tmp_path_factory: pytest.TempPathFactory) -> ThemeIntelligenceAggregateService:
    repository = ThemeRepository(tmp_path_factory.mktemp("aggregate") / "theme.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False)
    return ThemeIntelligenceAggregateService(repository=repository)


def test_cpo_aggregate_uses_backend_canonical_identity(
    aggregate: ThemeIntelligenceAggregateService,
) -> None:
    payload = aggregate.get_theme("cpo")

    assert payload["theme_id"] == "cpo_photonics"
    assert payload["name"] == "CPO Photonics"
    assert payload["industrial_intelligence"]["graph"]["nodes"]
    assert payload["industrial_intelligence"]["identity"]["canonical_theme_key"] == "cpo_photonics"


@pytest.mark.parametrize(
    ("theme_value", "canonical"),
    [
        ("HBM", "hbm"),
        ("CoWoS", "cowos"),
        ("Glass Substrate", "glass_substrate"),
        ("CPO", "cpo_photonics"),
        ("AI Infrastructure", "ai_infrastructure"),
        ("Data Center Cooling", "data_center_cooling"),
    ],
)
def test_aggregate_additively_exposes_industrial_intelligence(
    aggregate: ThemeIntelligenceAggregateService,
    theme_value: str,
    canonical: str,
) -> None:
    payload = aggregate.get_theme(theme_value)

    assert payload["theme_id"] == canonical
    assert payload["industrial_intelligence"]["identity"]["canonical_theme_key"] == canonical
    assert payload["industrial_intelligence"]["graph"]["nodes"]
    assert payload["industrial_intelligence"]["graph"]["edges"]
    assert payload["industrial_intelligence"]["constraints"]
    assert set(payload) >= {
        "score",
        "discovery",
        "lifecycle",
        "catalysts",
        "bottlenecks",
        "beneficiaries",
        "portfolio_context",
        "supply_chain",
        "relationship_intelligence",
        "industrial_intelligence",
    }


def test_legacy_supply_dependency_paths_use_evidenced_graph_paths(
    aggregate: ThemeIntelligenceAggregateService,
) -> None:
    payload = aggregate.get_theme("hbm")

    assert payload["supply_chain"]["dependency_paths"]
    assert all(row["path"] for row in payload["supply_chain"]["dependency_paths"])
    assert all("explanation" not in row for row in payload["supply_chain"]["dependency_paths"])
