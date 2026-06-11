# Phase 10.13 Quote Freshness and Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make stock quote freshness auditable and convert Theme Intelligence GET endpoints to fast persisted reads.

**Architecture:** A single backend quote freshness classifier controls status and timestamps across provider, quote-cache, endpoint-cache, and LKG paths. Theme GET endpoints read persisted SQLite rows, while explicit refresh/rebuild operations remain separate and invalidate short-lived aggregate caches.

**Tech Stack:** Python, SQLite, FastAPI, pytest, TypeScript, React, Next.js.

---

### Task 1: Cache Metadata and Quote Freshness

**Files:**
- Modify: `backend/quant_engine/data_pipeline/market_data.py`
- Modify: `backend/quant_engine/data_pipeline/providers.py`
- Test: `test_quote_freshness.py`

- [ ] Add failing tests for fresh, stale, LKG, metadata, market-aware TTL, and forced quote-cache bypass.
- [ ] Run focused tests and confirm expected failures.
- [ ] Add metadata-aware cache reads and quote freshness normalization.
- [ ] Add `force_refresh` to the quote fetch path.
- [ ] Re-run focused tests.

### Task 2: Stock Endpoint Recovery and Quote-Only Refresh

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/quant_engine/stock_service.py`
- Test: `test_stock_quote_freshness_api.py`

- [ ] Add failing API tests for expired endpoint downgrade and quote-only force refresh.
- [ ] Confirm force refresh reuses endpoint research sections.
- [ ] Implement endpoint freshness downgrade and quote-section replacement.
- [ ] Re-run focused API tests.

### Task 3: Persisted Theme Reads

**Files:**
- Modify: `backend/theme_intelligence/discovery/discovery_engine.py`
- Modify: `backend/theme_intelligence/portfolio/portfolio_engine.py`
- Modify: `backend/theme_intelligence/storage/theme_repository.py`
- Modify: `backend/theme_intelligence/aggregate.py`
- Modify: `backend/theme_intelligence/graph/graph_engine.py`
- Modify: `backend/main.py`
- Test: `test_theme_read_performance_contracts.py`

- [ ] Add failing tests proving default discovery and portfolio GET paths do not recompute.
- [ ] Add filtered repository methods for one theme.
- [ ] Add aggregate TTL cache and invalidation hooks.
- [ ] Read persisted overlap edges on GET.
- [ ] Add explicit discovery refresh and graph rebuild routes where required.
- [ ] Re-run focused tests.

### Task 4: Frontend Freshness Contract

**Files:**
- Modify: `frontend/src/types/stock.ts`
- Modify: `frontend/src/services/stockApi.ts`
- Modify: `frontend/src/components/StockAnalysisWorkspace.tsx`
- Modify: `frontend/src/lib/payloadSafety.test.ts`
- Add or modify: focused source contract tests

- [ ] Add failing source/type contracts for freshness metadata and labels.
- [ ] Preserve stale/fallback status during normalization.
- [ ] Render status, source, timestamp, and cache age.
- [ ] Remove hard-coded timestamps.
- [ ] Re-run TypeScript checks.

### Task 5: Frontend Request Deduplication

**Files:**
- Modify: `frontend/src/services/stockApi.ts`
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/lib/themeIntelligence.test.ts`

- [ ] Add source contracts for one in-flight request per normalized theme.
- [ ] Keep abort-on-switch semantics.
- [ ] Confirm hover paths contain no aggregate fetch.
- [ ] Re-run TypeScript checks.

### Task 6: Full Verification

- [ ] Run full pytest.
- [ ] Run `npx tsc --noEmit`.
- [ ] Run lint.
- [ ] Run production build.
- [ ] Measure discovery, aggregate, portfolio, overlap, normal stock, and force-refresh stock timings.
- [ ] Browser validate NVDA and HBM, Glass Substrate, and AI Infrastructure request behavior.
- [ ] Capture screenshots when browser capture is available.
