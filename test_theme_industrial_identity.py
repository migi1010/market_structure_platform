from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from theme_intelligence.industrial_graph.theme_industrial_projection import (
    CanonicalThemeResolver,
)
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.storage.theme_repository import ThemeRepository


@pytest.fixture(scope="module")
def resolver(tmp_path_factory: pytest.TempPathFactory) -> CanonicalThemeResolver:
    repository = ThemeRepository(tmp_path_factory.mktemp("identity") / "theme.sqlite3")
    ThemeSeedLoader(repository=repository).load(recompute=False)
    return CanonicalThemeResolver(repository)


@pytest.mark.parametrize(
    ("value", "canonical_key", "display_name"),
    [
        ("HBM", "hbm", "HBM"),
        ("CoWoS", "cowos", "CoWoS"),
        ("Glass Substrate", "glass_substrate", "Glass Substrate"),
        ("CPO", "cpo_photonics", "CPO Photonics"),
        ("CPO Photonics", "cpo_photonics", "CPO Photonics"),
        ("Co-Packaged Optics", "cpo_photonics", "CPO Photonics"),
        ("AI Infrastructure", "ai_infrastructure", "AI Infrastructure"),
        ("Data Center Cooling", "data_center_cooling", "Data Center Cooling"),
    ],
)
def test_resolver_returns_graph_canonical_theme(
    resolver: CanonicalThemeResolver,
    value: str,
    canonical_key: str,
    display_name: str,
) -> None:
    identity = resolver.resolve(value)
    assert identity.canonical_theme_key == canonical_key
    assert identity.display_name == display_name
    assert identity.resolution_state in {"canonical", "alias"}


def test_resolver_does_not_match_unknown_theme_by_substring(
    resolver: CanonicalThemeResolver,
) -> None:
    identity = resolver.resolve("CPO Adjacent Speculation")
    assert identity.canonical_theme_key == "cpo_adjacent_speculation"
    assert identity.resolution_state == "unresolved"

