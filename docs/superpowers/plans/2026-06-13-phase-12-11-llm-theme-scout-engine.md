# Phase 12.11 LLM Theme Scout Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persisted-evidence-only Theme Scout that freezes structured LLM proposals, deterministically ranks research candidates, preserves explicit lifecycle review, and exposes a separate dense Scout workspace without writing to the Industrial Graph.

**Architecture:** Scout is an independent immutable snapshot family before the Industrial Graph. An explicit proposal provider receives one frozen persisted evidence bundle and returns structured candidate proposals; deterministic builder, validator, repository, and engine layers admit cited evidence, calculate metrics and readiness, stage records, and transactionally activate one Scout snapshot. Read-only APIs and a separate frontend workspace expose candidate intelligence while keeping candidate, graph, and investment truth states visibly separate.

**Tech Stack:** Python 3.12, FastAPI, SQLite, dataclasses, canonical JSON/SHA-256, `requests`, pytest, Next.js, React, TypeScript, Vitest, in-app Browser.

---

## Approved Invariants

- Scout consumes persisted evidence only.
- No provider call occurs at startup or from a GET request.
- A model proposal is frozen input, not evidence.
- Every admitted evidence row retains source table, row ID, timestamp,
  identifier, citation, source value, and content hash.
- Candidate creation starts at `DISCOVERED`.
- `APPROVED` requires an explicit actor, reason, and immutable transition
  snapshot.
- Scout cannot create or mutate graph nodes, graph edges, graph evidence,
  Controller, Opportunity, Decision Packet, or Committee records.
- Duplicate evidence contributes once.
- Default ranking starts with Bottleneck Potential, not Theme Score or Novelty.
- Identical evidence bundle, proposal payload, algorithm version, and
  configuration produce identical output.
- Scout activation is transactional and independent from downstream snapshots.
- The six UX examples are not production seed records.

## Files

Create:

- `backend/theme_intelligence/industrial_graph/theme_scout_models.py`
- `backend/theme_intelligence/industrial_graph/theme_scout_builder.py`
- `backend/theme_intelligence/industrial_graph/theme_scout_validator.py`
- `backend/theme_intelligence/industrial_graph/theme_scout_engine.py`
- `backend/theme_intelligence/industrial_graph/theme_scout_repository.py`
- `backend/theme_intelligence/industrial_graph/theme_scout_exports.py`
- `frontend/src/components/ThemeScoutPage.tsx`
- `frontend/src/lib/themeScout.ts`
- `frontend/src/lib/themeScout.test.ts`
- `test_theme_scout_models.py`
- `test_theme_scout_engine.py`
- `test_theme_scout_builder.py`
- `test_theme_scout_validator.py`
- `test_theme_scout_repository.py`
- `test_theme_scout_snapshots.py`
- `test_theme_scout_integration.py`

Modify:

- `backend/theme_intelligence/storage/theme_repository.py`
- `backend/theme_intelligence/industrial_graph/__init__.py`
- `backend/settings.py`
- `backend/main.py`
- `frontend/src/types/stock.ts`
- `frontend/src/services/stockApi.ts`
- `frontend/src/modules/terminalModules.ts`
- `frontend/src/modules/terminalModules.test.ts`
- `frontend/src/context/WorkspaceContext.tsx`
- `frontend/src/components/Dashboard.tsx`
- `frontend/src/components/GlobalStockSearch.tsx`
- `frontend/src/app/globals.css`

Do not modify:

- Industrial Graph builders or validators;
- Controller Engine;
- Hidden Opportunity Engine;
- Decision Packet Engine;
- Committee logic;
- quote providers or quote cache behavior;
- portfolio logic;
- Theme Research aggregate contracts;
- Phase 10 theme-overlap graph APIs.

### Task 1: Define Scout Models, Canonicalization, And Checksums

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_models.py`
- Create: `test_theme_scout_models.py`

- [ ] **Step 1: Write failing model tests**

Cover:

```python
def test_candidate_key_is_deterministic() -> None:
    assert canonical_candidate_key("AI Power Grid") == "candidate:ai-power-grid"


def test_provider_cannot_create_approved_candidate() -> None:
    proposal = make_proposal(lifecycle_status="APPROVED")
    with pytest.raises(ValueError, match="DISCOVERED"):
        proposal.validate()


def test_candidate_checksum_ignores_database_identity() -> None:
    first = make_candidate(id=None, created_at="")
    second = make_candidate(id=99, created_at="later")
    assert candidate_checksum(first) == candidate_checksum(second)
```

Also test:

- allowed lifecycle and snapshot states;
- allowed evidence domain and path types;
- score bounds;
- non-negative counts;
- canonical evidence ordering;
- canonical JSON serialization;
- duplicate evidence identity;
- invalid lifecycle transitions.

- [ ] **Step 2: Run the model test and confirm import failure**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_scout_models.py -q
```

Expected: failure because `theme_scout_models` does not exist.

- [ ] **Step 3: Implement model contracts**

Define immutable dataclasses:

```python
ScoutSourceEvidence
ThemeScoutProposal
ThemeScoutProposalCandidate
ThemeScoutSignalCluster
ThemeScoutPath
ThemeScoutMetrics
ThemeScoutResearchReadiness
ThemeScoutCandidate
ThemeScoutSnapshot
ThemeScoutBuild
```

Define:

```python
LIFECYCLE_STATES
LIFECYCLE_TRANSITIONS
SNAPSHOT_STATES
EVIDENCE_DOMAIN_TYPES
PATH_TYPES
DEFAULT_SCOUT_WEIGHTS
DEFAULT_READINESS_THRESHOLD
canonical_candidate_key()
canonical_json()
content_checksum()
candidate_checksum()
snapshot_checksum()
```

Database IDs and timestamps assigned by persistence must not affect content
checksums.

- [ ] **Step 4: Run the model tests**

Expected: all model tests pass.

- [ ] **Step 5: Commit the isolated model change**

```powershell
git add backend/theme_intelligence/industrial_graph/theme_scout_models.py test_theme_scout_models.py
git commit -m "feat: define theme scout models"
```

### Task 2: Add The Five Scout Tables Additively

**Files:**
- Modify: `backend/theme_intelligence/storage/theme_repository.py`
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_repository.py`
- Create: `test_theme_scout_repository.py`

- [ ] **Step 1: Write failing schema tests**

Assert that `ThemeRepository.initialize()` creates:

```text
theme_scout_snapshots
theme_candidates
theme_candidate_evidence
theme_candidate_paths
theme_candidate_influence_maps
```

Assert:

- all required columns exist;
- foreign keys point to the Scout parent rows;
- candidate identity and rank are unique per snapshot;
- evidence and path order are unique per candidate;
- existing graph, controller, opportunity, and packet tables are unchanged.

- [ ] **Step 2: Run repository tests and confirm missing tables**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_scout_repository.py -q
```

Expected: failure naming the missing Scout tables.

- [ ] **Step 3: Add schema through `ThemeRepository.initialize()`**

Use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`.

Do not:

- drop or rename tables;
- rewrite existing rows;
- add Scout columns to downstream Phase 12 tables.

- [ ] **Step 4: Add the dedicated Scout repository**

Implement `ThemeScoutRepository` as a focused wrapper over `ThemeRepository`.
Add active Scout snapshot readers and deterministic row mapping helpers. Keep
write operations for later tasks.

- [ ] **Step 5: Run repository and existing graph schema tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_scout_repository.py test_graph_snapshot.py test_controller_persistence.py test_opportunity_snapshot.py test_decision_packet_snapshot.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit schema work**

```powershell
git add backend/theme_intelligence/storage/theme_repository.py backend/theme_intelligence/industrial_graph/theme_scout_repository.py test_theme_scout_repository.py
git commit -m "feat: add theme scout snapshot schema"
```

### Task 3: Build Persisted Evidence Adapters

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_builder.py`
- Create: `test_theme_scout_builder.py`

- [ ] **Step 1: Write failing evidence-admission tests**

Use temporary SQLite fixtures with persisted rows.

Required assertions:

```python
def test_missing_citation_is_not_admitted() -> None: ...
def test_missing_source_identifier_is_not_admitted() -> None: ...
def test_duplicate_content_contributes_once() -> None: ...
def test_runtime_cache_row_is_not_an_allowed_source() -> None: ...
def test_source_watermark_excludes_newer_rows() -> None: ...
```

Cover eligible adapters for currently supported persisted tables:

```text
theme_mentions
theme_catalysts
theme_bottlenecks
theme_entities
graph_evidence
```

Only retain rows that satisfy every provenance requirement.

- [ ] **Step 2: Run builder tests and confirm failure**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_scout_builder.py -q
```

- [ ] **Step 3: Implement evidence bundle creation**

Add:

```python
ThemeScoutEvidenceAdapter
build_evidence_bundle(connection, source_watermark)
evidence_bundle_checksum(evidence)
```

Use explicit table adapters. Do not use a generic `SELECT *` or accept arbitrary
tables.

Map domain types only when persisted fields provide a deterministic mapping.
Otherwise use `Other`.

- [ ] **Step 4: Add rejection audit data**

Return structured rejection counters:

```text
unknown_source_type
missing_timestamp
missing_identifier
missing_citation
missing_content
duplicate_content
after_watermark
```

Do not synthesize missing citation or timestamps.

- [ ] **Step 5: Run builder tests**

Expected: evidence admission tests pass.

- [ ] **Step 6: Commit evidence adapter work**

```powershell
git add backend/theme_intelligence/industrial_graph/theme_scout_builder.py test_theme_scout_builder.py
git commit -m "feat: admit persisted scout evidence"
```

### Task 4: Add The Explicit Proposal Provider Boundary

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_scout_models.py`
- Modify: `backend/theme_intelligence/industrial_graph/theme_scout_builder.py`
- Modify: `backend/settings.py`
- Modify: `test_theme_scout_builder.py`

- [ ] **Step 1: Write failing provider-boundary tests**

Test:

- no provider configured raises `ThemeScoutProviderUnavailable`;
- fixed provider receives only the frozen evidence bundle;
- proposal references unknown evidence IDs are rejected;
- proposal payload checksum is stable;
- provider output cannot set `APPROVED`;
- provider prose is stored only as `generated_candidate_summary`.

- [ ] **Step 2: Add provider protocol**

Define:

```python
class ThemeScoutProposalProvider(Protocol):
    provider_name: str
    provider_model: str
    prompt_version: str

    def propose(
        self,
        evidence: tuple[ScoutSourceEvidence, ...],
    ) -> ThemeScoutProposal: ...
```

- [ ] **Step 3: Add optional OpenAI-compatible adapter**

Use `requests` with explicit timeout and structured JSON response validation.
Read only:

```text
THEME_SCOUT_LLM_BASE_URL
THEME_SCOUT_LLM_API_KEY
THEME_SCOUT_LLM_MODEL
THEME_SCOUT_LLM_PROMPT_VERSION
```

Do not add a startup call, fallback model, or silent exception handling.

- [ ] **Step 4: Add settings**

Add optional settings with empty defaults. Redact the API key from logs,
snapshots, checksums, and error detail.

- [ ] **Step 5: Run focused tests**

Expected: provider protocol and fixed-provider tests pass without network.

- [ ] **Step 6: Commit provider boundary**

```powershell
git add backend/theme_intelligence/industrial_graph/theme_scout_models.py backend/theme_intelligence/industrial_graph/theme_scout_builder.py backend/settings.py test_theme_scout_builder.py
git commit -m "feat: add explicit scout proposal provider"
```

### Task 5: Implement Deterministic Candidate Construction And Scoring

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_scout_builder.py`
- Modify: `test_theme_scout_builder.py`

- [ ] **Step 1: Write failing scoring tests**

Assert exact formulas for:

- Novelty;
- Velocity;
- Breadth;
- Capital;
- Bottleneck Potential;
- Confidence;
- Serendipity;
- Theme Score;
- Research Readiness.

Assert default rank order:

```text
bottleneck, confidence, velocity, novelty, breadth, capital, candidate_key
```

Test that:

- source spam does not increase scores;
- duplicated evidence does not increase scores;
- missing capital evidence is not favorable;
- Serendipity does not alter Theme Score;
- every raw and normalized input is persisted.

- [ ] **Step 2: Implement cluster validation and construction**

Implement:

```python
build_signal_clusters()
clusters_are_independent()
```

Require two valid independent clusters per admitted candidate.

- [ ] **Step 3: Implement metrics**

Implement named pure functions for every score. Clamp only at the public score
boundary; reject invalid raw inputs rather than masking them.

- [ ] **Step 4: Implement Theme Evolution and bottleneck paths**

Retain a path only when every step references admitted evidence. Mark
bottleneck paths as `potential`.

- [ ] **Step 5: Implement readiness and handoff eligibility**

Use the exact formula and threshold in the design specification. Handoff
eligibility is a boolean result only; it creates no downstream records.

- [ ] **Step 6: Run builder tests twice**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_scout_builder.py -q
.\backend\.venv\Scripts\python.exe -m pytest test_theme_scout_builder.py -q
```

Expected: identical deterministic output in both runs.

- [ ] **Step 7: Commit deterministic builder**

```powershell
git add backend/theme_intelligence/industrial_graph/theme_scout_builder.py test_theme_scout_builder.py
git commit -m "feat: build deterministic theme candidates"
```

### Task 6: Implement Full Snapshot Validation

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_validator.py`
- Create: `test_theme_scout_validator.py`

- [ ] **Step 1: Write failing validator tests**

Required rejection tests:

```text
unknown lifecycle state
automatic approved candidate
invalid lifecycle transition
duplicate candidate identity
duplicate rank
score outside 0..100
negative counts
missing timestamp
missing identifier
missing citation
missing content hash
unknown source table
duplicate evidence contribution
invalid cluster
non-independent clusters
unsupported evolution step
unsupported bottleneck path
missing path evidence
inconsistent readiness
generated summary admitted as evidence
downstream graph/controller/opportunity/packet write marker
unsupported influence-map item
checksum mismatch
non-deterministic ordering
```

- [ ] **Step 2: Implement `ThemeScoutValidator`**

Expose:

```python
validate_build(build: ThemeScoutBuild) -> None
validate_transition(previous, next_candidate) -> None
```

Collect deterministic error codes and raise one validation exception containing
the sorted failures.

- [ ] **Step 3: Run validator tests**

Expected: all rejection and valid-build tests pass.

- [ ] **Step 4: Commit validator**

```powershell
git add backend/theme_intelligence/industrial_graph/theme_scout_validator.py test_theme_scout_validator.py
git commit -m "feat: validate theme scout snapshots"
```

### Task 7: Implement Transactional Snapshot Persistence And Lifecycle Revisions

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_scout_repository.py`
- Modify: `test_theme_scout_repository.py`
- Create: `test_theme_scout_snapshots.py`

- [ ] **Step 1: Write failing snapshot tests**

Assert:

- stage writes one immutable snapshot family;
- activation supersedes the previous active snapshot;
- activation rollback leaves the previous active snapshot unchanged;
- failed validation writes no active candidate rows;
- repeated identical builds have identical content checksums;
- candidate transition creates a new snapshot revision;
- approval without actor or reason fails;
- rollback can reactivate the previous valid revision;
- graph/controller/opportunity/packet statuses are unchanged.

- [ ] **Step 2: Implement stage and activate methods**

Add:

```python
stage_theme_scout_snapshot()
activate_theme_scout_snapshot()
rollback_theme_scout_snapshot()
```

Activation uses `BEGIN IMMEDIATE`. Perform status updates and final checksum
verification in the same transaction.

- [ ] **Step 3: Implement active reads**

Add:

```python
get_active_theme_scout_snapshot()
list_theme_candidates()
get_theme_candidate()
```

Default reads are active-snapshot-only and use the approved deterministic
ordering.

- [ ] **Step 4: Implement lifecycle transition snapshots**

Add:

```python
transition_theme_candidate(
    candidate_key,
    next_status,
    actor,
    reason,
    changed_at,
)
```

Clone the full active snapshot, modify exactly one lifecycle record, validate,
stage, and activate. Never update an active candidate row in place.

- [ ] **Step 5: Run repository and snapshot tests**

Expected: all transaction and rollback tests pass.

- [ ] **Step 6: Commit persistence**

```powershell
git add backend/theme_intelligence/industrial_graph/theme_scout_repository.py test_theme_scout_repository.py test_theme_scout_snapshots.py
git commit -m "feat: persist theme scout snapshots"
```

### Task 8: Implement The Scout Engine

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_engine.py`
- Modify: `backend/theme_intelligence/industrial_graph/__init__.py`
- Create: `test_theme_scout_engine.py`

- [ ] **Step 1: Write failing engine tests**

Cover:

- explicit build with fixed provider;
- no provider configured;
- provider failure preserves active snapshot;
- validation failure preserves active snapshot;
- staging failure preserves active snapshot;
- identical frozen input produces identical output;
- audit result contains watermark, source counts, rejection counts, provider
  identity, proposal checksum, candidate count, and activated version;
- no graph or downstream snapshot is activated.

- [ ] **Step 2: Implement `ThemeScoutEngine`**

Public internal methods:

```python
build_and_activate(source_watermark=None) -> ThemeScoutBuildAudit
transition_candidate(...) -> ThemeScoutBuildAudit
get_active_snapshot()
```

Do not call `build_and_activate()` from application startup.

- [ ] **Step 3: Export Scout contracts**

Update `industrial_graph/__init__.py` without changing existing exports.

- [ ] **Step 4: Run engine tests**

Expected: all engine tests pass.

- [ ] **Step 5: Commit engine**

```powershell
git add backend/theme_intelligence/industrial_graph/theme_scout_engine.py backend/theme_intelligence/industrial_graph/__init__.py test_theme_scout_engine.py
git commit -m "feat: add theme scout engine"
```

### Task 8A: Implement Deterministic Scout Exports

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/theme_scout_exports.py`
- Modify: `backend/theme_intelligence/industrial_graph/__init__.py`
- Modify: `test_theme_scout_integration.py`

- [ ] **Step 1: Write failing export tests**

Assert exports include one exact Scout snapshot with candidates, evidence,
paths, and influence maps in deterministic order. Influence-map items remain
explicit hypotheses and downstream graph/controller/opportunity/packet records
are excluded.

- [ ] **Step 2: Implement export functions**

```python
export_theme_scout_snapshot(repository, scout_version=None)
export_theme_candidate(repository, candidate_key, scout_version=None)
```

- [ ] **Step 3: Run export tests**

Expected: deterministic export assertions pass.

### Task 9: Add Read-Only Scout APIs

**Files:**
- Modify: `backend/main.py`
- Create: `test_theme_scout_integration.py`

- [ ] **Step 1: Write failing API tests**

Test:

```text
GET /api/theme/scout
GET /api/theme/scout/{candidate_key}
```

Required behavior:

- `200` with explicit unavailable state when no active snapshot exists;
- deterministic candidate ordering;
- active snapshot metadata included;
- candidate detail returns evidence, paths, readiness, and handoff eligibility;
- unknown candidate returns `404`;
- generated summaries are labeled and not listed as evidence;
- no route invokes a proposal provider;
- no existing Theme aggregate contract changes.

- [ ] **Step 2: Add response mapping helpers**

Map repository models to JSON without exposing:

- API keys;
- provider request payloads;
- internal database paths;
- mutable repository objects.

- [ ] **Step 3: Add GET routes**

Keep route handlers read-only. Do not add build, transition, approval, rejection,
or handoff routes.

- [ ] **Step 4: Run integration and aggregate regressions**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_scout_integration.py test_theme_intelligence_aggregate_api.py test_theme_api_contracts.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit API work**

```powershell
git add backend/main.py test_theme_scout_integration.py
git commit -m "feat: expose theme scout reads"
```

### Task 10: Add Typed Frontend Contracts And Client Mapping

**Files:**
- Modify: `frontend/src/types/stock.ts`
- Modify: `frontend/src/services/stockApi.ts`
- Create: `frontend/src/lib/themeScout.ts`
- Create: `frontend/src/lib/themeScout.test.ts`

- [ ] **Step 1: Write failing TypeScript tests**

Cover:

- response parsing;
- explicit unavailable fields;
- deterministic ranking comparator;
- lifecycle labels;
- handoff eligibility;
- candidate-versus-theme search identity;
- stale request abort behavior at the client boundary.

- [ ] **Step 2: Define Scout response types**

Add explicit types for:

```text
ThemeScoutSnapshotSummary
ThemeScoutCandidateSummary
ThemeScoutCandidateDetail
ThemeScoutEvidence
ThemeScoutPath
ThemeScoutReadiness
```

Extend target tab and search result unions with `scout`.

- [ ] **Step 3: Add client functions**

Add:

```typescript
fetchThemeScout(signal?: AbortSignal)
fetchThemeScoutCandidate(candidateKey: string, signal?: AbortSignal)
```

Use the existing API base URL and error conventions. Do not use stock quote
cache paths.

- [ ] **Step 4: Add pure presentation mapping**

`themeScout.ts` converts API availability states to truthful display values and
implements the approved ranking comparator.

- [ ] **Step 5: Run focused frontend tests**

```powershell
cd frontend
npx vitest run src/lib/themeScout.test.ts
```

Expected: all pass.

- [ ] **Step 6: Commit frontend contracts**

```powershell
git add frontend/src/types/stock.ts frontend/src/services/stockApi.ts frontend/src/lib/themeScout.ts frontend/src/lib/themeScout.test.ts
git commit -m "feat: add theme scout frontend contracts"
```

### Task 11: Register Scout Navigation And Search Routing

**Files:**
- Modify: `frontend/src/modules/terminalModules.ts`
- Modify: `frontend/src/modules/terminalModules.test.ts`
- Modify: `frontend/src/context/WorkspaceContext.tsx`
- Modify: `frontend/src/components/Dashboard.tsx`
- Modify: `frontend/src/components/GlobalStockSearch.tsx`
- Modify: `frontend/src/lib/searchRouting.test.ts`

- [ ] **Step 1: Write failing navigation and routing tests**

Assert primary order:

```text
Themes, Scout, Supply Chain, Stocks
```

Assert:

- active candidate exact match routes to Scout;
- verified Theme exact match routes to Themes;
- ticker exact match routes to Stocks;
- supply-chain entity routing remains unchanged;
- candidate result visibly carries `DISCOVERED`, `OBSERVING`, `VALIDATING`,
  `APPROVED`, or `REJECTED`.

- [ ] **Step 2: Register the Scout module**

Use an order between Themes and Supply Chain and a dedicated workspace view.

- [ ] **Step 3: Add lazy Scout page routing**

Lazy-load `ThemeScoutPage`. Do not map it to `ThemeResearchPage`.

- [ ] **Step 4: Extend search result rendering**

Render a candidate badge and lifecycle state. Do not show candidate examples as
search records when the API has no candidate.

- [ ] **Step 5: Run navigation and search tests**

```powershell
cd frontend
npx vitest run src/modules/terminalModules.test.ts src/lib/searchRouting.test.ts
```

Expected: all pass.

- [ ] **Step 6: Commit navigation work**

```powershell
git add frontend/src/modules/terminalModules.ts frontend/src/modules/terminalModules.test.ts frontend/src/context/WorkspaceContext.tsx frontend/src/components/Dashboard.tsx frontend/src/components/GlobalStockSearch.tsx frontend/src/lib/searchRouting.test.ts
git commit -m "feat: register theme scout workspace"
```

### Task 12: Build The Dense Theme Scout Workspace

**Files:**
- Create: `frontend/src/components/ThemeScoutPage.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/lib/themeScout.test.ts`

- [ ] **Step 1: Write failing rendering tests**

Test:

- truthful no-snapshot empty state;
- examples have unavailable metrics and are labeled examples;
- ranked candidates render Bottleneck Potential first;
- selecting a candidate loads detail once;
- stale detail requests abort;
- lifecycle, readiness, evidence, clusters, evolution, bottlenecks, and handoff
  render from the API;
- generated summary is labeled generated candidate context;
- candidate-versus-graph warning is always visible;
- no Controller, Opportunity, Packet, recommendation, target, or allocation
  block is rendered.

- [ ] **Step 2: Implement ranking pane**

Use a dense table and compact filter header. Default sorting follows the backend
rank and approved metric priority.

- [ ] **Step 3: Implement detail pane**

Add compact sections:

```text
Overview
Signals
Evidence
Theme Evolution
Potential Bottlenecks
Research Readiness
Research Pipeline Handoff
```

Use content-driven height. Avoid fixed-height empty panels.

- [ ] **Step 4: Implement truthful empty state**

Display the six approved labels as non-record examples only:

```text
Reusable Rockets
Starlink Economy
AI Power Grid
Nuclear SMR
Humanoid Robotics
Defense Drones
```

All metrics, evidence, status, and paths remain unavailable.

- [ ] **Step 5: Add styling**

Follow existing design tokens and terminal primitives. Preserve Chinese-first
labels where established and add concise English secondary labels.

- [ ] **Step 6: Run frontend tests and typecheck**

```powershell
cd frontend
npx vitest run src/lib/themeScout.test.ts src/modules/terminalModules.test.ts src/lib/searchRouting.test.ts
npx tsc --noEmit
```

Expected: tests and typecheck pass.

- [ ] **Step 7: Commit workspace UI**

```powershell
git add frontend/src/components/ThemeScoutPage.tsx frontend/src/app/globals.css frontend/src/lib/themeScout.test.ts
git commit -m "feat: add theme scout workspace"
```

### Task 13: Run Full Backend And Frontend Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run all seven Scout backend suites**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_scout_models.py test_theme_scout_engine.py test_theme_scout_builder.py test_theme_scout_validator.py test_theme_scout_repository.py test_theme_scout_snapshots.py test_theme_scout_integration.py -q
```

Expected: all pass.

- [ ] **Step 2: Run full backend regression**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest
```

Expected: all pass.

- [ ] **Step 3: Run frontend verification**

```powershell
cd frontend
npx vitest run
npx tsc --noEmit
npm run build
```

Expected: tests, typecheck, and production build pass.

- [ ] **Step 4: Audit canonical database**

Using `backend/.cache/market_cache.sqlite3`, report:

```text
Scout snapshot count
active Scout snapshot count
candidate count
candidate evidence count
candidate path count
active Graph/Controller/Opportunity/Packet versions
```

Confirm Scout activation did not alter downstream lineage.

### Task 14: Browser Validation And Screenshots

**Files:**
- Create screenshots under `reports/`.

- [ ] **Step 1: Start canonical local topology**

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000
Database: backend/.cache/market_cache.sqlite3
```

- [ ] **Step 2: Validate Scout placement**

Confirm navigation order and that Scout opens a distinct workspace.

- [ ] **Step 3: Validate truthful empty state or active snapshot**

Inspect:

```text
Reusable Rockets
Starlink Economy
AI Power Grid
Nuclear SMR
Humanoid Robotics
Defense Drones
```

When no active snapshot exists, confirm all are examples with unavailable
metrics. When a validated fixture snapshot is explicitly loaded for browser
testing, confirm every displayed value maps to persisted fixture evidence.

- [ ] **Step 4: Validate candidate detail**

Inspect:

- lifecycle visibility;
- Bottleneck-first ranking;
- evidence clusters;
- evidence citations;
- Theme Evolution support;
- Potential Bottleneck truth state;
- readiness percentages;
- hypothetical influence-map targets and evidence;
- handoff eligibility;
- candidate-versus-graph separation.

- [ ] **Step 5: Inspect browser diagnostics**

Confirm:

- no hydration errors;
- no duplicate React keys;
- no stale candidate detail;
- no duplicate Scout requests;
- no mojibake;
- no quote calls;
- no provider calls;
- no generated stock recommendation content.

- [ ] **Step 6: Capture before and after screenshots**

Save:

```text
reports/phase1211-scout-empty-state.png
reports/phase1211-scout-ranking.png
reports/phase1211-scout-candidate-detail.png
reports/phase1211-scout-readiness-handoff.png
```

### Task 15: Final Acceptance Audit

**Files:**
- Verify only.

- [ ] **Step 1: Check design invariants against implementation**

Confirm:

- five additive tables only;
- no Scout write in downstream engines;
- no startup model call;
- no GET-triggered model call;
- no auto approval;
- no fabricated evidence;
- no example seeds;
- explicit source provenance;
- deterministic checksums;
- transactional rollback;
- Bottleneck-first default ranking.

- [ ] **Step 2: Produce the final report**

Include:

- architecture findings;
- changed files;
- schema audit;
- snapshot audit;
- candidate audit;
- proposal-provider boundary;
- lifecycle and approval audit;
- metric and ranking summary;
- readiness and handoff summary;
- browser screenshots;
- backend and frontend verification results;
- known limitations.

- [ ] **Step 3: Use verification-before-completion**

Do not state PASS until the exact commands above have completed successfully and
browser evidence has been inspected.
