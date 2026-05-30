# Phase 6.0 Local Full-Power Quant + Theme Forecast AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a parallel `local_full` research subsystem with feature store, theme forecast engine, walk-forward validation, LEAN export boundary, Docker support, and a frontend Theme Forecast AI module.

**Architecture:** Existing Render-safe endpoints remain unchanged. New Phase 6 modules live under `backend/quant_engine/research_store`, `backend/quant_engine/theme_forecast`, `backend/quant_engine/validation`, and `backend/quant_engine/lean_integration`, with new `/theme/forecast*` and `/lean/insights` endpoints. Frontend adds a module/page that consumes the new endpoint without disturbing existing workspace routing.

**Tech Stack:** Python, FastAPI, pandas, numpy, optional sklearn/hmmlearn/xgboost/lightgbm/pyarrow, Next.js, TypeScript, Docker Compose, optional Redis/PostgreSQL/LEAN.

---

### Task 1: Runtime Mode Foundation

**Files:**
- Modify: `backend/settings.py`
- Modify: `backend/.env.example`

- [ ] Add runtime mode flags:
  - `miji_runtime_mode`
  - `miji_enable_theme_forecast`
  - `miji_enable_lean`
  - `miji_enable_background_jobs`
  - `miji_enable_feature_store`
  - `miji_feature_store_dir`
- [ ] Ensure defaults preserve Render-safe behavior.
- [ ] Run `py -m py_compile backend/settings.py`.

### Task 2: Research Store Schemas

**Files:**
- Create: `backend/quant_engine/research_store/__init__.py`
- Create: `backend/quant_engine/research_store/schemas.py`
- Create: `backend/quant_engine/research_store/feature_store.py`

- [ ] Define typed dataclasses for theme features, forecasts, validation summaries, and lifecycle status.
- [ ] Implement local filesystem persistence with parquet if available and CSV fallback.
- [ ] Implement feature snapshot hydration from existing theme definitions and market data helpers.
- [ ] Ensure feature frames never include future target columns in model feature columns.
- [ ] Run `py -m py_compile backend/quant_engine/research_store/*.py`.

### Task 3: Theme Forecast Engine

**Files:**
- Create: `backend/quant_engine/theme_forecast/__init__.py`
- Create: `backend/quant_engine/theme_forecast/engine.py`

- [ ] Build forecast horizons: `1w`, `1m`, `3m`.
- [ ] Compute forecast score, expected excess return, probability, confidence, risk state, crowding state, positive drivers, negative drivers, and regime context.
- [ ] Keep model adapters optional so missing sklearn/xgboost/lightgbm never crashes the endpoint.
- [ ] Return `status=disabled` when local forecast mode is off.
- [ ] Run `py -m py_compile backend/quant_engine/theme_forecast/*.py`.

### Task 4: Walk-Forward Validation

**Files:**
- Create: `backend/quant_engine/validation/__init__.py`
- Create: `backend/quant_engine/validation/walk_forward.py`

- [ ] Implement chronological expanding-window validation.
- [ ] Compute hit rate, precision@top5, information ratio, max drawdown, calibration quality, confusion matrix, turnover, and excess return stability.
- [ ] Return `partial_data` when not enough observations exist.
- [ ] Add explicit guard that target columns are excluded from features.
- [ ] Run `py -m py_compile backend/quant_engine/validation/*.py`.

### Task 5: LEAN Integration Boundary

**Files:**
- Create: `backend/quant_engine/lean_integration/__init__.py`
- Create: `backend/quant_engine/lean_integration/insights.py`

- [ ] Implement `LeanInsightAdapter`.
- [ ] Implement `LeanSignalExporter`.
- [ ] Implement `LeanBacktestRunner` as a local command boundary only.
- [ ] Ensure no live brokerage execution code exists.
- [ ] Run `py -m py_compile backend/quant_engine/lean_integration/*.py`.

### Task 6: API Endpoints

**Files:**
- Modify: `backend/main.py`

- [ ] Add `GET /theme/forecast`.
- [ ] Add `GET /theme/forecast/validation`.
- [ ] Add `GET /theme/forecast/status`.
- [ ] Add `GET /lean/insights`.
- [ ] Ensure endpoints are fail-soft and do not alter existing `/stock`, `/alpha/top`, `/sector/rotation`, `/market/regime`.
- [ ] Run FastAPI smoke checks for new endpoints.

### Task 7: Frontend Theme Forecast AI Module

**Files:**
- Modify: `frontend/src/types/stock.ts`
- Modify: `frontend/src/services/stockApi.ts`
- Modify: `frontend/src/modules/terminalModules.ts`
- Modify: `frontend/src/components/Dashboard.tsx`
- Create: `frontend/src/components/ThemeForecastAIPage.tsx`

- [ ] Add forecast response types.
- [ ] Add `fetchThemeForecast()` and `fetchThemeForecastValidation()`.
- [ ] Add terminal module `theme-forecast`.
- [ ] Add lazy page mount in Dashboard.
- [ ] Render forecast cards, horizon toggle, regime context, drivers, and validation performance.
- [ ] Run `npx tsc --noEmit` and `npm run build`.

### Task 8: Docker Local Full Runtime

**Files:**
- Modify: `docker-compose.yml`
- Modify: `backend/requirements.txt`
- Modify: `.env.example`

- [ ] Add backend/frontend local full service env.
- [ ] Add Redis and PostgreSQL services.
- [ ] Add LEAN placeholder service/boundary.
- [ ] Add optional local research dependencies.
- [ ] Verify compose syntax with `docker compose config` if Docker is available.

### Task 9: Final Verification

**Commands:**
- `py -m py_compile backend/settings.py backend/main.py`
- `py -m py_compile backend/quant_engine/research_store/*.py backend/quant_engine/theme_forecast/*.py backend/quant_engine/validation/*.py backend/quant_engine/lean_integration/*.py`
- `npx tsc --noEmit`
- `npm run build`

- [ ] Verify Render-safe defaults remain unchanged.
- [ ] Verify local_full endpoints return explainable forecast payloads.
- [ ] Verify no live brokerage execution is present.
- [ ] Verify generated artifacts are not staged.
