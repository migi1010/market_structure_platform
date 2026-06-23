# Phase 12.11B Scout Proposal Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic manual/offline proposal boundary that can activate a reviewed non-empty Theme Scout snapshot without mutating any downstream intelligence system.

**Architecture:** Export a checksummed evidence manifest from the active graph snapshot, parse a strict versioned proposal JSON that references only manifest evidence IDs, and pass the frozen proposal through the existing deterministic Scout builder and repository. A local CLI owns explicit validation, build, activation, and isolation verification; no startup or public write path is added.

**Tech Stack:** Python 3.12, SQLite, dataclasses, strict JSON parsing, SHA-256 canonical checksums, argparse, pytest, React, TypeScript.

---

### Task 1: Strict Proposal Contract

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_providers.py`
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_proposal.schema.json`
- Create: `test_theme_scout_providers.py`

- [ ] Write failing tests for strict fields, inline evidence, review metadata,
  empty dry-run acceptance, empty production rejection, and `DISCOVERED`.
- [ ] Run `.\backend\.venv\Scripts\python.exe -m pytest test_theme_scout_providers.py -q`
  and confirm the provider module is missing.
- [ ] Implement strict typed parsing with explicit allowed-key sets at every
  object level and immutable dataclass conversion.
- [ ] Add the versioned JSON Schema as documentation and external validation
  contract.
- [ ] Re-run the provider tests.

### Task 2: Frozen Active-Graph Evidence Manifest

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_manifest.py`
- Create: `test_theme_scout_manifest.py`
- Modify: `backend/theme_intelligence/industrial_graph/theme_scout_engine.py`

- [ ] Write failing tests proving only evidence attached to the active graph
  build is exported and domain derivation is deterministic.
- [ ] Implement manifest models, active graph joins, endpoint context,
  canonical ordering, and bundle checksum.
- [ ] Change the engine to consume a supplied frozen manifest rather than
  independently querying all approved graph evidence.
- [ ] Add rejection for stale graph versions and evidence checksum mismatch.
- [ ] Run manifest and existing Scout engine tests.

### Task 3: Strict Evidence Admission

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_scout_builder.py`
- Modify: `backend/theme_intelligence/industrial_graph/theme_scout_validator.py`
- Modify: `test_theme_scout_builder.py`
- Modify: `test_theme_scout_validator.py`

- [ ] Add failing tests for unknown candidate, cluster, path, influence, and
  bottleneck evidence references.
- [ ] Replace silent filtering with explicit validation errors.
- [ ] Require non-empty citations for every activated candidate evidence row.
- [ ] Run builder and validator suites.

### Task 4: Manual And Offline Providers

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_scout_providers.py`
- Modify: `test_theme_scout_providers.py`

- [ ] Add failing tests for in-memory immutability, frozen file bytes, stable
  file checksum, and repeatable output.
- [ ] Implement `ManualThemeScoutProposalProvider`.
- [ ] Implement `OfflineFileThemeScoutProposalProvider`.
- [ ] Ensure no network package or runtime provider is imported.
- [ ] Run provider tests.

### Task 5: CLI And Isolation Guard

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_cli.py`
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_isolation.py`
- Create: `test_theme_scout_cli.py`
- Create: `test_theme_scout_isolation.py`

- [ ] Add failing tests for all six commands and production activation gates.
- [ ] Implement canonical JSON output and non-zero exit behavior.
- [ ] Fingerprint graph, controller, opportunity, and packet tables before and
  after activation.
- [ ] On isolation mismatch, restore the prior active Scout snapshot or remove
  the newly activated first snapshot transactionally.
- [ ] Run CLI, isolation, snapshot, and repository tests.

### Task 6: Scout Snapshot Metadata

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_scout_exports.py`
- Modify: `frontend/src/types/stock.ts`
- Modify: `frontend/src/components/ThemeScoutPage.tsx`
- Modify: `frontend/src/lib/themeScout.test.ts`

- [ ] Add provider, prompt, evidence checksum, and proposal checksum fields to
  the frontend response type.
- [ ] Render compact read-only metadata in the Scout header.
- [ ] Keep activation controls absent.
- [ ] Run frontend unit tests and TypeScript.

### Task 7: End-to-End Verification

**Files:**
- Create only a proposal template or test fixture; do not create an unreviewed
  production proposal.

- [ ] Export the canonical active-graph evidence manifest.
- [ ] Validate a dry-run empty proposal.
- [ ] Validate and build a non-empty test fixture against a temporary database.
- [ ] Run the full backend pytest suite.
- [ ] Run `npx tsc --noEmit` and `npm run build`.
- [ ] Run `verify-isolation` against the canonical database.
- [ ] If and only if a separately reviewed non-empty production proposal file
  exists, activate it and audit the first snapshot.
- [ ] Inspect the Scout workspace at `http://127.0.0.1:3000/`.

