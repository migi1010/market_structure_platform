from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend" / "src"
THEME_RESEARCH = FRONTEND / "components" / "ThemeResearchPage.tsx"
MARKET_TREEMAP = FRONTEND / "components" / "terminal" / "MarketTreemap.tsx"
ROTATION_WORKSPACE = FRONTEND / "lib" / "rotationWorkspace.ts"
CSS = FRONTEND / "app" / "globals.css"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_rotation_layout_is_capital_flow_command_center() -> None:
    source = read(THEME_RESEARCH)
    css = read(CSS)

    assert "rotation-command-center" in source
    assert "Capital Flow Command Center" in source
    assert "rotation-command-center-grid" in css
    assert "65%" in css
    assert "35%" in css


def test_rotation_removes_duplicate_ranking_surfaces() -> None:
    source = read(THEME_RESEARCH)
    forbidden = ("Sector Ranking", "Leader Board", "Top Sector List", "<FlowRanking")

    for phrase in forbidden:
        assert phrase not in source


def test_rotation_theme_ranking_panel_is_top_five_and_click_routes_to_theme() -> None:
    source = read(THEME_RESEARCH)

    assert "DynamicThemeRotationPanel" in source
    assert "limit={5}" in source
    assert "openThemeFromRotation" in source
    assert 'setTab("command")' in source


def test_rotation_visual_states_and_label_density_rules_are_explicit() -> None:
    source = read(ROTATION_WORKSPACE)
    treemap = read(MARKET_TREEMAP)

    for label in ("Strong Leader", "Leader", "Neutral", "Weakening", "Laggard"):
        assert label in source
    assert "showName" in source
    assert "showFlow" in source
    assert "showRegime" in source
    assert "showMomentum" in source
    assert "labelPolicy.showName" in treemap
    assert "labelPolicy.showFlow" in treemap
    assert "labelPolicy.showRegime" in treemap
    assert "labelPolicy.showMomentum" in treemap


def test_selected_sector_intelligence_is_compact_and_ranking_aware() -> None:
    source = read(THEME_RESEARCH)

    assert "Leading Themes" in source
    assert "Supporting Themes" in source
    assert "Key Beneficiaries" in source
    assert "Supporting Evidence" in source
    assert "selectedSectorRankedThemes" in source
