# Phase 10.14 Rotation Repair and Theme Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore truthful sector Rotation data and compress sparse Theme Research evidence without introducing fabricated market data or evidence.

**Architecture:** The backend owns a stable `RotationSnapshotResponse` assembled from cached ETF quote evidence and explicit availability metadata. The frontend owns one abortable Rotation request and renders either verified rows or compact truthful unavailable states. Theme Intelligence continues using the existing Dashboard-owned aggregate request, with canonical aliases and a compact evidence coverage grid at the rendering boundary.

**Tech Stack:** FastAPI, SQLite cache, pytest, Next.js 14, React 18, TypeScript.

---

### Task 1: Rotation Contract Tests

**Files:**
- Create: `test_rotation_api_contract.py`
- Create: `test_rotation_empty_state_contract.py`
- Create: `test_rotation_persisted_fallback.py`
- Create: `test_rotation_status_truthfulness.py`
- Create: `test_rotation_sector_ranking.py`

- [ ] Define the required response envelope and row contracts.
- [ ] Verify empty inputs produce `unavailable`, null metrics, and no leaders.
- [ ] Verify expired persisted quotes produce `stale`, never `live`.
- [ ] Verify mixed quote coverage produces `partial`.
- [ ] Verify sector ranking is deterministic and contains no fabricated baseline rows.
- [ ] Run the focused tests and confirm they fail against the current list response and baseline behavior.

### Task 2: Backend Rotation Snapshot

**Files:**
- Modify: `backend/quant_engine/sector_rotation_engine/engine.py`
- Modify: `backend/main.py`
- Modify: `backend/settings.py`

- [ ] Replace numeric safe baselines with nullable unavailable rows.
- [ ] Track quote provenance, freshness, and row-level truth status.
- [ ] Build the stable Rotation snapshot envelope.
- [ ] Preserve `/sector/rotation` while returning the authoritative envelope.
- [ ] Read valid persisted endpoint data as cached or stale fallback.
- [ ] Resolve the default SQLite cache path from the backend project directory.
- [ ] Add nullable future Committee fields without using them for decisions.
- [ ] Run the focused backend tests until green.

### Task 3: Frontend Rotation Tests

**Files:**
- Modify: `frontend/src/lib/rotationWorkspace.test.ts`
- Modify: `frontend/src/lib/themeIntelligence.test.ts`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] Define normalization expectations for envelope and legacy list responses.
- [ ] Verify valid rows, including zero values, are not silently dropped.
- [ ] Verify truthful status labels and compact unavailable output.
- [ ] Verify Theme Research has one abortable sector Rotation fetch owner.
- [ ] Verify leaders and ranking render branches are present.
- [ ] Run TypeScript and focused source-contract tests to confirm expected failures.

### Task 4: Frontend Rotation Binding

**Files:**
- Modify: `frontend/src/types/stock.ts`
- Modify: `frontend/src/services/stockApi.ts`
- Modify: `frontend/src/lib/rotationWorkspace.ts`
- Modify: `frontend/src/components/ThemeResearchPage.tsx`

- [ ] Add strict Rotation snapshot interfaces and status union.
- [ ] Normalize authoritative envelopes and legacy arrays without inventing values.
- [ ] Fetch Rotation once with an abort signal and local persisted fallback.
- [ ] Stop resetting Rotation feeds without fetching them.
- [ ] Render compact unavailable states for snapshot, leaders, ranking, and selected intelligence.
- [ ] Render backend status, source, timestamp, diagnostics, links, and data quality truthfully.

### Task 5: Theme Density and Alias Tests

**Files:**
- Modify: `frontend/src/lib/themeIntelligence.test.ts`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] Verify the compact evidence grid covers all eight approved sections.
- [ ] Verify missing evidence uses compact coverage gaps rather than chart-sized panels.
- [ ] Verify large visual classes are conditional on sufficient evidence.
- [ ] Verify `CPO` and `CPO Photonics` normalize to `cpo_photonics`.
- [ ] Verify CoWoS and Glass Substrate aliases remain canonical.
- [ ] Verify TER ticker precedence and no internal identifier navigation leakage.
- [ ] Confirm tests fail before implementation.

### Task 6: Theme Density and Canonical Identity

**Files:**
- Modify: `frontend/src/services/stockApi.ts`
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] Add one canonical theme alias map shared by aggregate normalization and search routing.
- [ ] Replace oversized sparse sections with the compact evidence grid.
- [ ] Show counts, coverage, up to two verified facts, and missing-evidence chips.
- [ ] Only render supply-chain and evidence visuals when sufficient verified rows exist.
- [ ] Keep CoWoS truthful and avoid generated relationships.
- [ ] Preserve the Dashboard-owned aggregate fetch and Phase 12 lineage labels.

### Task 7: Integrated Verification

**Files:**
- Review all modified files.

- [ ] Run focused Rotation and Theme contract tests.
- [ ] Run `.\backend\.venv\Scripts\python.exe -m pytest`.
- [ ] Run `npx tsc --noEmit`.
- [ ] Run `npm run build`.
- [ ] Start or reuse local backend and frontend services.
- [ ] Browser validate Rotation, HBM, Glass Substrate, CoWoS, CPO, AI Infrastructure, Data Center Cooling, TER, and NVDA freshness.
- [ ] Check console/network for hydration errors, duplicate keys, and duplicate aggregate requests.
- [ ] Capture screenshots where useful.
