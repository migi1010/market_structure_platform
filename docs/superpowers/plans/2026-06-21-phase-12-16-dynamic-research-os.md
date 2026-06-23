# Phase 12.16 Dynamic Research OS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Research OS behave as a dynamic ranking-driven terminal instead of a static single-theme demo.

**Architecture:** Keep Theme Ranking as the master projection source from `/api/theme/ranking`. Add one shared frontend ranking panel/projection helper and wire it into Rotation, Scout, Theme, and Supply Chain without changing backend schemas, scoring, graph generation, or Scout lifecycle.

**Tech Stack:** Next.js/React, TypeScript, existing frontend contract tests plus Python static contract tests, existing FastAPI backend regression suite.

---

### Task 1: Add Dynamic Research OS Contract Tests

**Files:**
- Create: `test_phase1216_dynamic_research_os_contracts.py`
- Modify: `frontend/src/lib/themeRanking.test.ts`

- [ ] **Step 1: Write failing contract tests**

Add Python static assertions that verify:
- `DynamicThemeRotationPanel` exists.
- Rotation, Scout, Theme, and Supply Chain import/use it.
- Navigation does not expose Pipeline or Decision Intelligence.
- Theme and Supply Chain selectors cap visible ranked themes to five.
- Forbidden recommendation words are absent from the new dynamic panel.

- [ ] **Step 2: Run failing tests**

Run: `.\backend\.venv\Scripts\python.exe -m pytest test_phase1216_dynamic_research_os_contracts.py`

Expected before implementation: fail because `DynamicThemeRotationPanel` does not exist.

### Task 2: Build Shared Theme Rotation Panel

**Files:**
- Create: `frontend/src/components/theme-workspace/DynamicThemeRotationPanel.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Implement panel**

Panel props:
- `themes`
- `selectedTheme`
- `onThemeSelect`
- optional `variant`
- optional `limit`

Render:
- Top ranked theme buttons
- rank badge
- lifecycle badge
- momentum
- evidence

No buy/sell/hold/target/allocation language.

- [ ] **Step 2: Add compact CSS**

Style as a dense research terminal selector usable across Rotation, Scout, Theme, and Supply Chain.

### Task 3: Wire Ranking Into Workspaces

**Files:**
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/components/ThemeScoutPage.tsx`
- Modify: `frontend/src/components/theme-workspace/ThemeInvestmentWorkflow.tsx`
- Modify: `frontend/src/components/theme-workspace/IndustrialDependencyWorkflow.tsx`

- [ ] **Step 1: Rotation**

Replace bespoke ranking panel with `DynamicThemeRotationPanel`.

- [ ] **Step 2: Theme**

Replace static ribbon map with `DynamicThemeRotationPanel` capped at top five.

- [ ] **Step 3: Supply Chain**

Replace supply selector map with `DynamicThemeRotationPanel` capped at top five.

- [ ] **Step 4: Scout**

Display Top Emerging, Top Accelerating, and Top Active sections from theme ranking. Keep Scout candidates limited to validated active snapshot data.

### Task 4: Tighten Workspace Responsibility Model

**Files:**
- Modify: `frontend/src/lib/researchOsWorkspaceResponsibilities.ts`
- Modify: `frontend/src/lib/researchOsWorkspaceResponsibilities.test.ts`

- [ ] **Step 1: Update questions**

Use:
- Rotation: Where is capital moving?
- Scout: What themes deserve research?
- Theme: Why does this theme matter?
- Supply Chain: How does this industry work?
- Stock: Which company benefits?

- [ ] **Step 2: Assert no duplicate storytelling**

Keep graph out of Theme, memo out of Supply Chain, recommendations out of all dynamic panels.

### Task 5: Verify

Run:
- `npm test`
- `npx tsc --noEmit`
- `npm run build`
- `.\backend\.venv\Scripts\python.exe -m pytest`

Browser validate:
- Rotation
- Scout
- Theme
- Supply Chain
- Stock

Capture before/after screenshots under `reports/phase1216-browser/`.
