# Phase 12.9 Hidden Opportunity Engine Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic, evidence-backed hidden-opportunity intelligence from one active Controller snapshot and its exact Industrial Graph snapshot, without runtime market providers, public APIs, frontend changes, recommendations, or Investment Committee behavior.

**Architecture:** Opportunity analytics form a third independent snapshot layer above Industrial Graph and Controller snapshots. A builder reads one immutable Controller snapshot, verifies its referenced Graph snapshot, derives industrial components from persisted controller metrics and reasoning paths, admits only persisted market inputs with explicit availability, validates the complete build, and stages it in additive SQLite tables. Opportunity activation is transactional and does not mutate Controller or Graph snapshot state.

**Tech Stack:** Python 3.12, SQLite, dataclasses, deterministic graph/path inspection, pytest.

---

## Scope And Invariants

- Candidate companies come only from the selected Controller snapshot.
- Every Opportunity snapshot references exactly one Controller snapshot.
- Its `graph_snapshot_id` must equal the Graph snapshot referenced by that Controller snapshot.
- Controller and Graph snapshots remain immutable and independently active.
- No quote provider, runtime enrichment, Bubble Engine call, search result, news, sentiment, analyst rating, market cap, frontend state, LLM inference, or manually assigned opportunity label may be used.
- Legacy `CONTROLS`, beneficiary `ENABLES`, and `COMPANY_EXPOSED_TO_CONSTRAINT` remain excluded because the Controller snapshot already excludes them from positive controller evidence.
- Opportunity reasoning paths must be reproducible from persisted Controller reasoning paths and the selected Graph snapshot.
- Missing market data never contributes a favorable score.
- Raw values, normalized values, configured weights, applied weights, availability states, source records, evidence IDs, paths, algorithm version, and snapshot references are persisted.
- No buy, sell, hold, target-price, allocation, or portfolio output is introduced.

## Architecture Findings

- `ControllerEngine` already provides the correct independent `build -> validate -> stage -> activate` lifecycle.
- `controller_snapshots` references one `graph_snapshots.id`; `controller_metrics` persists all approved industrial components, evidence IDs, reasoning paths, rank, and coverage.
- Controller reasoning paths begin at Company and follow the analytical influence projection. Theme-facing opportunity paths can be created only by reversing persisted paths that terminate at or contain a Theme node.
- `theme_discovery_scores` persists `crowding_proxy` and `updated_at` for themes and can support market-attention scoring without runtime calls.
- `theme_beneficiary_scores` persists `valuation_penalty`, `bubble_penalty`, and `updated_at`, but it has no provenance field proving that a zero is an explicitly observed zero.
- Existing seed and scoring flows write zero penalties as defaults. Therefore, every current zero valuation or bubble penalty is ambiguous and must be unavailable.
- Positive finite persisted penalties are explicit enough to admit in Phase 12.9, provided the company and theme are connected by a retained evidence-backed Controller reasoning path.

## Root Causes Addressed

1. Controller intelligence identifies industrial influence but does not distinguish less-crowded opportunities from already-crowded themes.
2. Persisted beneficiary penalty rows mix observed positive values with ambiguous default zeros.
3. Treating missing penalties as zero would turn incomplete evidence into a positive valuation or bubble signal.
4. Existing market tables are mutable latest-state tables, so Opportunity snapshots must copy every admitted source value and timestamp to remain reproducible.
5. Controller paths are Company-first, while opportunity explanations require deterministic Theme-to-Company presentation paths.

## Affected Systems

Create:

- `backend/theme_intelligence/industrial_graph/opportunity_models.py`
- `backend/theme_intelligence/industrial_graph/opportunity_builder.py`
- `backend/theme_intelligence/industrial_graph/opportunity_validator.py`
- `backend/theme_intelligence/industrial_graph/opportunity_engine.py`
- `test_opportunity_metrics.py`
- `test_opportunity_engine.py`
- `test_opportunity_builder.py`
- `test_opportunity_validation.py`
- `test_opportunity_paths.py`
- `test_opportunity_snapshot.py`
- `test_opportunity_ranking.py`

Modify:

- `backend/theme_intelligence/storage/theme_repository.py`: additive Opportunity schema only.
- `backend/theme_intelligence/industrial_graph/graph_repository.py`: read-only source queries plus Opportunity persistence/query methods.
- `backend/theme_intelligence/industrial_graph/__init__.py`: internal exports only.

Do not modify:

- FastAPI routes or `backend/main.py`
- aggregate contracts
- frontend source
- quote/cache/search/provider systems
- Bubble Engine runtime
- portfolio logic
- Investment Committee
- Industrial Graph construction or activation
- Controller formulas, projection, persistence, or activation
- Phase 10 graph APIs

## Exact Component Definitions

All normalized components are clamped to `0..100`. Calculations use full precision and persisted values are rounded to six decimal places.

### Industrial Components

For a persisted `ControllerIntelligence` row:

```python
controller_component = controller.controller_score
constraint_component = controller.constraint_influence
dependency_component = controller.dependency_score
resolution_component = controller.resolution_influence

criticality_component = (
    controller.technology_control * 0.15
    + controller.process_control * 0.20
    + controller.material_control * 0.25
    + controller.equipment_control * 0.25
    + controller.supply_chain_influence * 0.15
)
```

These five components are always available because they are copied from a validated Controller snapshot. They must retain the Controller snapshot ID, Graph snapshot ID, algorithm version, evidence IDs, and reasoning paths as provenance.

### Reachable Themes

A theme is reachable only when it appears in a persisted Controller reasoning path for the company.

For each distinct theme:

```python
theme_support_count = number_of_distinct_controller_paths_containing_theme
theme_weight = theme_support_count / sum(all_reachable_theme_support_counts)
```

Theme ordering is canonical-key order. Duplicate paths and duplicate theme appearances inside one path count once.

### Market Attention

Admit a theme crowding input only when:

- a matching `theme_discovery_scores` row exists;
- `crowding_proxy` is finite and in `0..100`;
- the row has a non-empty `updated_at`;
- the theme is reachable through a persisted Controller reasoning path.

An explicit persisted crowding value of zero is available because row existence proves the measured value was persisted.

```python
weighted_reachable_theme_crowding = sum(
    theme.crowding_proxy * normalized_available_theme_support_weight
)
market_attention_component = 100.0 - weighted_reachable_theme_crowding
```

If no reachable theme has an admissible crowding row, the component is unavailable, its raw and normalized values are `NULL`, and its applied weight is zero.

### Valuation And Bubble Risk

Query `theme_beneficiary_scores` only for the candidate ticker and reachable themes.

For each company/theme/component:

- positive finite penalty in `0..100`: available;
- zero penalty: unavailable unless a future source schema explicitly proves observed zero;
- missing row: unavailable;
- negative, non-finite, or above-100 value: invalid input and build failure.

When multiple beneficiary-type rows exist for one company/theme, select the highest positive penalty. This is deterministic and conservative; duplicate role rows cannot dilute risk.

Aggregate selected theme penalties using the same reachable-theme support weights, renormalized across themes with available values:

```python
valuation_penalty_raw = weighted_mean(selected_positive_valuation_penalties)
valuation_component = 100.0 - valuation_penalty_raw

bubble_penalty_raw = weighted_mean(selected_positive_bubble_penalties)
bubble_risk_component = 100.0 - bubble_penalty_raw
```

If no positive explicit penalty is available, the component is unavailable. An unavailable valuation or bubble component must have:

```text
raw value = NULL
normalized value = NULL
applied weight = 0
availability_state = unavailable
```

It must never become `100`, `0`, or any other favorable substitute.

## Exact Weight And Coverage Policy

Configured weights:

```python
OPPORTUNITY_WEIGHTS = {
    "controller_component": 0.25,
    "constraint_component": 0.20,
    "dependency_component": 0.15,
    "resolution_component": 0.15,
    "criticality_component": 0.10,
    "market_attention_component": 0.05,
    "valuation_component": 0.05,
    "bubble_risk_component": 0.05,
}
```

Available components are renormalized:

```python
available_weight_total = sum(
    configured_weight
    for component, configured_weight in OPPORTUNITY_WEIGHTS.items()
    if availability_state[component] == "available"
)

applied_weight[component] = (
    configured_weight / available_weight_total
    if availability_state[component] == "available"
    else 0.0
)

base_score = sum(
    normalized_component[component] * applied_weight[component]
    for component in OPPORTUNITY_WEIGHTS
)
```

Coverage:

```python
coverage_component = available_weight_total * 100.0

industrial_evidence_confidence = (
    controller.coverage + controller.coverage_confidence
) / 2.0

coverage_confidence = (
    industrial_evidence_confidence * coverage_component / 100.0
)

opportunity_score = base_score * (
    0.50 + 0.50 * coverage_confidence / 100.0
)
```

Consequences:

- all three market components unavailable: coverage component is `85`;
- valuation and bubble unavailable but attention available: coverage component is `90`;
- no unavailable component can improve `base_score`;
- every unavailable component reduces final confidence;
- final score remains in `0..100`.

## Opportunity Type Derivation

Types are evidence-derived and sorted in this order:

```python
OPPORTUNITY_TYPE_ORDER = (
    "Technology Opportunity",
    "Process Opportunity",
    "Material Opportunity",
    "Equipment Opportunity",
    "Capacity Opportunity",
    "Constraint Opportunity",
    "Supply Chain Opportunity",
    "Hybrid Opportunity",
)
```

Rules:

- Technology Opportunity: positive `technology_control` and a retained path containing Technology.
- Process Opportunity: positive `process_control` and a retained path containing Process.
- Material Opportunity: positive `material_control` and a retained path containing Material.
- Equipment Opportunity: positive `equipment_control` and a retained path containing Equipment.
- Capacity Opportunity: Controller type includes `Capacity Controller` and a retained path contains a Capacity Constraint.
- Constraint Opportunity: positive `constraint_influence` and a retained path containing Constraint.
- Supply Chain Opportunity: positive `supply_chain_influence` and a retained path contains an explicit supply/dependency relationship.
- Hybrid Opportunity: add when at least two non-Hybrid opportunity types qualify; retain the qualifying specific types.

No type may be inferred from beneficiary labels, role strings, market penalties, seeded controller tags, or unavailable values.

## Persistence Design

Add through `ThemeRepository.initialize()` only.

```sql
CREATE TABLE IF NOT EXISTS opportunity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_version TEXT NOT NULL UNIQUE,
    controller_snapshot_id INTEGER NOT NULL,
    controller_version TEXT NOT NULL,
    graph_snapshot_id INTEGER NOT NULL,
    graph_build_version TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    status TEXT NOT NULL,
    checksum TEXT NOT NULL,
    company_count INTEGER NOT NULL,
    path_count INTEGER NOT NULL,
    activated_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id),
    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id)
);

CREATE TABLE IF NOT EXISTS opportunity_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_snapshot_id INTEGER NOT NULL,
    opportunity_version TEXT NOT NULL,
    controller_snapshot_id INTEGER NOT NULL,
    graph_snapshot_id INTEGER NOT NULL,
    company_node_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    controller_component_raw REAL NOT NULL,
    controller_component REAL NOT NULL,
    constraint_component_raw REAL NOT NULL,
    constraint_component REAL NOT NULL,
    dependency_component_raw REAL NOT NULL,
    dependency_component REAL NOT NULL,
    resolution_component_raw REAL NOT NULL,
    resolution_component REAL NOT NULL,
    criticality_component_raw REAL NOT NULL,
    criticality_component REAL NOT NULL,
    market_attention_raw REAL,
    market_attention_component REAL,
    valuation_penalty_raw REAL,
    valuation_component REAL,
    bubble_penalty_raw REAL,
    bubble_risk_component REAL,
    coverage_component REAL NOT NULL,
    coverage_confidence REAL NOT NULL,
    base_score REAL NOT NULL,
    opportunity_score REAL NOT NULL,
    rank INTEGER NOT NULL,
    opportunity_types_json TEXT NOT NULL,
    configured_weights_json TEXT NOT NULL,
    applied_weights_json TEXT NOT NULL,
    availability_states_json TEXT NOT NULL,
    source_records_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(opportunity_snapshot_id, company_node_id),
    UNIQUE(opportunity_snapshot_id, rank),
    FOREIGN KEY(opportunity_snapshot_id) REFERENCES opportunity_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id),
    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id),
    FOREIGN KEY(company_node_id) REFERENCES graph_nodes(id)
);

CREATE TABLE IF NOT EXISTS opportunity_reasoning_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_snapshot_id INTEGER NOT NULL,
    opportunity_version TEXT NOT NULL,
    company_node_id INTEGER NOT NULL,
    path_order INTEGER NOT NULL,
    path_kind TEXT NOT NULL,
    path_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(opportunity_snapshot_id, company_node_id, path_order),
    FOREIGN KEY(opportunity_snapshot_id) REFERENCES opportunity_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY(company_node_id) REFERENCES graph_nodes(id)
);
```

Indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_opportunity_snapshots_status
ON opportunity_snapshots(status);

CREATE INDEX IF NOT EXISTS idx_opportunity_snapshots_controller
ON opportunity_snapshots(controller_snapshot_id, status);

CREATE INDEX IF NOT EXISTS idx_opportunity_metrics_snapshot_rank
ON opportunity_metrics(opportunity_snapshot_id, rank);

CREATE INDEX IF NOT EXISTS idx_opportunity_metrics_company
ON opportunity_metrics(company_node_id);

CREATE INDEX IF NOT EXISTS idx_opportunity_paths_snapshot_company
ON opportunity_reasoning_paths(opportunity_snapshot_id, company_node_id, path_order);
```

`source_records_json` is a canonical object keyed by market component. Every admitted source record contains:

```python
{
    "source_table": "theme_discovery_scores",
    "source_record_key": {"theme_name": "HBM"},
    "source_timestamp": "persisted updated_at",
    "source_value": 42.0,
    "availability_state": "available",
}
```

Unavailable components retain an availability entry and a deterministic reason such as `missing_row` or `ambiguous_zero`; they do not contain an admitted source value.

---

### Task 1: Define Opportunity Models And Formula Contracts

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/opportunity_models.py`
- Create: `test_opportunity_metrics.py`

- [ ] **Step 1: Write failing tests for weights, availability, and ambiguous zero**

Test that configured weights sum to one, valid market states are only `available` and `unavailable`, an unavailable component requires `None` raw/normalized values and zero applied weight, and scores outside `0..100` fail.

```python
def test_unavailable_market_component_cannot_have_a_favorable_value() -> None:
    with pytest.raises(ValueError, match="unavailable market component"):
        MarketComponent(
            name="valuation_component",
            raw_value=0.0,
            normalized_value=100.0,
            availability_state="unavailable",
            configured_weight=0.05,
            applied_weight=0.0,
            source_records=(),
        )
```

- [ ] **Step 2: Run and verify import failure**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_opportunity_metrics.py -q
```

- [ ] **Step 3: Implement immutable models**

Define:

```python
@dataclass(frozen=True)
class MarketSourceRecord:
    source_table: str
    source_record_key: Mapping[str, str]
    source_timestamp: str
    source_value: float
    availability_state: str = "available"


@dataclass(frozen=True)
class MarketComponent:
    name: str
    raw_value: float | None
    normalized_value: float | None
    availability_state: str
    configured_weight: float
    applied_weight: float
    source_records: tuple[MarketSourceRecord, ...] = ()
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class OpportunityIntelligence:
    company_key: NodeKey
    company_name: str
    opportunity_types: tuple[str, ...]
    controller_component: float
    constraint_component: float
    dependency_component: float
    resolution_component: float
    criticality_component: float
    market_attention: MarketComponent
    valuation: MarketComponent
    bubble_risk: MarketComponent
    coverage_component: float
    coverage_confidence: float
    base_score: float
    opportunity_score: float
    configured_weights: Mapping[str, float]
    applied_weights: Mapping[str, float]
    evidence_ids: tuple[int, ...]
    reasoning_paths: tuple[tuple[NodeKey, ...], ...]
    rank: int = 0


@dataclass(frozen=True)
class OpportunityBuild:
    controller_snapshot_id: int
    controller_version: str
    graph_snapshot_id: int
    graph_build_version: str
    algorithm_version: str
    opportunities: tuple[OpportunityIntelligence, ...]


@dataclass(frozen=True)
class OpportunitySnapshot:
    opportunity_version: str
    controller_snapshot_id: int
    controller_version: str
    graph_snapshot_id: int
    graph_build_version: str
    algorithm_version: str
    status: str
    checksum: str
    company_count: int
    path_count: int
    activated_at: str | None = None
    created_at: str = ""
    id: int | None = None
```

Add `opportunity_build_checksum()` using canonical JSON and excluding timestamps/database IDs.

- [ ] **Step 4: Run model tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/opportunity_models.py test_opportunity_metrics.py
git commit -m "feat: define hidden opportunity models"
```

### Task 2: Add Additive Opportunity Persistence Schema

**Files:**
- Modify: `backend/theme_intelligence/storage/theme_repository.py`
- Create: `test_opportunity_snapshot.py`

- [ ] **Step 1: Write failing schema tests**

Assert all three tables, columns, foreign keys, uniqueness constraints, and indexes from the Persistence Design section exist after `ThemeRepository.initialize()`.

- [ ] **Step 2: Run the schema test and verify failure**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_opportunity_snapshot.py::test_opportunity_schema_is_additive -q
```

- [ ] **Step 3: Add the schema exactly through `ThemeRepository.initialize()`**

Do not add migrations elsewhere and do not alter existing Graph or Controller tables.

- [ ] **Step 4: Run repository regression tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_repository.py test_controller_persistence.py -q
```

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/storage/theme_repository.py test_opportunity_snapshot.py
git commit -m "feat: add opportunity snapshot schema"
```

### Task 3: Add Snapshot-Bound Source Queries

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/graph_repository.py`
- Create: `test_opportunity_builder.py`

- [ ] **Step 1: Write failing source-query tests**

Require:

```python
controller = repository.get_active_controller_snapshot()
context = repository.get_opportunity_source_context(controller.controller_version)

assert context.controller_snapshot.id == controller.id
assert context.graph_snapshot.id == controller.graph_snapshot_id
assert context.controllers
```

Test that crowding and beneficiary rows are returned only for requested canonical themes and ticker, with source table, row key, timestamp, and raw value intact.

- [ ] **Step 2: Run and verify missing methods**

- [ ] **Step 3: Implement read-only queries**

Add:

```python
def get_opportunity_source_context(
    self,
    controller_version: str | None = None,
) -> OpportunitySourceContext: ...

def get_persisted_theme_crowding(
    self,
    theme_names: Iterable[str],
) -> tuple[PersistedMarketInput, ...]: ...

def get_persisted_beneficiary_penalties(
    self,
    ticker: str,
    theme_names: Iterable[str],
) -> tuple[PersistedBeneficiaryPenalty, ...]: ...
```

The context method must verify the Controller snapshot's Graph reference before returning data. Queries sort by theme, ticker, beneficiary type, timestamp, then row ID.

- [ ] **Step 4: Run source-query tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/graph_repository.py test_opportunity_builder.py
git commit -m "feat: expose persisted opportunity inputs"
```

### Task 4: Build Deterministic Opportunity Paths

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/opportunity_builder.py`
- Create: `test_opportunity_paths.py`

- [ ] **Step 1: Write failing path tests**

Assert:

- retained paths are exact Controller paths;
- Theme-ending paths are reversed for presentation;
- reversed paths begin at Theme and end at Company;
- no path is invented by a new NetworkX search;
- duplicate paths are removed;
- ordering is length, theme key, full path;
- output is bounded to 25 paths per company.

- [ ] **Step 2: Run and verify missing builder**

- [ ] **Step 3: Implement path preparation**

```python
class OpportunityBuilder:
    ALGORITHM_VERSION = "opportunity-v1"
    MAX_REASONING_PATHS = 25

    def prepare_reasoning_paths(
        self,
        controller: ControllerIntelligence,
    ) -> tuple[tuple[NodeKey, ...], ...]:
        ...
```

Retain canonical Controller paths. Reverse only paths with a Theme node so the Theme is first and Company is last. Do not splice paths or infer graph shortcuts.

- [ ] **Step 4: Run path tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/opportunity_builder.py test_opportunity_paths.py
git commit -m "feat: prepare opportunity reasoning paths"
```

### Task 5: Implement Market Input Availability

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/opportunity_builder.py`
- Extend: `test_opportunity_metrics.py`
- Extend: `test_opportunity_builder.py`

- [ ] **Step 1: Write failing availability tests**

Required cases:

```text
positive valuation penalty -> available
positive bubble penalty -> available
zero valuation penalty -> unavailable/ambiguous_zero
zero bubble penalty -> unavailable/ambiguous_zero
missing row -> unavailable/missing_row
explicit crowding zero row -> available
missing crowding row -> unavailable
negative/non-finite/above-100 input -> failure
unreachable theme row -> ignored
```

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement deterministic admission**

Add:

```python
def _market_attention_component(...) -> MarketComponent: ...
def _valuation_component(...) -> MarketComponent: ...
def _bubble_risk_component(...) -> MarketComponent: ...
def _select_penalty_rows(...) -> tuple[PersistedBeneficiaryPenalty, ...]: ...
```

For duplicate beneficiary rows on one theme, select the maximum positive penalty and use row ID as the final deterministic tie-breaker. Persist every selected row's source table, key, timestamp, and value.

- [ ] **Step 4: Run market-input tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/opportunity_builder.py test_opportunity_metrics.py test_opportunity_builder.py
git commit -m "feat: enforce opportunity input availability"
```

### Task 6: Compute Components, Coverage, Types, And Ranking

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/opportunity_builder.py`
- Extend: `test_opportunity_metrics.py`
- Create: `test_opportunity_ranking.py`

- [ ] **Step 1: Write failing formula tests**

Use hand-calculated fixtures to verify the exact formulas in this plan, including:

- all components available;
- valuation and bubble unavailable;
- all market components unavailable;
- applied weights sum to one;
- unavailable components have zero applied weight;
- coverage falls from `100` to `90` or `85`;
- missing data cannot increase the score when all admitted values are otherwise equal.

- [ ] **Step 2: Write failing deterministic ranking tests**

Sort by:

```python
(
    -opportunity_score,
    -coverage_confidence,
    -controller_component,
    -constraint_component,
    company_key,
)
```

Assign one-based ordinal ranks. Ties do not share a rank.

- [ ] **Step 3: Implement `build()`**

```python
def build(
    self,
    controller_version: str | None = None,
) -> OpportunityBuild:
    ...
```

Build one Opportunity row per Controller metric row, apply the formulas exactly, derive types from persisted evidence-backed controller components and paths, and preserve evidence IDs.

- [ ] **Step 4: Run metrics, builder, path, and ranking tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/opportunity_builder.py test_opportunity_metrics.py test_opportunity_ranking.py
git commit -m "feat: calculate hidden opportunity intelligence"
```

### Task 7: Validate Opportunity Builds

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/opportunity_validator.py`
- Create: `test_opportunity_validation.py`

- [ ] **Step 1: Write failing validation tests**

Cover:

```text
negative or above-100 score
missing Controller snapshot reference
missing Graph snapshot reference
Controller/Graph reference mismatch
duplicate company record
duplicate rank
missing evidence
orphan evidence
invalid reasoning path
path not present in Controller evidence
configured weights not equal to approved constants
applied weights not summing to one
unavailable component with non-null score
unavailable component with positive applied weight
available market component without source table/timestamp/value
ambiguous zero treated as available
checksum mismatch
non-deterministic output
```

- [ ] **Step 2: Run and verify missing validator**

- [ ] **Step 3: Implement validation**

```python
class OpportunityValidationError(ValueError):
    ...


class OpportunityValidator:
    def validate(
        self,
        build: OpportunityBuild,
        repository: IndustrialGraphRepository,
    ) -> None:
        ...
```

Recompute formulas, weights, coverage, types, paths, and checksum inputs. Validate evidence IDs against the selected Graph build and ensure each stored path is an exact Controller path or its permitted Theme-first reversal.

- [ ] **Step 4: Run validation tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/opportunity_validator.py test_opportunity_validation.py
git commit -m "feat: validate hidden opportunity builds"
```

### Task 8: Persist Opportunity Metrics And Paths

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/graph_repository.py`
- Extend: `test_opportunity_snapshot.py`

- [ ] **Step 1: Write failing persistence tests**

Assert:

- one metric row per candidate company;
- one ordered row per retained reasoning path;
- source JSON preserves source table, timestamp, and value;
- every market component has an availability state;
- ambiguous zero remains unavailable after round trip;
- active queries return active-snapshot rows only;
- Controller and Graph snapshot statuses are unchanged.

- [ ] **Step 2: Run and verify missing methods**

- [ ] **Step 3: Implement persistence methods**

```python
def insert_opportunity_snapshot(...) -> int: ...
def insert_opportunity_metrics(...) -> int: ...
def insert_opportunity_reasoning_paths(...) -> int: ...
def get_opportunity_snapshot(...) -> OpportunitySnapshot | None: ...
def get_active_opportunity_snapshot(...) -> OpportunitySnapshot | None: ...
def get_opportunity_metrics(...) -> list[OpportunityIntelligence]: ...
def get_opportunity_reasoning_paths(...) -> dict[NodeKey, tuple[tuple[NodeKey, ...], ...]]: ...
```

Serialize all mappings and records with canonical sorted JSON and `allow_nan=False`.

- [ ] **Step 4: Run persistence tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/graph_repository.py test_opportunity_snapshot.py
git commit -m "feat: persist hidden opportunity intelligence"
```

### Task 9: Add Transactional Opportunity Snapshot Lifecycle

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/opportunity_engine.py`
- Create: `test_opportunity_engine.py`
- Extend: `test_opportunity_snapshot.py`

- [ ] **Step 1: Write failing lifecycle and rollback tests**

Require:

```python
first = engine.build_and_activate()
second = engine.build_and_activate()

assert first.opportunity_version != second.opportunity_version
assert first.checksum == second.checksum
assert second.status == "active"
```

Force failure after superseding the prior Opportunity snapshot and prove rollback leaves the first active. Record Controller and Graph status rows before and after and assert they are byte-for-byte unchanged.

- [ ] **Step 2: Run and verify missing engine**

- [ ] **Step 3: Implement engine**

```python
class OpportunityEngine:
    def build(self, controller_version: str | None = None) -> OpportunityBuild: ...
    def stage(self, build: OpportunityBuild) -> OpportunitySnapshot: ...
    def activate(self, opportunity_version: str) -> OpportunitySnapshot: ...
    def build_and_activate(
        self,
        controller_version: str | None = None,
    ) -> OpportunitySnapshot: ...
```

Stage transaction:

1. validate build;
2. insert `opportunity_snapshots` as `building`;
3. insert metrics and paths;
4. verify stored counts;
5. commit or rollback.

Activation transaction:

1. reload staged build;
2. verify checksum;
3. require status `building` or `active`;
4. supersede only the prior active Opportunity snapshot;
5. activate target;
6. never update Controller or Graph tables;
7. commit or rollback.

- [ ] **Step 4: Run engine tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/opportunity_engine.py test_opportunity_engine.py test_opportunity_snapshot.py
git commit -m "feat: add transactional opportunity snapshots"
```

### Task 10: Add Internal Opportunity Queries

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/opportunity_engine.py`
- Extend: `test_opportunity_engine.py`
- Extend: `test_opportunity_ranking.py`

- [ ] **Step 1: Write failing internal-query tests**

```python
ranked = engine.get_ranked_opportunities(limit=10)
assert ranked == sorted(ranked, key=lambda row: (row.rank, row.company_key))

row = engine.get_opportunity_intelligence(("Company", "company:KLAC"))
assert row is not None
assert row.evidence_ids
assert row.reasoning_paths
```

No active snapshot returns `[]`/`None`; unknown companies are not fabricated.

- [ ] **Step 2: Implement internal methods**

```python
def get_ranked_opportunities(
    self,
    *,
    limit: int | None = None,
) -> list[OpportunityIntelligence]: ...

def get_opportunity_intelligence(
    self,
    company: NodeKey,
) -> OpportunityIntelligence | None: ...
```

Do not add FastAPI routes or aggregate response fields.

- [ ] **Step 3: Run query and ranking tests**

- [ ] **Step 4: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/opportunity_engine.py test_opportunity_engine.py test_opportunity_ranking.py
git commit -m "feat: query hidden opportunity intelligence"
```

### Task 11: Export Internals And Run Focused Regression

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/__init__.py`

- [ ] **Step 1: Export internal types**

Export:

```text
MarketComponent
MarketSourceRecord
OpportunityBuild
OpportunityEngine
OpportunityIntelligence
OpportunitySnapshot
OpportunityValidationError
OpportunityValidator
opportunity_build_checksum
```

- [ ] **Step 2: Run all seven Opportunity suites**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest `
  test_opportunity_metrics.py `
  test_opportunity_engine.py `
  test_opportunity_builder.py `
  test_opportunity_validation.py `
  test_opportunity_paths.py `
  test_opportunity_snapshot.py `
  test_opportunity_ranking.py -q
```

- [ ] **Step 3: Run Controller and Industrial Graph regressions**

```powershell
$tests = Get-ChildItem -Name `
  'test_graph_*.py', `
  'test_supply_chain_*.py', `
  'test_technology_*.py', `
  'test_process_*.py', `
  'test_material_*.py', `
  'test_equipment_*.py', `
  'test_constraint_*.py', `
  'test_controller_*.py', `
  'test_opportunity_*.py'
.\backend\.venv\Scripts\python.exe -m pytest $tests -q
```

- [ ] **Step 4: Confirm forbidden modules are unchanged**

```powershell
git diff --name-only -- `
  backend/main.py `
  backend/theme_intelligence/aggregate.py `
  backend/theme_intelligence/portfolio `
  backend/quant_engine `
  frontend
```

Expected: no Phase 12.9 changes.

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/__init__.py
git commit -m "feat: export hidden opportunity foundation"
```

### Task 12: Full Verification And Deliverable Audit

**Files:**
- No implementation files unless verification exposes a root-cause defect.

- [ ] **Step 1: Run complete backend suite**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest
```

- [ ] **Step 2: Run frontend TypeScript**

```powershell
Set-Location frontend
npx tsc --noEmit
```

- [ ] **Step 3: Run frontend production build**

```powershell
npm run build
```

- [ ] **Step 4: Audit a temporary Opportunity build**

Report:

```text
Graph snapshot ID/version
Controller snapshot ID/version
Opportunity snapshot ID/version
algorithm version
candidate company count
active opportunity count
opportunity types by count
available/unavailable market components by type
ambiguous zero valuation rows admitted: 0
ambiguous zero bubble rows admitted: 0
opportunities without evidence: 0
invalid reasoning paths: 0
applied-weight sums not equal to 1: 0
```

- [ ] **Step 5: Verify transactional independence**

Assert Graph and Controller snapshot IDs, statuses, checksums, and metric counts are unchanged before and after Opportunity activation.

- [ ] **Step 6: Review final diff**

```powershell
git diff --check
git status --short
```

Do not revert unrelated user changes.

## Deliverables

Report:

- changed files;
- Opportunity architecture;
- exact component formulas and weights;
- ambiguous-zero availability behavior;
- source provenance persistence;
- opportunity type derivation;
- reasoning path behavior;
- persistence and transactional activation;
- validation behavior;
- test, TypeScript, and build results;
- representative top opportunities from the current persisted snapshots;
- known limitations.

Known limitations must state:

- current beneficiary tables cannot prove an explicitly observed zero valuation or bubble penalty, so all current zeros remain unavailable;
- market inputs are copied from persisted latest-state tables at Opportunity build time, not historical market snapshots;
- results are limited by Controller and Industrial Graph evidence coverage;
- no runtime providers, live Bubble Engine, public API, frontend, Investment Committee, recommendation, or portfolio behavior is included;
- Opportunity scores are industrial research prioritization signals, not expected-return forecasts.
