# Phase 12.11E Institutional Research Operating System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the score-first Theme and Scout dashboards with dense, evidence-first institutional research workspaces while preserving all persisted data contracts.

**Architecture:** Keep backend aggregate and Scout snapshot contracts unchanged. Add pure frontend projections for rotation state and persisted graph/supply-chain presentation, then compose three Theme layers: operating summary, primary research, and validation. Scout becomes an evidence, constraint, queue, and lifecycle workspace with score metadata demoted to a compact strip.

**Tech Stack:** Next.js, React, TypeScript, CSS, Node test runner, pytest contract tests, in-app browser.

---

### Task 1: Lock Visual Contracts

**Files:**
- Modify: `frontend/src/lib/rotationWorkspace.test.ts`
- Modify: `frontend/src/lib/supplyChainIntelligence.test.ts`
- Modify: `frontend/src/lib/themeScout.test.ts`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] Add failing tests for Strong Leader, Improving, Neutral, Weakening, and Laggard projection.
- [ ] Add failing contracts for a connected persisted industrial graph and beneficiary flow.
- [ ] Add failing Scout contracts requiring evidence-first panels and prohibiting dominant gauges/radar.
- [ ] Run focused tests and confirm failures represent missing Phase 12.11E behavior.

### Task 2: Rotation State Projection

**Files:**
- Modify: `frontend/src/lib/rotationWorkspace.ts`
- Modify: `frontend/src/components/terminal/MarketTreemap.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] Implement deterministic visual-state projection from persisted score, momentum, and flow.
- [ ] Expose the state through stable data attributes.
- [ ] Apply unique fill, border, and legend treatments.
- [ ] Run focused tests and TypeScript.

### Task 3: Theme Replacement Architecture

**Files:**
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/components/theme-workspace/ThemeIndustrialWorkspace.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] Replace the command view with one compact operating summary.
- [ ] Remove AI hero, ranking, deep-dive, repeated confidence/lifecycle/timeline, and duplicate beneficiary widgets from the primary command surface.
- [ ] Place supply chain, constraints, controllers, and opportunities in the primary viewport.
- [ ] Place coverage, gaps, packets, and lineage in a compact validation surface.

### Task 4: Persisted Dependency Graph and Supply Flow

**Files:**
- Modify: `frontend/src/lib/supplyChainIntelligence.ts`
- Modify: `frontend/src/components/theme-workspace/ThemeIndustrialWorkspace.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] Project only persisted path endpoints and relationships.
- [ ] Render a width-filling dependency graph ordered Theme through Company.
- [ ] Render connected Controller to Constraint to Resolution Enabler to Direct and Indirect Beneficiary flow.
- [ ] Preserve explicit unavailable states without creating inferred edges.

### Task 5: Scout Evidence-First Recomposition

**Files:**
- Modify: `frontend/src/lib/themeScout.ts`
- Modify: `frontend/src/components/ThemeScoutPage.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] Promote signal clusters, constraint watch, evidence distribution, evidence-linked companies, research queue, pipeline, and lifecycle.
- [ ] Demote persisted score/readiness fields to compact metadata.
- [ ] Remove dominant gauges, radar, and candidate-health widgets.
- [ ] Keep novelty unavailable when methodology is unavailable.

### Task 6: Verification and Visual Acceptance

**Files:**
- Update: `reports/phase1211e-after/*.png`

- [ ] Run focused frontend tests.
- [ ] Run `npx tsc --noEmit`.
- [ ] Run `npm run build`.
- [ ] Run full backend pytest.
- [ ] Validate Rotation, six supply-chain themes, Theme command density, and active Scout candidate on `http://localhost:3000`.
- [ ] Capture matched screenshots and compare above-the-fold occupied research area.

