# Phase 9.2F Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Rotation Command Center a unified selection-driven workflow led by sector rotation, theme flow ranking, and beneficiary intelligence.

**Architecture:** `Dashboard.contextDock.target` remains the only persistent entity selection. Pure frontend resolvers derive active theme context, flow rankings, flow lanes, and beneficiary rows from existing payloads. ContextDock remains supplementary and collapses by default.

**Tech Stack:** Next.js 14, React 18, TypeScript, existing terminal primitives and CSS.

---

### Task 1: Pure Intelligence Contracts

**Files:**
- Create: `frontend/src/lib/flowRanking.ts`
- Create: `frontend/src/lib/flowRanking.test.ts`
- Modify: `frontend/src/lib/beneficiaries.ts`
- Modify: `frontend/src/lib/beneficiaries.test.ts`

- [ ] Add ranking derivation tests for score ordering, momentum ordering, beneficiary counts, and active-selection emphasis.
- [ ] Add beneficiary tests for the full approved fallback chain and stale-row clearing.
- [ ] Implement pure ranking and beneficiary resolvers using existing payload fields only.

### Task 2: Shared Flow Ranking Surface

**Files:**
- Create: `frontend/src/components/terminal/FlowRanking.tsx`
- Modify: `frontend/src/components/terminal/index.ts`
- Modify: `frontend/src/components/terminal/interaction-primitives.test.tsx`

- [ ] Add the shared sortable ranking surface.
- [ ] Preserve hover, click, and double-click interaction semantics.

### Task 3: Unified Command Center Selection

**Files:**
- Modify: `frontend/src/components/ThemeResearchPage.tsx`

- [ ] Derive active theme, sector, supply role, flow lanes, Theme Command, and beneficiary rows from `activeSelection`.
- [ ] Make every Command Center click update `Dashboard.contextDock.target`.
- [ ] Remove the duplicate Theme Tape and duplicate flow presentation.

### Task 4: Rotation and Flow Visual Hierarchy

**Files:**
- Modify: `frontend/src/components/terminal/CapitalFlowSurface.tsx`
- Modify: `frontend/src/components/terminal/MarketTreemap.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] Make Rotation Snapshot the dominant first-view surface.
- [ ] Move ranking and flow graph below Rotation.
- [ ] Emphasize strongest and selected flow paths with ranked labels and visible beneficiaries.

### Task 5: Supplementary ContextDock

**Files:**
- Modify: `frontend/src/components/terminal/InteractionPrimitives.tsx`
- Modify: `frontend/src/components/Dashboard.tsx`
- Modify: `frontend/src/components/terminal/interaction-primitives.test.tsx`

- [ ] Add collapsed and expanded dock states.
- [ ] Default to collapsed, expand on user action, and collapse on route change.

### Task 6: Verification

- [ ] Run `npx tsc --noEmit`.
- [ ] Run `npm run build`.
- [ ] Run `git diff --check`.
- [ ] Verify click, hover, double-click, route-change, stale-state, and browser-console behavior.
- [ ] Capture desktop screenshots.
