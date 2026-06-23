# Phase 12.2 Industrial Knowledge Graph Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, provenance-first industrial graph foundation backed by SQLite snapshots without changing existing APIs, frontend behavior, portfolio logic, or Phase 10 theme graph contracts.

**Architecture:** Add an independent `theme_intelligence.industrial_graph` package that owns canonical graph models, persistence, validation, snapshot activation, deterministic Phase 10 evidence adapters, and NetworkX export. `ThemeRepository.initialize()` remains the single additive schema bootstrap, while `IndustrialGraphRepository` owns graph reads and writes. Builds are assembled and validated before persistence, staged under a build version, and activated with one SQLite transaction.

**Tech Stack:** Python 3, SQLite, dataclasses, hashlib/JSON from the standard library, NetworkX `MultiDiGraph`, pytest.

---

## Scope And File Map

**Create**

- `backend/theme_intelligence/industrial_graph/__init__.py`: internal exports only.
- `backend/theme_intelligence/industrial_graph/graph_models.py`: taxonomies and immutable node, edge, evidence, snapshot, and build records.
- `backend/theme_intelligence/industrial_graph/graph_repository.py`: graph persistence and active-snapshot reads.
- `backend/theme_intelligence/industrial_graph/graph_builder.py`: deterministic adapters for persisted Phase 10 and curated seed evidence.
- `backend/theme_intelligence/industrial_graph/graph_validator.py`: pre-activation validation.
- `backend/theme_intelligence/industrial_graph/graph_snapshot.py`: build orchestration, checksum, staging, and transactional activation.
- `test_graph_nodes.py`
- `test_graph_edges.py`
- `test_graph_evidence.py`
- `test_graph_builder.py`
- `test_graph_validation.py`
- `test_graph_snapshot.py`
- `test_graph_networkx_export.py`

**Modify**

- `backend/theme_intelligence/storage/theme_repository.py`: additive/idempotent schema only.
- `backend/theme_intelligence/seeds/seed_loader.py`: invoke the industrial graph snapshot builder after persisted Phase 10 outputs exist; do not alter API payloads.
- `requirements.txt`: declare NetworkX.
- `backend/requirements.txt`: declare NetworkX.

**Explicitly unchanged**

- `backend/theme_intelligence/graph/*`
- `backend/theme_intelligence/aggregate.py`
- `backend/main.py` public routes and contracts
- `backend/theme_intelligence/portfolio/*`
- `frontend/*`

## Approved Semantic Boundary

The builder may create only relationships directly supported by persisted semantics:

- A persisted bottleneck creates a `Constraint` node and `Constraint LIMITS Theme`.
- A persisted bottleneck controller creates `Company CONTROLS Constraint`.
- A persisted resolution enabler creates `Company RESOLVES Constraint`.
- A persisted equipment-role entity creates an `Equipment` node and `Company PRODUCED_BY` is **not** emitted because the stored record does not prove manufacturing ownership.
- A persisted company/theme association may create nodes and evidence without forcing an edge when the approved relationship taxonomy cannot express the fact honestly.
- Catalysts become evidence for supported edges; they do not become nodes because `Catalyst` is not an approved Phase 12.2 node type.
- No inverse edge is synthesized.

This intentionally produces a conservative graph. Rich process, material, facility, patent, standard, and country edges require later approved research or richer curated industrial seed facts.

### Task 1: Taxonomies And Immutable Models

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/graph_models.py`
- Create: `backend/theme_intelligence/industrial_graph/__init__.py`
- Test: `test_graph_nodes.py`
- Test: `test_graph_edges.py`
- Test: `test_graph_evidence.py`

- [ ] **Step 1: Write failing model tests**

Test that:

- all 17 approved node types are accepted;
- all 18 approved relationships are accepted;
- unknown values raise `ValueError`;
- canonical keys are lowercase deterministic slugs, while ticker-backed company keys preserve an explicit `company:<TICKER>` namespace;
- aliases and external IDs are sorted before serialization;
- node, edge, and evidence identity keys exclude database IDs and generated timestamps.

- [ ] **Step 2: Run the focused tests and confirm import failures**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_graph_nodes.py test_graph_edges.py test_graph_evidence.py -q
```

Expected: collection fails because `theme_intelligence.industrial_graph` does not exist.

- [ ] **Step 3: Implement taxonomies and records**

Define:

```python
NODE_TYPES = frozenset({
    "Theme", "Technology", "Process", "Material", "Equipment", "Company",
    "Supplier", "Customer", "Industry", "Patent", "Standard", "Country",
    "Constraint", "Facility", "Product", "Capacity", "Certification",
})

RELATIONSHIP_TYPES = frozenset({
    "USES", "REQUIRES", "DEPENDS_ON", "SUPPLIED_BY", "PRODUCED_BY",
    "SUPPLIES", "CUSTOMER_OF", "COMPETES_WITH", "ENABLES", "CONTROLS",
    "PROTECTS", "LIMITS", "RESOLVES", "OWNS", "HAS_CAPACITY", "LICENSES",
    "PROCESS_PRECEDES_PROCESS", "MATERIAL_SUBSTITUTES_FOR",
})
```

Add frozen dataclasses:

- `IndustrialGraphNode`
- `IndustrialGraphEdge`
- `IndustrialGraphEvidence`
- `IndustrialGraphEdgeEvidence`
- `IndustrialGraphSnapshot`
- `IndustrialGraphBuild`

Use UTC ISO timestamps and deterministic JSON helpers. Clamp confidence and dependency values to `0..100`.

- [ ] **Step 4: Export internal interfaces**

Export models, taxonomies, builder, validator, repository, snapshot service, and `export_to_networkx` from `industrial_graph/__init__.py`. Do not export them from `theme_intelligence/__init__.py`.

- [ ] **Step 5: Re-run focused tests**

Expected: model tests pass.

### Task 2: Additive SQLite Schema

**Files:**
- Modify: `backend/theme_intelligence/storage/theme_repository.py`
- Test: `test_graph_nodes.py`
- Test: `test_graph_edges.py`
- Test: `test_graph_evidence.py`

- [ ] **Step 1: Add failing schema tests**

Initialize the same temporary database twice and assert:

- all five new tables exist;
- required columns exist;
- required unique indexes and read indexes exist;
- `PRAGMA foreign_keys` can enforce edge and link references through repository connections;
- the existing `theme_graph_edges` table remains present and unchanged.

- [ ] **Step 2: Run tests and confirm missing-table failures**

- [ ] **Step 3: Add schema to `ThemeRepository.initialize()`**

Create:

- `graph_nodes`
- `graph_edges`
- `graph_evidence`
- `graph_edge_evidence`
- `graph_snapshots`

Use the exact requested fields. Add foreign keys:

```sql
FOREIGN KEY(source_node_id) REFERENCES graph_nodes(id),
FOREIGN KEY(target_node_id) REFERENCES graph_nodes(id),
FOREIGN KEY(edge_id) REFERENCES graph_edges(id) ON DELETE CASCADE,
FOREIGN KEY(evidence_id) REFERENCES graph_evidence(id) ON DELETE CASCADE
```

Add:

```sql
UNIQUE(node_type, canonical_key)
UNIQUE(source_node_id, relationship_type, target_node_id, valid_from)
UNIQUE(source_type, source_record_id, content_hash)
PRIMARY KEY(edge_id, evidence_id)
```

Enable `PRAGMA foreign_keys = ON` in `ThemeRepository._connect()`.

- [ ] **Step 4: Add all required indexes**

Use explicit names:

- `idx_graph_nodes_type`
- `idx_graph_nodes_canonical_key`
- `idx_graph_nodes_status`
- `idx_graph_edges_source`
- `idx_graph_edges_target`
- `idx_graph_edges_relationship`
- `idx_graph_edges_build_status`
- `idx_graph_snapshots_build_version`
- `idx_graph_snapshots_status`

- [ ] **Step 5: Re-run schema tests**

Expected: idempotent schema tests pass.

### Task 3: Repository Persistence And Duplicate Enforcement

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/graph_repository.py`
- Test: `test_graph_nodes.py`
- Test: `test_graph_edges.py`
- Test: `test_graph_evidence.py`

- [ ] **Step 1: Write failing repository tests**

Cover:

- canonical node resolution and lookup;
- duplicate node rejection within one build and by the database uniqueness constraint;
- canonical evidence resolution;
- duplicate evidence rejection within one build and by the database uniqueness constraint;
- reuse of an unchanged node or evidence row in a later snapshot;
- edge insertion only after both endpoints exist;
- orphan-edge rejection through foreign keys and repository validation;
- edge/evidence attachment;
- deterministic ordered reads;
- active-build filtering.

- [ ] **Step 2: Run tests and confirm missing repository behavior**

- [ ] **Step 3: Implement `IndustrialGraphRepository`**

Required methods:

```python
initialize() -> None
resolve_nodes(conn, nodes) -> dict[tuple[str, str], int]
resolve_evidence(conn, evidence) -> dict[tuple[str, str, str], int]
insert_edges(conn, edges, node_ids) -> dict[tuple[str, str, str, str], int]
attach_evidence(conn, links, edge_ids, evidence_ids) -> int
get_nodes(node_ids: set[int] | None = None) -> list[IndustrialGraphNode]
get_edges(build_version: str | None = None, status: str | None = "active") -> list[IndustrialGraphEdge]
get_evidence_for_edge(edge_id: int) -> list[IndustrialGraphEvidence]
get_active_snapshot() -> IndustrialGraphSnapshot | None
export_to_networkx(build_version: str | None = None) -> nx.MultiDiGraph
```

Repository write methods accept an existing connection so snapshot staging and activation can share transaction ownership. Node and evidence resolution first queries by canonical identity, inserts only missing identities, and returns IDs for both existing and new rows. Validation remains responsible for rejecting duplicates inside a single build.

- [ ] **Step 4: Implement NetworkX export**

Select edges from the requested build, collect their endpoint IDs, and load only those nodes. Nodes use `(node_type, canonical_key)` tuple IDs. Attach persisted node fields as attributes. Each directed edge uses its database ID or deterministic edge identity as the multigraph key and includes relationship, confidence, dependency strength, build version, and evidence IDs.

- [ ] **Step 5: Re-run repository tests**

Expected: node, edge, and evidence tests pass.

### Task 4: Deterministic Builder And Evidence Adapters

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/graph_builder.py`
- Test: `test_graph_builder.py`

- [ ] **Step 1: Write failing deterministic-build tests**

Use a temporary `ThemeRepository` populated by `ThemeSeedLoader(...).load(recompute=False)`.

Assert:

- two builds from unchanged persisted inputs have identical node identities, edge identities, evidence identities, source watermark, and checksum input;
- no edge source references quotes, frontend state, runtime LLMs, endpoint cache, or portfolio outputs;
- every edge has one or more evidence links;
- controller and resolution relationships are directional only;
- unsupported beneficiary associations do not fabricate edges;
- all output lists are deterministically sorted.

- [ ] **Step 2: Run tests and confirm builder import failure**

- [ ] **Step 3: Implement identity normalization**

Use:

- themes: `theme:<normalized_theme_id>`
- companies: `company:<UPPERCASE_TICKER>`
- constraints: `constraint:<theme_id>:<normalized_bottleneck_name>`
- equipment nodes only from explicit equipment entity types, with canonical keys scoped by normalized role text where no product identifier exists.

Do not infer supplier/customer/manufacturer identity from a company’s beneficiary classification.

- [ ] **Step 4: Implement persisted evidence adapters**

Read only:

- `get_entities()`
- `get_beneficiaries()`
- `get_beneficiary_scores()`
- `get_catalysts()`
- `get_bottlenecks()`
- `TARGET_SEED_THEMES`

Evidence source types are allowlisted:

- `phase10:theme_entity`
- `phase10:beneficiary`
- `phase10:beneficiary_score`
- `phase10:catalyst`
- `phase10:bottleneck`
- `seed:curated`
- `research:approved`

Generate `source_record_id` from persisted natural keys, never transient row ordering. Generate `content_hash` from canonical JSON containing the exact persisted fields supporting the fact.

- [ ] **Step 5: Build conservative edges**

Emit:

- `Constraint LIMITS Theme`
- `Company CONTROLS Constraint`
- `Company RESOLVES Constraint`
- `Company ENABLES Theme` only for explicit persisted `Resolution Enabler` records

Create nodes without edges for unsupported facts so future approved adapters can use the canonical identities.

- [ ] **Step 6: Re-run builder tests**

Expected: deterministic builder tests pass.

### Task 5: Validation

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/graph_validator.py`
- Test: `test_graph_validation.py`

- [ ] **Step 1: Write one failing test per validation rule**

Cover:

- missing node type;
- missing canonical key;
- invalid node type;
- invalid relationship type;
- edge without evidence;
- orphan endpoint identity;
- duplicate canonical node;
- duplicate evidence identity;
- duplicate edge identity;
- forbidden source;
- empty citation;
- edge confidence or dependency outside bounds.

- [ ] **Step 2: Run tests and confirm validator import failure**

- [ ] **Step 3: Implement `GraphValidationError` and `GraphValidator`**

Return all discovered errors in deterministic order and raise once through:

```python
validate(build: IndustrialGraphBuild) -> None
```

The forbidden-source check rejects source types containing or beginning with:

- `quote`
- `yfinance`
- `frontend`
- `runtime_llm`
- `endpoint_cache`
- `portfolio`

- [ ] **Step 4: Re-run validation tests**

Expected: all validation cases pass.

### Task 6: Snapshot Staging And Transactional Activation

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/graph_snapshot.py`
- Test: `test_graph_snapshot.py`

- [ ] **Step 1: Write failing snapshot tests**

Assert:

- a validated build creates a `building` snapshot before activation;
- activation changes the prior active snapshot and edges to `superseded`;
- activation changes the new snapshot and edges to `active`;
- a forced error during activation rolls back all status changes;
- failed validation creates no active snapshot;
- counts and checksum match persisted rows;
- repeated unchanged builds have equal checksums but distinct build versions;
- active snapshot reads never expose staged edges.

- [ ] **Step 2: Run tests and confirm missing snapshot service**

- [ ] **Step 3: Implement deterministic checksum**

Hash canonical JSON of sorted node identities and attributes, edge identities and scores, evidence identities, and edge/evidence links. Exclude database IDs, generated timestamps, and build version.

- [ ] **Step 4: Implement `IndustrialGraphSnapshotService`**

Public internal interface:

```python
build_and_activate() -> IndustrialGraphSnapshot
stage(build: IndustrialGraphBuild) -> IndustrialGraphSnapshot
activate(build_version: str) -> IndustrialGraphSnapshot
```

`build_and_activate()` performs:

1. build in memory;
2. validate in memory;
3. stage nodes, evidence, edges, links, and snapshot;
4. verify staged counts/checksum;
5. activate with `BEGIN IMMEDIATE`;
6. commit only after every status update succeeds.

- [ ] **Step 5: Re-run snapshot tests**

Expected: snapshot tests pass, including rollback proof.

### Task 7: NetworkX Dependency And Export Verification

**Files:**
- Modify: `requirements.txt`
- Modify: `backend/requirements.txt`
- Test: `test_graph_networkx_export.py`

- [ ] **Step 1: Write failing export tests**

Assert:

- export returns `networkx.MultiDiGraph`;
- node count and edge count equal the active snapshot;
- parallel directed relationships are retained;
- no inverse edges appear unless persisted;
- attributes contain future analytics inputs;
- export of an empty database returns an empty `MultiDiGraph`.

- [ ] **Step 2: Add the dependency**

Add the same bounded requirement to both files:

```text
networkx>=3.4,<4
```

- [ ] **Step 3: Install into the repository virtual environment**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install "networkx>=3.4,<4"
```

- [ ] **Step 4: Run export tests**

Expected: NetworkX export tests pass.

### Task 8: Seed-Pipeline Integration Without Contract Changes

**Files:**
- Modify: `backend/theme_intelligence/seeds/seed_loader.py`
- Modify: `test_seed_loader.py`
- Test: `test_graph_builder.py`

- [ ] **Step 1: Add failing integration tests**

Assert:

- seed loading invokes industrial graph build only after Phase 10 evidence is persisted;
- the returned seed-loader payload remains backward compatible;
- a new optional `industrial_graph` status object may be added only if existing exact-contract tests permit it; otherwise log the result without changing the return payload;
- graph build failure is surfaced and does not activate a partial snapshot;
- the existing Phase 10 graph rebuild still runs unchanged.

- [ ] **Step 2: Run focused tests and confirm the missing integration**

- [ ] **Step 3: Integrate snapshot construction**

After `GraphEngine(self.repository).rebuild()`, call:

```python
IndustrialGraphSnapshotService(self.repository).build_and_activate()
```

Do not import or call quote, cache, frontend, aggregate, portfolio, or API modules from the industrial graph package.

- [ ] **Step 4: Re-run focused seed and graph tests**

Expected: integration passes and existing aggregate/API tests remain unchanged.

### Task 9: Full Verification

**Files:**
- No additional production files.

- [ ] **Step 1: Run all backend tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -q
```

Expected: zero failures.

- [ ] **Step 2: Run frontend TypeScript verification**

```powershell
npm test
```

Working directory: `frontend`

Expected: `tsc --noEmit` exits successfully.

- [ ] **Step 3: Run frontend production build**

```powershell
npm run build
```

Working directory: `frontend`

Expected: Next.js build exits successfully.

- [ ] **Step 4: Verify unchanged contracts**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_intelligence_aggregate_api.py test_theme_graph_api.py test_portfolio_api.py test_quote_freshness.py test_stock_quote_contract.py -q
```

Expected: zero failures.

- [ ] **Step 5: Review scope**

Confirm `git diff --name-only` contains no frontend source, aggregate, portfolio, public API route, controller engine, hidden opportunity engine, or investment committee changes.

- [ ] **Step 6: Report**

Provide:

- files changed;
- schema summary;
- build process summary;
- validation summary;
- test and build results;
- known limitations;
- explicit note that Phase 12.3 has not started.
