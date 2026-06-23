# Phase 12.7 Constraint Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make constraints globally canonical, evidence-backed graph entities with explicit dependency, resolver, and exposure semantics.

**Architecture:** Add a constraint taxonomy and typed curated constraint records while migrating supported persisted Phase 10 bottlenecks into canonical nodes. Existing process/material/equipment constraint link constructors remain compatible through optional fields. Legacy relationship types remain registered, but inferred `LIMITS` and `RESOLVES` construction stops.

**Tech Stack:** Python dataclasses, SQLite, NetworkX, pytest

---

### Task 1: Taxonomy and compatible seed contracts
- [ ] Add failing taxonomy and canonical-key tests.
- [ ] Add `constraint_taxonomy.py`.
- [ ] Add the missing constraint seed dataclasses.
- [ ] Extend existing process/material/equipment constraint links additively.

### Task 2: Validation
- [ ] Add failing category, identity, citation, endpoint, relation, duplicate, and evidence tests.
- [ ] Validate global company identity for resolver and exposure records.
- [ ] Reject inferred resolver relationships and invalid endpoint directions.

### Task 3: Migration and curated builder
- [ ] Add failing builder tests for canonical migration, unsupported-category skipping, explicit resolver/exposure, and inferred-edge removal.
- [ ] Migrate supported persisted bottlenecks with deterministic canonical identities.
- [ ] Add six approved curated constraints and their explicit cited links.
- [ ] Remove inferred `LIMITS` and beneficiary-derived `RESOLVES` edges.

### Task 4: Traversal and NetworkX
- [ ] Add failing traversal, resolver, exposure, path, and NetworkX tests.
- [ ] Add eight bounded deterministic active-snapshot traversal methods.

### Task 5: Verification
- [ ] Run constraint tests and all graph regressions.
- [ ] Run full backend pytest.
- [ ] Run frontend TypeScript and production build.
- [ ] Audit for schema, frontend, API, quote, portfolio, scoring, and analytics changes.
