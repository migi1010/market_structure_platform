from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend" / "src"
THEME_RESEARCH = FRONTEND / "components" / "ThemeResearchPage.tsx"
SCOUT_PAGE = FRONTEND / "components" / "ThemeScoutPage.tsx"
THEME_WORKFLOW = FRONTEND / "components" / "theme-workspace" / "ThemeInvestmentWorkflow.tsx"
SUPPLY_WORKFLOW = FRONTEND / "components" / "theme-workspace" / "IndustrialDependencyWorkflow.tsx"
DYNAMIC_PANEL = FRONTEND / "components" / "theme-workspace" / "DynamicThemeRotationPanel.tsx"
TERMINAL_MODULES = FRONTEND / "modules" / "terminalModules.ts"
RESPONSIBILITIES = FRONTEND / "lib" / "researchOsWorkspaceResponsibilities.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_dynamic_theme_rotation_panel_is_shared_by_primary_research_workspaces() -> None:
    assert DYNAMIC_PANEL.exists()
    panel = read(DYNAMIC_PANEL)
    assert "DynamicThemeRotationPanel" in panel
    assert "momentum_score" in panel
    assert "evidence_score" in panel
    assert "lifecycleBadgeModel" in panel

    for path in (THEME_RESEARCH, SCOUT_PAGE, THEME_WORKFLOW, SUPPLY_WORKFLOW):
        source = read(path)
        assert "DynamicThemeRotationPanel" in source, path


def test_theme_and_supply_selectors_are_ranking_driven_top_five() -> None:
    theme = read(THEME_WORKFLOW)
    supply = read(SUPPLY_WORKFLOW)

    assert "<DynamicThemeRotationPanel" in theme
    assert "<DynamicThemeRotationPanel" in supply
    assert "limit={5}" in theme
    assert "limit={5}" in supply


def test_scout_has_ranked_emerging_accelerating_and_active_sections() -> None:
    scout = read(SCOUT_PAGE)

    assert "Top Emerging" in scout
    assert "Top Accelerating" in scout
    assert "Top Active" in scout
    assert "validated active snapshot" in scout


def test_final_navigation_excludes_pipeline_and_decision_intelligence() -> None:
    modules = read(TERMINAL_MODULES)

    assert "research-pipeline" not in modules
    assert "decision-intelligence" not in modules
    assert "Research Pipeline" not in modules
    assert "Decision Intelligence" not in modules


def test_workspace_responsibility_questions_match_phase1216_model() -> None:
    source = read(RESPONSIBILITIES)

    assert "Where is capital moving?" in source
    assert "What themes deserve research?" in source
    assert "Why does this theme matter?" in source
    assert "How does this industry work?" in source
    assert "Which company benefits?" in source
    assert "Where is the bottleneck?" not in source
    assert "Why is this theme investable?" not in source


def test_dynamic_panel_contains_no_recommendation_language() -> None:
    panel = read(DYNAMIC_PANEL) if DYNAMIC_PANEL.exists() else ""
    forbidden = ("Buy", "Sell", "Hold", "Target Price", "Allocation", "Portfolio Weight", "Recommendation")

    for phrase in forbidden:
        assert phrase not in panel
