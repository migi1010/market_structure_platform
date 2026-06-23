# Phase 12.5 Material Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evidence-backed material layer to the industrial graph without changing schema, snapshot, frontend, or public API contracts.

**Architecture:** Extend the existing curated `ThemeSeed` model with typed material records and cited relationship links. The industrial builder creates reusable canonical Material nodes and directional edges, the validator rejects invalid or unsupported records before activation, and repository traversal reuses filtered active-snapshot NetworkX exports.

**Tech Stack:** Python dataclasses, SQLite, NetworkX, pytest

---

### Task 1: Material taxonomy and seed contracts

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/material_taxonomy.py`
- Modify: `backend/theme_intelligence/seeds/theme_seed_models.py`
- Modify: `backend/theme_intelligence/seeds/__init__.py`
- Test: `test_material_nodes.py`

- [ ] Write failing tests for category registration, canonical keys, and unknown categories.
- [ ] Run `.\backend\.venv\Scripts\python.exe -m pytest test_material_nodes.py -q` and confirm failure because the taxonomy is absent.
- [ ] Add the canonical category set, `validate_material_category()`, and `material_key()`.
- [ ] Add all seven explicit material seed dataclasses and `ThemeSeed` collections.
- [ ] Re-run the focused test and confirm it passes.

### Task 2: Relationship registration and seed validation

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/graph_models.py`
- Modify: `backend/theme_intelligence/seeds/seed_validator.py`
- Modify: `backend/theme_intelligence/industrial_graph/graph_validator.py`
- Test: `test_material_edges.py`
- Test: `test_material_validation.py`

- [ ] Write failing tests for relationship registration, duplicate identities and edges, missing citations, unknown categories, invalid references, self-substitution, invalid endpoints, and orphan nodes.
- [ ] Run the two focused files and confirm the expected failures.
- [ ] Register the seven directional material relationships.
- [ ] Add seed validation for material identities, relationship citations, and referenced material/process/company/constraint endpoints.
- [ ] Add graph validation for material endpoint types, evidence, duplicates, and connectivity.
- [ ] Re-run the focused tests and confirm they pass.

### Task 3: Curated material seeds and builder

**Files:**
- Modify: `backend/theme_intelligence/seeds/theme_seed_data.py`
- Modify: `backend/theme_intelligence/industrial_graph/graph_builder.py`
- Test: `test_material_builder.py`

- [ ] Write failing assertions for the approved curated examples and absence of inferred edges.
- [ ] Run the builder test and confirm failure because no material records are built.
- [ ] Add explicit material records using only citation `Approved curated seed: Phase 12.5 material graph`.
- [ ] Add a builder stage that reuses existing Theme, Process, Constraint, and Company nodes and creates only explicit material edges.
- [ ] Re-run the builder test and confirm it passes.

### Task 4: Material traversal and NetworkX

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/graph_repository.py`
- Modify: `backend/theme_intelligence/industrial_graph/__init__.py`
- Test: `test_material_paths.py`
- Test: `test_material_suppliers.py`
- Test: `test_material_networkx.py`

- [ ] Write failing traversal, supplier tracing, path, and filtered-export tests.
- [ ] Run the three focused files and confirm failure because the methods are absent.
- [ ] Add material relationship filters and the five bounded deterministic traversal methods.
- [ ] Export taxonomy symbols from the package.
- [ ] Re-run the focused tests and confirm they pass.

### Task 5: Regression and verification

**Files:**
- Verify only

- [ ] Run all material tests.
- [ ] Run all industrial graph and seed tests.
- [ ] Run `.\backend\.venv\Scripts\python.exe -m pytest`.
- [ ] Run `npx tsc --noEmit` from `frontend`.
- [ ] Run `npm run build` from `frontend`.
- [ ] Review `git diff` to confirm no frontend, public API, quote, portfolio, scoring, or schema contracts changed.
