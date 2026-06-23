# Phase 12.17 Rotation 2.0 Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Rotation into a capital-flow command center that answers only “Where is capital moving?”.

**Architecture:** Keep the work frontend-focused and Rotation-scoped. Reuse existing `/api/theme/ranking` projection already available as `registryThemes`, reuse `MarketTreemap`, and update only Rotation composition, treemap label policy, Rotation layout CSS, and Rotation contract tests.

**Tech Stack:** Next.js/React, TypeScript, CSS, pytest source-contract tests, existing browser validation scripts.

---

### Task 1: Add Rotation 2.0 Contract Tests

**Files:**
- Create: `test_phase1217_rotation_2_command_center_contracts.py`
- Modify: none

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Verify tests fail before implementation**

Run: `.\backend\.venv\Scripts\python.exe -m pytest test_phase1217_rotation_2_command_center_contracts.py`

Expected: failures for missing command-center class, routing helper, and label policy fields.

### Task 2: Update Rotation Treemap Label Policy

**Files:**
- Modify: `frontend/src/lib/rotationWorkspace.ts`
- Modify: `frontend/src/components/terminal/MarketTreemap.tsx`

- [ ] **Step 1: Extend `TreemapLabelPolicy`**

Add `showName` and make the policy match:
- tiny: name only
- small: name + flow
- medium: name + flow + state
- large: name + flow + state + momentum

- [ ] **Step 2: Update `MarketTreemap` rendering**

Render score only as a secondary metric for medium/large if kept, and ensure tiny tiles render only the name. Keep existing no-overlap behavior by CSS truncation and density classes.

### Task 3: Recompose Rotation Page

**Files:**
- Modify: `frontend/src/components/ThemeResearchPage.tsx`

- [ ] **Step 1: Add `openThemeFromRotation`**

Route Theme Ranking clicks from Rotation to the Theme workspace by calling `selectTheme(themeId)` and then `setTab("command")`.

- [ ] **Step 2: Replace Rotation layout class**

Use `rotation-command-center` and `rotation-command-center-grid`.

- [ ] **Step 3: Keep only allowed surfaces**

Render:
- Capital Flow Treemap
- Market Diagnostics
- Capital Flow Story
- Theme Rotation Panel
- Selected Sector Intelligence

Do not render `FlowRanking`, Sector Ranking, Leader Board, or Top Sector List.

### Task 4: Add Rotation 2.0 CSS

**Files:**
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Add command-center grid**

Desktop layout:
- treemap: left 65%
- center column: diagnostics and story
- right column: theme rotation panel

Responsive layout:
- 1366x768 keeps treemap primary and avoids overlap
- narrow widths stack panels without duplicate ranking surfaces

### Task 5: Verify

**Files:**
- No source changes

- [ ] **Step 1: Run focused contracts**

Run:
`.\backend\.venv\Scripts\python.exe -m pytest test_phase1217_rotation_2_command_center_contracts.py test_phase1216_dynamic_research_os_contracts.py test_final_acceptance_frontend_contracts.py`

- [ ] **Step 2: Run frontend validation**

Run:
`npm test`
`npx tsc --noEmit`
`npm run build`

- [ ] **Step 3: Run backend regression**

Run:
`.\backend\.venv\Scripts\python.exe -m pytest`

- [ ] **Step 4: Browser validation**

Validate `http://localhost:3000` at 1366x768 and 1920x1080. Capture screenshots under `reports/phase1217-browser/`.
