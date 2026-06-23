# Phase 9.2D Market Operating System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Rotation card-grid workspace with a dense, unified market command center built from existing frontend payloads.

**Architecture:** Add shared deterministic treemap geometry and reusable market surfaces, then compose them inside the existing Rotation route. Extend drilldown dock payloads additively so existing search, routing, and workspace behavior remain compatible.

**Tech Stack:** Next.js 14, React 18, TypeScript, CSS, existing terminal primitives.

---

### Task 1: Shared Treemap Geometry

**Files:**
- Create: `frontend/src/lib/treemap.test.ts`
- Create: `frontend/src/lib/treemap.ts`

- [ ] Write a contract test proving weighted items produce bounded, non-overlapping calculated rectangles.
- [ ] Run the contract and verify it fails because the module does not exist.
- [ ] Implement deterministic squarified treemap geometry with safe fallback weights.
- [ ] Run the contract and verify it passes.

### Task 2: Shared Market Surfaces

**Files:**
- Create: `frontend/src/components/terminal/MarketTreemap.tsx`
- Create: `frontend/src/components/terminal/CapitalFlowSurface.tsx`
- Create: `frontend/src/components/terminal/BeneficiaryMatrix.tsx`
- Modify: `frontend/src/components/terminal/index.ts`
- Modify: `frontend/src/components/terminal/interaction-primitives.test.tsx`

- [ ] Add failing compile-time usage contracts for all three surfaces.
- [ ] Implement the smallest reusable components supporting preview, context, drilldown, and selected states.
- [ ] Verify the component contracts compile.

### Task 3: ContextDock Intelligence Contract

**Files:**
- Modify: `frontend/src/lib/drilldown.test.ts`
- Modify: `frontend/src/lib/drilldown.ts`
- Modify: `frontend/src/lib/entities.ts`
- Modify: `frontend/src/components/Dashboard.tsx`

- [ ] Add a failing contract assertion for optional summary, flow, risk, exposure, beneficiaries, and related themes.
- [ ] Extend the dock contract additively.
- [ ] Render intelligence sections while retaining the existing generic drilldown fallback.
- [ ] Verify old and new dock payloads compile.

### Task 4: Unified Rotation Command Center

**Files:**
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] Replace Rotation’s fixed-span heatmap composition with `MarketTreemap`.
- [ ] Replace the Theme Flow button row in the command-center workflow with `CapitalFlowSurface`.
- [ ] Add `BeneficiaryMatrix` and compact context preview to the first viewport.
- [ ] Preserve all non-Rotation ThemeResearchPage fallback sections.
- [ ] Apply dense terminal styling and responsive fallback behavior.

### Task 5: Verification

**Files:**
- Create: `reports/phase92d-rotation-command-center.png`
- Create: `reports/phase92d-context-dock.png`

- [ ] Run treemap and drilldown contract assertions.
- [ ] Run `npx tsc --noEmit`.
- [ ] Run `npm run build`.
- [ ] Run `git diff --check` and confirm no backend source changes from Phase 9.2D.
- [ ] Verify hover, single-click ContextDock, and double-click drilldown in the browser.
- [ ] Capture before/after screenshots.
