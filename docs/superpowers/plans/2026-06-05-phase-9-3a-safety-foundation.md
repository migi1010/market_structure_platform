# Phase 9.3A Safety Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish render-safe frontend utilities and remove known safety regressions before any Phase 9.3 workspace composition changes.

**Architecture:** Add small pure helpers at frontend data-to-render boundaries, then migrate the beneficiary resolver, Rotation view model, treemap, and search-result identity to those helpers. Preserve all backend, API, cache, routing, selection, and visual-layout contracts.

**Tech Stack:** TypeScript, React 18, Next.js 14

---

### Task 1: Render-safe collection utilities

**Files:**
- Create: `frontend/src/lib/payloadSafety.ts`
- Create: `frontend/src/lib/payloadSafety.test.ts`

- [ ] Add pure helpers for coercing unknown collections, filtering nullable rows, and stable unique values.
- [ ] Add compile-time contract coverage for undefined, null, malformed, duplicate, and valid payloads.

### Task 2: Search-result identity

**Files:**
- Create: `frontend/src/lib/searchResultIdentity.ts`
- Create: `frontend/src/lib/searchResultIdentity.test.ts`
- Modify: `frontend/src/components/GlobalStockSearch.tsx`

- [ ] Centralize stable search-result keys.
- [ ] Use the same identity for quick-result deduplication and React rendering.
- [ ] Verify duplicate command results produce distinct or deduplicated keys.

### Task 3: Beneficiary fallback hardening

**Files:**
- Modify: `frontend/src/lib/beneficiaries.ts`
- Modify: `frontend/src/lib/beneficiaries.test.ts`

- [ ] Make all beneficiary source collections render-safe.
- [ ] Apply explicit beneficiaries before entity-specific fallback.
- [ ] Expand theme, sector, and supply fallback coverage without retaining stale rows.

### Task 4: Rotation safety and mojibake repair

**Files:**
- Modify: `frontend/src/lib/rotationWorkspace.ts`
- Modify: `frontend/src/lib/rotationWorkspace.test.ts`
- Modify: `frontend/src/components/terminal/MarketTreemap.tsx`

- [ ] Replace corrupt Rotation diagnostic labels with Chinese-first labels.
- [ ] Use shared safe collection utilities at Rotation render boundaries.
- [ ] Preserve the accepted Phase 9.2G composition and adaptive treemap behavior.

### Task 5: Verification

- [ ] Run `npm run lint`.
- [ ] Run `npm run test`.
- [ ] Run `npx tsc --noEmit`.
- [ ] Run `npm run build`.
- [ ] Run `git diff --check`.
- [ ] Verify the browser console no longer reports duplicate React keys.
- [ ] Confirm Rotation contains no Capital Flow or Theme Flow surfaces.
