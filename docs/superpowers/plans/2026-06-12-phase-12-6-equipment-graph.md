# Phase 12.6 Equipment Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit, evidence-backed equipment layer with globally reusable producer companies.

**Architecture:** Extend `ThemeSeed` with typed equipment records and cited directional links. Equipment nodes are created only by the curated equipment builder stage; producer records may create or reuse global canonical Company nodes. Existing SQLite persistence, snapshots, and NetworkX export remain unchanged.

**Tech Stack:** Python dataclasses, SQLite, NetworkX, pytest

---

### Task 1: Taxonomy and seed contracts
- [ ] Add failing taxonomy and canonical-key tests.
- [ ] Add `equipment_taxonomy.py` with the 14 approved categories.
- [ ] Add the seven required equipment seed dataclasses and `ThemeSeed` collections.
- [ ] Export the new contracts.

### Task 2: Relationship and seed validation
- [ ] Add failing relationship, category, identity, citation, ticker, reference, substitution, and duplicate tests.
- [ ] Register the seven equipment relationships.
- [ ] Validate equipment records and global producer-company identity across all themes.
- [ ] Reject conflicting names for one canonical ticker.

### Task 3: Explicit curated construction
- [ ] Add failing builder tests for all approved records and role-string removal.
- [ ] Add curated equipment records with citation `Approved curated seed: Phase 12.6 equipment graph`.
- [ ] Remove incidental role-derived Equipment node creation.
- [ ] Build only explicit equipment nodes and edges, including `company:TER`.

### Task 4: Graph validation and traversal
- [ ] Add failing orphan, endpoint, evidence, traversal, path, supplier, and NetworkX tests.
- [ ] Validate equipment categories, endpoint types, connectivity, substitutions, and evidence.
- [ ] Add the five bounded deterministic active-snapshot traversal methods.

### Task 5: Verification
- [ ] Run all equipment tests.
- [ ] Run all industrial graph and seed regressions.
- [ ] Run `.\backend\.venv\Scripts\python.exe -m pytest`.
- [ ] Run `npx tsc --noEmit` and `npm run build` from `frontend`.
- [ ] Audit the diff for schema, API, frontend, scoring, quote, and portfolio changes.
