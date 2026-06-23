# Phase 12.8 Controller Engine Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic, evidence-backed controller intelligence from one active Industrial Graph snapshot without changing graph facts, public APIs, frontend behavior, aggregate contracts, quotes, portfolios, or investment systems.

**Architecture:** Controller analytics are a separate derived snapshot layer. A builder reads exactly one immutable Industrial Graph snapshot, creates an in-memory analytical projection from an explicit relationship allowlist, computes transparent raw and normalized metrics, validates the complete result, and stages it in SQLite. Controller activation is transactional and independent from graph activation; projected edges are never persisted.

**Tech Stack:** Python 3.12, SQLite, NetworkX 3.x, dataclasses, pytest.

---

## Scope And Invariants

The implementation must preserve these rules:

- A controller is a graph conclusion, not a seed label.
- Legacy `CONTROLS` edges remain stored but are excluded from projection, metrics, types, paths, and score.
- `ENABLES` and `COMPANY_EXPOSED_TO_CONSTRAINT` are excluded from positive controller evidence.
- Only active or explicitly selected Industrial Graph snapshots may be analyzed.
- Every positive controller anchor must have persisted edge evidence.
- Analytical edge reversal occurs in memory only.
- Controller snapshots reference exactly one `graph_snapshots.id`.
- Controller activation never activates or mutates an Industrial Graph snapshot.
- No hidden-opportunity, investment, valuation, price, sentiment, quote, portfolio, or frontend inputs are permitted.
- Unknown or unsupported influence remains zero and produces no controller type.

## Approved Relationship Policy

Create constants in `controller_models.py`:

```python
POSITIVE_CONTROLLER_RELATIONSHIPS = frozenset({
    "EQUIPMENT_PRODUCED_BY",
    "MATERIAL_SUPPLIED_BY",
    "CONSTRAINT_RESOLVED_BY_COMPANY",
    "PROCESS_RESOLVED_BY_COMPANY",
    "EQUIPMENT_RESOLVED_BY",
    "MATERIAL_RESOLVED_BY",
    "SUPPLIES",
    "CUSTOMER_OF",
    "DEPENDS_ON",
    "USES_SUPPLIER",
})

EXCLUDED_CONTROLLER_RELATIONSHIPS = frozenset({
    "CONTROLS",
    "ENABLES",
    "COMPANY_EXPOSED_TO_CONSTRAINT",
})

DEPENDENCY_PROPAGATION_RELATIONSHIPS = frozenset({
    "USES_TECHNOLOGY",
    "REQUIRES_PROCESS",
    "TECHNOLOGY_ENABLES_PROCESS",
    "PROCESS_PRECEDES_PROCESS",
    "PROCESS_DEPENDS_ON_PROCESS",
    "PROCESS_REQUIRES_MATERIAL",
    "MATERIAL_ENABLES_PROCESS",
    "PROCESS_REQUIRES_EQUIPMENT",
    "EQUIPMENT_ENABLES_PROCESS",
    "THEME_DEPENDS_ON_MATERIAL",
    "THEME_DEPENDS_ON_EQUIPMENT",
    "THEME_LIMITED_BY_CONSTRAINT",
    "TECHNOLOGY_LIMITED_BY_CONSTRAINT",
    "PROCESS_LIMITED_BY_CONSTRAINT",
    "MATERIAL_LIMITED_BY_CONSTRAINT",
    "EQUIPMENT_LIMITED_BY_CONSTRAINT",
    "CONSTRAINT_DEPENDS_ON_MATERIAL",
    "CONSTRAINT_DEPENDS_ON_EQUIPMENT",
    "CONSTRAINT_DEPENDS_ON_PROCESS",
})
```

`SUPPLY_CHAIN_ROLE` and `PART_OF_SUPPLY_CHAIN` may be used for context inspection but never as positive controller anchors. A role label alone does not prove control.

## Metric Definitions

All normalized metrics are clamped to `0..100`. Raw values are persisted separately.

### Analytical Projection

Collapse the selected `nx.MultiDiGraph` into a deterministic `nx.DiGraph`.

- Reverse `EQUIPMENT_PRODUCED_BY`, `MATERIAL_SUPPLIED_BY`, `CONSTRAINT_RESOLVED_BY_COMPANY`, `PROCESS_RESOLVED_BY_COMPANY`, `EQUIPMENT_RESOLVED_BY`, and `MATERIAL_RESOLVED_BY` so influence flows `Company -> controlled entity`.
- Preserve explicit company-to-company `SUPPLIES`, `CUSTOMER_OF`, `DEPENDS_ON`, and `USES_SUPPLIER` direction.
- Preserve dependency-propagation edges.
- Exclude every other relationship from the analytical graph.
- Store original edge IDs and evidence IDs on each projected edge.
- If parallel edges collapse onto one analytical edge, merge sorted edge IDs, evidence IDs, and relationship types.
- Use deterministic distance:

```python
strength = max(confidence_score, dependency_strength, 1.0)
distance = 100.0 / strength
```

### Raw Metrics

For every candidate Company with at least one positive controller anchor:

```text
degree_centrality_raw
betweenness_centrality_raw
dependency_reach_raw
weighted_dependency_reach_raw
dependency_coverage_raw
constraint_coverage_raw
material_coverage_raw
equipment_coverage_raw
process_coverage_raw
technology_coverage_raw
resolution_edge_count_raw
supply_chain_edge_count_raw
evidence_count_raw
reasoning_path_count_raw
```

Definitions:

- `dependency_reach_raw`: count of unique non-Company descendants within four projected edges.
- `weighted_dependency_reach_raw`: sum of `1 / path_length` for unique reachable non-Company descendants using deterministic shortest paths.
- Coverage raw values: unique reachable nodes of that type divided by the total nodes of that type in the analytical graph.
- `constraint_coverage_raw`: only constraints reached through an explicit resolver anchor or dependency propagation from a positive anchor.
- `resolution_edge_count_raw`: count of explicit resolver anchors.
- `supply_chain_edge_count_raw`: count of explicit company-to-company allowlisted edges.
- `evidence_count_raw`: distinct persisted evidence IDs supporting positive anchors and retained reasoning paths.

### Normalized Components

```python
dependency_score = mean(
    percent(dependency_reach_raw, total_non_company_nodes),
    percent(weighted_dependency_reach_raw, total_non_company_nodes),
    degree_centrality * 100,
    betweenness_centrality * 100,
)

constraint_influence = percent(reachable_constraints, total_constraints)
material_control = percent(reachable_materials, total_materials)
equipment_control = percent(reachable_equipment, total_equipment)
process_control = percent(reachable_processes, total_processes)
technology_control = percent(reachable_technologies, total_technologies)
resolution_influence = percent(explicit_resolution_edges, total_resolution_edges)
supply_chain_influence = percent(explicit_supply_chain_edges, total_supply_chain_edges)
```

When a graph-wide denominator is zero, the component is `0.0` and that dimension is excluded from the coverage denominator.

### Coverage And Controller Score

Applicable dimensions are component dimensions whose graph-wide denominator is non-zero.

```python
positive_dimensions = count(component > 0 for applicable component)
coverage = 100.0 * positive_dimensions / applicable_dimensions
coverage_confidence = min(
    100.0,
    20.0 * distinct_positive_relationship_types
    + 10.0 * min(distinct_evidence_count, 6),
)

base_score = (
    dependency_score * 0.20
    + constraint_influence * 0.20
    + resolution_influence * 0.15
    + equipment_control * 0.10
    + material_control * 0.10
    + process_control * 0.10
    + technology_control * 0.05
    + supply_chain_influence * 0.10
)

controller_score = base_score * (0.50 + 0.50 * coverage_confidence / 100.0)
```

Persist `base_score`, `coverage`, and `coverage_confidence`; do not hide the confidence adjustment.

### Controller Type Derivation

Types require positive evidence and are sorted in this fixed order:

```python
CONTROLLER_TYPE_ORDER = (
    "Technology Controller",
    "Process Controller",
    "Material Controller",
    "Equipment Controller",
    "Capacity Controller",
    "Constraint Controller",
    "Supply Chain Controller",
)
```

Rules:

- Technology Controller: `technology_control > 0` through a positive anchor path.
- Process Controller: explicit process resolution or `process_control > 0` through a positive anchor.
- Material Controller: explicit material supplier/resolver anchor.
- Equipment Controller: explicit equipment producer/resolver anchor.
- Capacity Controller: explicit `CONSTRAINT_RESOLVED_BY_COMPANY` anchor to a `Capacity Constraint`.
- Constraint Controller: explicit constraint resolver anchor; exposure never qualifies.
- Supply Chain Controller: at least one explicit allowlisted company-to-company supply/dependency anchor.

## File Structure

Create:

- `backend/theme_intelligence/industrial_graph/controller_models.py`: immutable controller records, constants, checksum payloads, and score clamping.
- `backend/theme_intelligence/industrial_graph/controller_builder.py`: analytical projection, metric calculation, type derivation, evidence/path collection.
- `backend/theme_intelligence/industrial_graph/controller_validator.py`: build and persistence validation.
- `backend/theme_intelligence/industrial_graph/controller_engine.py`: stage, activate, build-and-activate, ranking, and intelligence orchestration.

Modify:

- `backend/theme_intelligence/storage/theme_repository.py`: additive controller tables and indexes only.
- `backend/theme_intelligence/industrial_graph/graph_repository.py`: evidence-aware export helpers and controller persistence/query methods.
- `backend/theme_intelligence/industrial_graph/__init__.py`: internal package exports.

Create tests:

- `test_controller_metrics.py`
- `test_controller_engine.py`
- `test_controller_builder.py`
- `test_controller_validation.py`
- `test_controller_paths.py`
- `test_controller_networkx.py`
- `test_controller_persistence.py`

Do not modify:

- `backend/main.py`
- `backend/theme_intelligence/aggregate.py`
- `backend/theme_intelligence/portfolio/`
- quote/cache/search modules
- frontend source
- Phase 10 graph APIs
- existing Industrial Graph edge or snapshot schemas

---

### Task 1: Define Controller Models And Metric Contracts

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/controller_models.py`
- Create: `test_controller_metrics.py`

- [ ] **Step 1: Write failing model tests**

Test:

```python
def test_controller_metric_models_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        ControllerMetric(
            company_key=("Company", "company:KLAC"),
            metric_name="equipment_control",
            raw_value=1.0,
            normalized_value=-1.0,
            coverage=100.0,
        )


def test_controller_intelligence_is_deterministic_and_transparent() -> None:
    row = ControllerIntelligence(
        company_key=("Company", "company:KLAC"),
        company_name="KLA",
        controller_types=("Equipment Controller", "Constraint Controller"),
        dependency_score=25.0,
        controller_score=30.0,
        constraint_influence=40.0,
        material_control=0.0,
        equipment_control=50.0,
        process_control=20.0,
        technology_control=0.0,
        resolution_influence=30.0,
        supply_chain_influence=0.0,
        coverage=50.0,
        coverage_confidence=80.0,
        evidence_ids=(1, 2),
        reasoning_paths=(
            (
                ("Company", "company:KLAC"),
                ("Equipment", "equipment:yield_inspection"),
                ("Constraint", "constraint:glass_substrate_yield"),
            ),
        ),
    )
    assert row.controller_types == (
        "Equipment Controller",
        "Constraint Controller",
    )
    assert row.to_dict()["evidence_ids"] == [1, 2]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_controller_metrics.py -q
```

Expected: import failure for `controller_models`.

- [ ] **Step 3: Implement immutable models**

Add:

```python
@dataclass(frozen=True)
class ControllerMetric:
    company_key: NodeKey
    metric_name: str
    raw_value: float
    normalized_value: float
    coverage: float
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ControllerIntelligence:
    company_key: NodeKey
    company_name: str
    controller_types: tuple[str, ...]
    dependency_score: float
    controller_score: float
    base_score: float
    constraint_influence: float
    material_control: float
    equipment_control: float
    process_control: float
    technology_control: float
    resolution_influence: float
    supply_chain_influence: float
    coverage: float
    coverage_confidence: float
    evidence_ids: tuple[int, ...]
    reasoning_paths: tuple[tuple[NodeKey, ...], ...]
    rank: int = 0


@dataclass(frozen=True)
class ControllerBuild:
    graph_snapshot_id: int
    graph_build_version: str
    algorithm_version: str
    metrics: tuple[ControllerMetric, ...]
    controllers: tuple[ControllerIntelligence, ...]


@dataclass(frozen=True)
class ControllerSnapshot:
    controller_version: str
    graph_snapshot_id: int
    graph_build_version: str
    algorithm_version: str
    status: str
    checksum: str
    company_count: int
    metric_count: int
    activated_at: str | None = None
    created_at: str = ""
    id: int | None = None
```

Validate Company identity, finite values, score bounds, sorted/deduplicated evidence IDs, controller types, and paths.

- [ ] **Step 4: Run model tests**

Expected: all `test_controller_metrics.py` tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/controller_models.py test_controller_metrics.py
git commit -m "feat: define controller intelligence models"
```

---

### Task 2: Add Additive Controller Persistence Schema

**Files:**
- Modify: `backend/theme_intelligence/storage/theme_repository.py`
- Create: `test_controller_persistence.py`

- [ ] **Step 1: Write failing schema tests**

Assert `ThemeRepository.initialize()` creates:

```text
controller_snapshots
graph_metrics
controller_metrics
```

Assert foreign keys, unique indexes, and required columns exist.

- [ ] **Step 2: Run schema test and verify failure**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_controller_persistence.py::test_controller_schema_is_additive -q
```

Expected: missing table failure.

- [ ] **Step 3: Add schema through `ThemeRepository.initialize()`**

Use:

```sql
CREATE TABLE IF NOT EXISTS controller_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    controller_version TEXT NOT NULL UNIQUE,
    graph_snapshot_id INTEGER NOT NULL,
    graph_build_version TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    status TEXT NOT NULL,
    checksum TEXT NOT NULL,
    company_count INTEGER NOT NULL,
    metric_count INTEGER NOT NULL,
    activated_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id)
);

CREATE TABLE IF NOT EXISTS graph_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    controller_snapshot_id INTEGER NOT NULL,
    controller_version TEXT NOT NULL,
    graph_snapshot_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    raw_value REAL NOT NULL,
    normalized_value REAL NOT NULL,
    coverage REAL NOT NULL,
    metadata_json TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(controller_snapshot_id, node_id, metric_name),
    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id),
    FOREIGN KEY(node_id) REFERENCES graph_nodes(id)
);

CREATE TABLE IF NOT EXISTS controller_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    controller_snapshot_id INTEGER NOT NULL,
    controller_version TEXT NOT NULL,
    graph_snapshot_id INTEGER NOT NULL,
    company_node_id INTEGER NOT NULL,
    dependency_score REAL NOT NULL,
    controller_score REAL NOT NULL,
    base_score REAL NOT NULL,
    constraint_influence REAL NOT NULL,
    material_control REAL NOT NULL,
    equipment_control REAL NOT NULL,
    process_control REAL NOT NULL,
    technology_control REAL NOT NULL,
    resolution_influence REAL NOT NULL,
    supply_chain_influence REAL NOT NULL,
    coverage REAL NOT NULL,
    coverage_confidence REAL NOT NULL,
    rank INTEGER NOT NULL,
    controller_types_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    reasoning_paths_json TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(controller_snapshot_id, company_node_id),
    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id),
    FOREIGN KEY(company_node_id) REFERENCES graph_nodes(id)
);
```

Indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_controller_snapshots_status
ON controller_snapshots(status);

CREATE INDEX IF NOT EXISTS idx_controller_snapshots_graph
ON controller_snapshots(graph_snapshot_id, status);

CREATE INDEX IF NOT EXISTS idx_graph_metrics_snapshot_metric
ON graph_metrics(controller_snapshot_id, metric_name);

CREATE INDEX IF NOT EXISTS idx_controller_metrics_snapshot_rank
ON controller_metrics(controller_snapshot_id, rank);

CREATE INDEX IF NOT EXISTS idx_controller_metrics_company
ON controller_metrics(company_node_id);
```

- [ ] **Step 4: Run schema tests**

Expected: schema and foreign-key tests pass.

- [ ] **Step 5: Run existing repository schema tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_repository.py test_graph_nodes.py test_graph_edges.py -q
```

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/storage/theme_repository.py test_controller_persistence.py
git commit -m "feat: add controller snapshot persistence schema"
```

---

### Task 3: Add Evidence-Aware Graph Export Helpers

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/graph_repository.py`
- Create: `test_controller_networkx.py`

- [ ] **Step 1: Write failing projection-input tests**

Create and activate the standard graph, then assert:

```python
graph = repository.export_controller_source_graph(snapshot.build_version)

assert graph.graph["graph_snapshot_id"] == snapshot.id
assert graph.graph["graph_build_version"] == snapshot.build_version
assert graph[("Constraint", "constraint:cowos_capacity")][
    ("Company", "company:TSM")
]
assert all(
    data["evidence_ids"]
    for _, _, _, data in graph.edges(keys=True, data=True)
)
```

Also assert selecting a missing or non-active graph snapshot fails.

- [ ] **Step 2: Run and verify failure**

Expected: missing `export_controller_source_graph`.

- [ ] **Step 3: Add repository helpers**

Implement:

```python
def get_snapshot(self, build_version: str) -> IndustrialGraphSnapshot | None: ...

def export_controller_source_graph(
    self,
    build_version: str | None = None,
) -> nx.MultiDiGraph:
    ...
```

Rules:

- Default to the active graph snapshot.
- If a version is supplied, require that snapshot to exist.
- Export all graph edges for that exact version so exclusion logic can be tested.
- Attach `graph_snapshot_id`, `graph_build_version`, and `graph_checksum` to `graph.graph`.
- Attach sorted evidence IDs and original edge ID to every edge.
- Do not reverse or mutate any edges here.

- [ ] **Step 4: Run NetworkX source tests**

Expected: tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/graph_repository.py test_controller_networkx.py
git commit -m "feat: expose evidence-aware controller graph source"
```

---

### Task 4: Build The In-Memory Analytical Projection

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/controller_builder.py`
- Extend: `test_controller_networkx.py`
- Create: `test_controller_paths.py`

- [ ] **Step 1: Write failing exclusion and reversal tests**

Required assertions:

```python
projection = ControllerBuilder(repository).build_projection()

assert projection.has_edge(
    ("Company", "company:AMAT"),
    ("Equipment", "equipment:advanced_etch"),
)
assert not projection.has_edge(
    ("Equipment", "equipment:advanced_etch"),
    ("Company", "company:AMAT"),
)
assert projection.has_edge(
    ("Company", "company:TSM"),
    ("Constraint", "constraint:cowos_capacity"),
)

for _, _, data in projection.edges(data=True):
    assert "CONTROLS" not in data["relationship_types"]
    assert "ENABLES" not in data["relationship_types"]
    assert "COMPANY_EXPOSED_TO_CONSTRAINT" not in data["relationship_types"]
```

Add a test proving HBM exposed companies receive no positive anchor solely from exposure.

- [ ] **Step 2: Run and verify failure**

Expected: missing `ControllerBuilder`.

- [ ] **Step 3: Implement deterministic projection**

Implement:

```python
class ControllerBuilder:
    MAX_PATH_DEPTH = 4
    ALGORITHM_VERSION = "controller-v1"

    def build_projection(
        self,
        graph_build_version: str | None = None,
    ) -> nx.DiGraph:
        ...
```

Use sorted nodes and sorted edges. Merge parallel projected edges with:

```python
{
    "relationship_types": tuple(sorted(types)),
    "source_edge_ids": tuple(sorted(edge_ids)),
    "evidence_ids": tuple(sorted(evidence_ids)),
    "distance": min(distances),
    "positive_anchor": any(anchor_flags),
}
```

Tag projected edges with `projected_from_reverse=True` where applicable.

- [ ] **Step 4: Implement bounded deterministic path collection**

```python
def reasoning_paths(
    self,
    projection: nx.DiGraph,
    company: NodeKey,
    *,
    max_depth: int = 4,
) -> tuple[tuple[NodeKey, ...], ...]:
    ...
```

Return at most 25 unique shortest paths, sorted by:

```text
path length
target node type
target canonical key
full path tuple
```

Only paths beginning with a positive anchor qualify.

- [ ] **Step 5: Run projection and path tests**

Expected: exclusions, reversals, bounded paths, and deterministic ordering pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/controller_builder.py test_controller_networkx.py test_controller_paths.py
git commit -m "feat: build controller analytical projection"
```

---

### Task 5: Compute Raw Metrics And Transparent Components

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/controller_builder.py`
- Extend: `test_controller_metrics.py`
- Create: `test_controller_builder.py`

- [ ] **Step 1: Write failing deterministic metric tests**

Required assertions:

```python
first = builder.build()
second = builder.build()
assert first == second

klac = next(
    row for row in first.controllers
    if row.company_key == ("Company", "company:KLAC")
)
assert klac.equipment_control > 0
assert klac.process_control > 0
assert "Equipment Controller" in klac.controller_types

tsm = next(
    row for row in first.controllers
    if row.company_key == ("Company", "company:TSM")
)
assert tsm.constraint_influence > 0
assert tsm.resolution_influence > 0
assert "Capacity Controller" in tsm.controller_types
assert "Constraint Controller" in tsm.controller_types
```

Assert SK hynix, Micron, and Samsung do not become Constraint Controllers from exposure.

- [ ] **Step 2: Run tests and verify failure**

Expected: missing metric build behavior.

- [ ] **Step 3: Implement graph-wide context and raw metrics**

Add private methods:

```python
def _candidate_companies(self, projection: nx.DiGraph) -> tuple[NodeKey, ...]: ...
def _graph_denominators(self, projection: nx.DiGraph) -> dict[str, int]: ...
def _raw_metrics(self, projection: nx.DiGraph, company: NodeKey) -> dict[str, float]: ...
def _reachable_by_type(
    self,
    projection: nx.DiGraph,
    company: NodeKey,
    node_type: str,
) -> tuple[NodeKey, ...]: ...
```

Calculate centrality once per build:

```python
degree = nx.degree_centrality(projection)
betweenness = nx.betweenness_centrality(
    projection,
    weight="distance",
    normalized=True,
)
```

Use only candidates with a positive anchor.

- [ ] **Step 4: Implement normalized components and score**

Implement the formulas in this plan exactly. Persist each raw metric as `ControllerMetric`.

Round persisted floating-point values to six decimal places only after calculation.

- [ ] **Step 5: Implement deterministic ranking**

Sort:

```python
sorted(
    controllers,
    key=lambda row: (
        -row.controller_score,
        -row.coverage_confidence,
        -row.dependency_score,
        row.company_key,
    ),
)
```

Assign one-based ordinal ranks. Equal scores do not share a rank.

- [ ] **Step 6: Run builder and metric tests**

Expected: deterministic output and influence assertions pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/controller_builder.py test_controller_metrics.py test_controller_builder.py
git commit -m "feat: compute deterministic controller metrics"
```

---

### Task 6: Derive Evidence, Types, And Controller Intelligence

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/controller_builder.py`
- Extend: `test_controller_builder.py`
- Extend: `test_controller_paths.py`

- [ ] **Step 1: Write failing evidence and type tests**

Test that:

- Every controller has at least one evidence ID.
- Every evidence ID exists in `graph_evidence`.
- Controller types follow `CONTROLLER_TYPE_ORDER`.
- No reasoning path contains an excluded relationship.
- No controller type is derived from a legacy `CONTROLS` edge.
- Removing an explicit producer edge removes the corresponding Equipment Controller conclusion.

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement evidence collection**

Evidence is the sorted union of:

- positive anchor edge evidence;
- evidence on dependency edges used by retained reasoning paths.

Do not include evidence from excluded edges or unrelated graph edges.

- [ ] **Step 4: Implement type derivation**

Use the rules in the Controller Type Derivation section. Type derivation must inspect positive anchor semantics and reachable typed nodes; it must not inspect seed beneficiary/controller labels.

- [ ] **Step 5: Run builder and path tests**

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/controller_builder.py test_controller_builder.py test_controller_paths.py
git commit -m "feat: derive evidence-backed controller intelligence"
```

---

### Task 7: Validate Controller Builds Before Persistence

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/controller_validator.py`
- Create: `test_controller_validation.py`

- [ ] **Step 1: Write failing validation tests**

Cover:

```text
negative score
score above 100
missing graph snapshot ID
missing graph build version
unknown graph snapshot
graph snapshot/version mismatch
missing evidence
orphan evidence ID
orphan company node
duplicate controller company
duplicate raw metric
unsorted or duplicate controller type
reasoning path not beginning at company
reasoning path containing an excluded relationship
non-deterministic checksum
```

- [ ] **Step 2: Run and verify failure**

Expected: missing validator.

- [ ] **Step 3: Implement validator**

```python
class ControllerValidationError(ValueError):
    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = tuple(sorted(set(errors)))
        super().__init__("; ".join(self.errors))


class ControllerValidator:
    def validate(
        self,
        build: ControllerBuild,
        repository: IndustrialGraphRepository,
    ) -> None:
        ...
```

Repository validation must confirm:

- referenced graph snapshot exists;
- snapshot ID and build version identify the same row;
- referenced company nodes exist;
- evidence IDs exist and are attached to graph edges in the selected build;
- reasoning paths can be reproduced in the analytical projection;
- excluded relationships cannot support stored paths.

- [ ] **Step 4: Add deterministic checksum**

In `controller_models.py`:

```python
def controller_build_checksum(build: ControllerBuild) -> str:
    payload = {
        "graph_snapshot_id": build.graph_snapshot_id,
        "graph_build_version": build.graph_build_version,
        "algorithm_version": build.algorithm_version,
        "metrics": [...],
        "controllers": [...],
    }
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()
```

Exclude generated timestamps and database IDs.

- [ ] **Step 5: Run validation tests**

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/controller_models.py backend/theme_intelligence/industrial_graph/controller_validator.py test_controller_validation.py
git commit -m "feat: validate controller builds"
```

---

### Task 8: Implement Controller Persistence Methods

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/graph_repository.py`
- Extend: `test_controller_persistence.py`

- [ ] **Step 1: Write failing persistence tests**

Test:

- staged snapshot references one graph snapshot;
- metrics persist with version, algorithm version, coverage, and timestamp;
- duplicate controller rows fail;
- query order is rank then canonical company key;
- active queries return only the active controller snapshot;
- graph snapshot rows and statuses are unchanged.

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Add persistence methods**

Implement:

```python
def insert_controller_snapshot(
    self,
    conn: sqlite3.Connection,
    snapshot: ControllerSnapshot,
) -> int: ...

def insert_graph_metrics(
    self,
    conn: sqlite3.Connection,
    controller_snapshot_id: int,
    controller_version: str,
    graph_snapshot_id: int,
    algorithm_version: str,
    metrics: Iterable[ControllerMetric],
    node_ids: dict[NodeKey, int],
) -> int: ...

def insert_controller_metrics(
    self,
    conn: sqlite3.Connection,
    controller_snapshot_id: int,
    controller_version: str,
    graph_snapshot_id: int,
    algorithm_version: str,
    controllers: Iterable[ControllerIntelligence],
    node_ids: dict[NodeKey, int],
) -> int: ...

def get_active_controller_snapshot(self) -> ControllerSnapshot | None: ...
def get_controller_snapshot(self, controller_version: str) -> ControllerSnapshot | None: ...
def get_controller_metrics(
    self,
    controller_version: str | None = None,
) -> list[ControllerIntelligence]: ...
```

Use canonical JSON serialization for metadata, types, evidence IDs, and reasoning paths.

- [ ] **Step 4: Run persistence tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/graph_repository.py test_controller_persistence.py
git commit -m "feat: persist controller metrics"
```

---

### Task 9: Add Transactional Controller Snapshot Lifecycle

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/controller_engine.py`
- Create: `test_controller_engine.py`
- Extend: `test_controller_persistence.py`

- [ ] **Step 1: Write failing lifecycle tests**

Required behavior:

```python
first = engine.build_and_activate()
second = engine.build_and_activate()

assert first.controller_version != second.controller_version
assert first.checksum == second.checksum
assert second.status == "active"
assert engine.repository.get_active_controller_snapshot() == second
```

Rollback test:

```python
def fail_after_supersede(conn, controller_version):
    conn.execute(
        "UPDATE controller_snapshots SET status='superseded' WHERE status='active'"
    )
    raise RuntimeError("forced controller activation failure")
```

After failure, the first controller snapshot must remain active.

Also assert graph snapshot status remains active and unchanged.

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement orchestration**

```python
class ControllerEngine:
    def __init__(self, repository: ThemeRepository | None = None) -> None:
        theme_repository = repository or ThemeRepository()
        self.repository = IndustrialGraphRepository(theme_repository)
        self.builder = ControllerBuilder(theme_repository)
        self.validator = ControllerValidator()

    def build(self, graph_build_version: str | None = None) -> ControllerBuild: ...
    def stage(self, build: ControllerBuild) -> ControllerSnapshot: ...
    def activate(self, controller_version: str) -> ControllerSnapshot: ...
    def build_and_activate(
        self,
        graph_build_version: str | None = None,
    ) -> ControllerSnapshot: ...
```

Stage transaction:

1. validate build;
2. insert `controller_snapshots` with `building`;
3. insert raw and controller metrics;
4. verify stored counts;
5. commit or rollback.

Activation transaction:

1. require target status `building` or `active`;
2. supersede the prior active controller snapshot;
3. activate target;
4. never update `graph_snapshots` or `graph_edges`;
5. commit or rollback.

- [ ] **Step 4: Run lifecycle tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/controller_engine.py test_controller_engine.py test_controller_persistence.py
git commit -m "feat: add transactional controller snapshots"
```

---

### Task 10: Add Internal Ranking And Intelligence Queries

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/controller_engine.py`
- Extend: `test_controller_engine.py`

- [ ] **Step 1: Write failing query tests**

Test:

```python
ranked = engine.get_ranked_controllers(limit=10)
assert ranked == sorted(
    ranked,
    key=lambda row: (
        row.rank,
        row.company_key,
    ),
)

kla = engine.get_controller_intelligence(("Company", "company:KLAC"))
assert kla is not None
assert kla.company_name == "KLA"
assert kla.evidence_ids
assert kla.reasoning_paths
```

Unknown company and no-active-snapshot cases must return `None` or `[]`, not fabricate data.

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement internal queries**

```python
def get_ranked_controllers(
    self,
    *,
    limit: int | None = None,
) -> list[ControllerIntelligence]: ...

def get_controller_intelligence(
    self,
    company: NodeKey,
) -> ControllerIntelligence | None: ...
```

These are internal Python APIs only. Do not add FastAPI routes or aggregate fields.

- [ ] **Step 4: Run query tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/controller_engine.py test_controller_engine.py
git commit -m "feat: query controller intelligence"
```

---

### Task 11: Export Controller Internals And Run Focused Regression

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/__init__.py`
- Modify only if necessary: controller test files

- [ ] **Step 1: Export internal controller types**

Export:

```text
ControllerBuild
ControllerEngine
ControllerIntelligence
ControllerMetric
ControllerSnapshot
ControllerValidationError
ControllerValidator
controller_build_checksum
```

- [ ] **Step 2: Run all controller tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest `
  test_controller_metrics.py `
  test_controller_engine.py `
  test_controller_builder.py `
  test_controller_validation.py `
  test_controller_paths.py `
  test_controller_networkx.py `
  test_controller_persistence.py -q
```

Expected: all pass.

- [ ] **Step 3: Run Industrial Graph regression tests**

```powershell
$tests = Get-ChildItem -Name `
  'test_graph_*.py', `
  'test_supply_chain_*.py', `
  'test_technology_*.py', `
  'test_process_*.py', `
  'test_material_*.py', `
  'test_equipment_*.py', `
  'test_constraint_*.py', `
  'test_controller_*.py'
.\backend\.venv\Scripts\python.exe -m pytest $tests -q
```

Expected: all pass and existing graph snapshot tests remain unchanged.

- [ ] **Step 4: Confirm forbidden modules are unchanged**

```powershell
git diff --name-only -- `
  backend/main.py `
  backend/theme_intelligence/aggregate.py `
  backend/theme_intelligence/portfolio `
  backend/quant_engine `
  frontend
```

Expected: no Phase 12.8 changes.

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/__init__.py
git commit -m "feat: export controller engine foundation"
```

---

### Task 12: Full Verification And Deliverable Audit

**Files:**
- No implementation files unless verification exposes a root-cause defect.

- [ ] **Step 1: Run complete backend suite**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend TypeScript safety check**

```powershell
Set-Location frontend
npx tsc --noEmit
```

Expected: exit code `0`.

- [ ] **Step 3: Run production frontend build**

```powershell
npm run build
```

Expected: successful production build with no new Phase 12.8 errors.

- [ ] **Step 4: Audit persisted controller results**

Build a fresh temporary database and report:

```text
graph snapshot ID/version
controller snapshot ID/version
algorithm version
candidate company count
raw metric count
active controller count
controller types by count
legacy CONTROLS edges in source graph
legacy CONTROLS edges used in projection: 0
ENABLES edges used in projection: 0
COMPANY_EXPOSED_TO_CONSTRAINT edges used in projection: 0
controllers without evidence: 0
reasoning paths above max depth: 0
```

- [ ] **Step 5: Verify transactional independence**

Record the active graph snapshot before and after controller activation. Assert:

```text
graph snapshot ID unchanged
graph build version unchanged
graph status unchanged
graph edge statuses unchanged
```

- [ ] **Step 6: Review final diff**

```powershell
git diff --check
git status --short
```

Do not revert unrelated user changes.

## Final Deliverables

Report:

- changed files;
- controller architecture;
- exact metric definitions and score weights;
- controller type derivation;
- persistence and transactional activation;
- NetworkX analytical projection;
- validation behavior;
- explicit legacy `CONTROLS` exclusion;
- test, TypeScript, and build results;
- known limitations.

Known limitations should explicitly state:

- conclusions are limited by current curated graph coverage;
- companies with only exposure or beneficiary labels are not controllers;
- supplier concentration and substitution difficulty are not separately scored yet;
- no live research ingestion is added;
- no Hidden Opportunity Engine, public API, frontend, investment recommendation, or scoring outside Controller Intelligence is implemented.
