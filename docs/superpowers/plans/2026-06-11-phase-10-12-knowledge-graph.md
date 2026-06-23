# Phase 10.12 Knowledge Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persisted, deterministic Theme Knowledge Graph and replace the Theme Discovery right-side widgets with one evidence-based Theme Intelligence Summary.

**Architecture:** Build graph edges only from records already persisted by Phase 10 engines. Store the complete edge set in the existing SQLite database through a dedicated graph repository, replace it transactionally after a successful in-memory build, derive overlap from five approved weighted components, and expose relationships through dedicated APIs plus the existing aggregate. The frontend consumes only the aggregate and renders honest unavailable states.

**Tech Stack:** Python 3, SQLite, FastAPI, pytest, TypeScript, React, Next.js, CSS.

---

### Task 1: Graph Contracts and Persistence

**Files:**
- Create: `backend/theme_intelligence/graph/graph_models.py`
- Create: `backend/theme_intelligence/graph/graph_repository.py`
- Modify: `backend/theme_intelligence/storage/theme_repository.py`
- Test: `test_theme_graph_repository.py`

- [ ] Write tests asserting the graph table, indexes, typed unique key, edge replacement, and filtered reads.
- [ ] Run `.\backend\.venv\Scripts\python.exe -m pytest test_theme_graph_repository.py -q` and confirm failure because graph persistence does not exist.
- [ ] Add immutable graph edge models and API serialization.
- [ ] Create `theme_graph_edges` with typed uniqueness and required indexes from `ThemeRepository.initialize`.
- [ ] Implement transactional `replace_edges`, `get_edges`, and `get_theme_edges`.
- [ ] Re-run the focused test and confirm it passes.

### Task 2: Deterministic Graph Builder

**Files:**
- Create: `backend/theme_intelligence/graph/graph_builder.py`
- Create: `backend/theme_intelligence/graph/graph_supply_chain.py`
- Create: `backend/theme_intelligence/graph/graph_portfolio.py`
- Test: `test_theme_graph_builder.py`

- [ ] Write tests using persisted beneficiaries, controllers, catalysts, bottlenecks, entities, and portfolios.
- [ ] Assert stable identifiers, evidence sources, reciprocal company/portfolio edges, supply-role evidence, deterministic ordering, and no synthetic edges.
- [ ] Run the focused test and confirm failure because the builder does not exist.
- [ ] Implement evidence adapters and an in-memory builder that produces a complete edge list before writing.
- [ ] Re-run the focused test and confirm it passes.

### Task 3: Overlap and Graph Engine

**Files:**
- Create: `backend/theme_intelligence/graph/graph_overlap.py`
- Create: `backend/theme_intelligence/graph/graph_ranker.py`
- Create: `backend/theme_intelligence/graph/graph_engine.py`
- Create: `backend/theme_intelligence/graph/__init__.py`
- Test: `test_theme_graph_overlap.py`

- [ ] Write tests for component intersections, the approved 35/25/15/15/10 formula, clamping, evidence-only supply roles, empty overlap, ranking, and transactional rebuild.
- [ ] Run the focused test and confirm failure because overlap and graph services do not exist.
- [ ] Implement normalized set overlap, score calculation, overlap evidence, theme-overlap edges, graph summaries, and relationship-intelligence payloads.
- [ ] Re-run the focused test and confirm it passes.

### Task 4: Startup, APIs, and Aggregate

**Files:**
- Modify: `backend/theme_intelligence/seeds/seed_loader.py`
- Modify: `backend/theme_intelligence/aggregate.py`
- Modify: `backend/theme_intelligence/__init__.py`
- Modify: `backend/main.py`
- Modify: `test_theme_intelligence_aggregate_api.py`
- Modify: `test_theme_api_contracts.py`
- Create: `test_theme_graph_api.py`

- [ ] Add failing tests for graph rebuild after Phase 10 recomputation, all three routes, honest unknown-theme payloads, and aggregate `relationship_intelligence`.
- [ ] Run the focused tests and confirm the expected contract failures.
- [ ] Rebuild graph after score and portfolio recomputation.
- [ ] Export graph service functions and add `/api/theme/graph`, `/api/theme/graph/{theme_id}`, and `/api/theme/overlap/{theme_id}`.
- [ ] Inject persisted relationship intelligence into the aggregate without changing existing keys.
- [ ] Re-run focused backend tests and confirm they pass.

### Task 5: Frontend Aggregate Contract

**Files:**
- Modify: `frontend/src/types/stock.ts`
- Modify: `frontend/src/services/stockApi.ts`
- Modify: `frontend/src/lib/themeIntelligence.test.ts`

- [ ] Update the source contract first to require `relationship_intelligence`, unified summary labels, and removal of the donut and placeholder.
- [ ] Run `npx tsc --noEmit` and confirm failure until the frontend contract is implemented.
- [ ] Add typed related themes, shared evidence, and portfolio exposure.
- [ ] Normalize unknown payloads defensively and add empty relationship intelligence to `emptyThemeAggregate`.
- [ ] Re-run `npx tsc --noEmit`.

### Task 6: Unified Theme Intelligence Summary

**Files:**
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] Replace `ThemeMomentumDashboard` with `ThemeIntelligenceSummary`.
- [ ] Derive rank from the Phase 10 score ranking and portfolio weight from the highest persisted aggregate allocation, displaying unavailable when absent.
- [ ] Render Positioning, Momentum, Why Now, Primary Bottleneck, Conviction Summary, and Theme Relationship Intelligence in one card.
- [ ] Remove the donut and lifecycle-mix widget.
- [ ] Render graph values only when aggregate evidence exists; otherwise render an honest empty state.
- [ ] Keep labels English where existing Chinese source text is corrupted, avoiding new mojibake.
- [ ] Add focused responsive styles preventing clipping and overflow.
- [ ] Run TypeScript and lint checks.

### Task 7: Verification and Browser Validation

**Files:**
- Create screenshots under: `reports/phase1012-*.png`

- [ ] Run `.\backend\.venv\Scripts\python.exe -m pytest`.
- [ ] Run `npx tsc --noEmit` in `frontend`.
- [ ] Run `npm run lint` in `frontend`.
- [ ] Run `npm run build` in `frontend`.
- [ ] Start or reuse local backend and frontend services.
- [ ] Verify graph APIs and aggregate payloads for HBM, Glass Substrate, and AI Infrastructure.
- [ ] Inspect each page for readability, overflow, clipping, duplicate values, hydration errors, console errors, and mojibake.
- [ ] Capture screenshots for all three themes.
- [ ] Review `git diff` and report only scoped changes and remaining risks.
