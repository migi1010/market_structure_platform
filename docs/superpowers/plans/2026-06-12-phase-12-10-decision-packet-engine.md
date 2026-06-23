# Phase 12.10 Decision Packet Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build immutable, deterministic Theme, Company, and Opportunity evidence dossiers from one Opportunity snapshot and its exact Controller and Industrial Graph lineage.

**Architecture:** The Decision Packet Engine is a snapshot-derived dossier layer. A builder reads one immutable Opportunity snapshot, verifies its Controller and Graph lineage, copies structured metrics, complete paths, evidence, explicit gaps, and strictly admitted risks into packet-owned records, then validates and stages one immutable packet family. Family activation is transactional and independent from all source snapshot activation.

**Tech Stack:** Python 3.12, SQLite, dataclasses, canonical JSON/SHA-256, pytest.

---

## Approved Invariants

- One packet family per build from one Opportunity snapshot.
- One Opportunity packet per Opportunity record.
- One Company packet per distinct Company.
- One Theme packet per distinct reachable Theme.
- Every packet references the same Graph, Controller, and Opportunity snapshot lineage.
- Packet content is structured and deterministic.
- No generated narrative, recommendation, signal, target price, allocation, or Committee output.
- Complete Opportunity paths are copied; no graph search creates new paths.
- Graph evidence and scalar provenance are copied into packet-owned immutable rows.
- Unknown, missing, and unavailable states remain explicit.
- Packet payload and child records are immutable after insertion.
- Repeated builds from identical snapshots have identical content checksums.
- Repeated staging creates the next transactional family revision.
- Activation modifies only Decision Packet statuses.

## Files

Create:

- `backend/theme_intelligence/industrial_graph/decision_packet_models.py`
- `backend/theme_intelligence/industrial_graph/decision_packet_builder.py`
- `backend/theme_intelligence/industrial_graph/decision_packet_validator.py`
- `backend/theme_intelligence/industrial_graph/decision_packet_engine.py`
- `test_decision_packet_models.py`
- `test_decision_packet_builder.py`
- `test_decision_packet_validator.py`
- `test_decision_packet_paths.py`
- `test_decision_packet_evidence.py`
- `test_decision_packet_snapshot.py`
- `test_decision_packet_versioning.py`

Modify:

- `backend/theme_intelligence/storage/theme_repository.py`
- `backend/theme_intelligence/industrial_graph/graph_repository.py`
- `backend/theme_intelligence/industrial_graph/__init__.py`

Do not modify:

- Graph, Controller, or Opportunity builders, validators, engines, or formulas;
- `backend/main.py`;
- aggregate contracts;
- portfolio code;
- quote/cache/search/enrichment/provider code;
- frontend source.

---

### Task 1: Define Decision Packet Models And Forbidden Narrative Policy

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/decision_packet_models.py`
- Create: `test_decision_packet_models.py`

- [ ] **Step 1: Write failing model tests**

Test:

```python
def test_packet_models_reject_generated_narrative_keys() -> None:
    with pytest.raises(ValueError, match="forbidden narrative"):
        DecisionPacket(
            packet_type="CompanyDecisionPacket",
            subject_type="Company",
            subject_key="company:KLAC",
            coverage=80.0,
            evidence_coverage=75.0,
            payload={"why_high_score": "generated"},
            paths=(),
            evidence=(),
            risks=(),
        )


def test_packet_checksum_excludes_database_identity() -> None:
    first = make_packet(id=None, created_at="")
    second = make_packet(id=99, created_at="later")
    assert packet_checksum(first) == packet_checksum(second)
```

Also test packet types, risk codes/states, evidence kinds, status values, score bounds, canonical subject keys, deterministic tuple ordering, and recursive forbidden-key scanning.

- [ ] **Step 2: Run and verify import failure**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_decision_packet_models.py -q
```

- [ ] **Step 3: Implement constants**

```python
PACKET_TYPE_ORDER = (
    "ThemeDecisionPacket",
    "CompanyDecisionPacket",
    "OpportunityDecisionPacket",
)

PACKET_STATUSES = frozenset({
    "draft", "validated", "active", "superseded", "archived",
})

RISK_CODES = frozenset({
    "CANONICAL_CONSTRAINT",
    "UNRESOLVED_CONSTRAINT_PATH",
    "MATCHED_PERSISTED_BOTTLENECK",
    "MARKET_ATTENTION_UNAVAILABLE",
    "VALUATION_UNAVAILABLE",
    "BUBBLE_UNAVAILABLE",
    "LOW_CONTROLLER_COVERAGE",
    "LOW_OPPORTUNITY_COVERAGE",
    "MISSING_GRAPH_EVIDENCE",
    "MISSING_PATH_EVIDENCE",
    "SOURCE_RECORD_UNAVAILABLE",
})

FORBIDDEN_PACKET_KEYS = frozenset({
    "summary", "narrative", "recommendation", "buy", "sell",
    "target_price", "why_high_score", "why_low_score",
    "major_risks", "conviction_reason", "allocation_notes",
    "generated_explanation",
})
```

- [ ] **Step 4: Implement immutable records**

```python
@dataclass(frozen=True)
class DecisionPacketPath:
    path_kind: str
    source_opportunity_path_order: int
    path: tuple[NodeKey, ...]
    evidence_ids: tuple[int, ...]


@dataclass(frozen=True)
class DecisionPacketEvidence:
    evidence_kind: str
    original_graph_evidence_id: int | None
    source_table: str
    source_record_key: Mapping[str, str]
    source_timestamp: str | None
    source_value: Any
    source_type: str
    source_record_id: str
    content_hash: str
    citation: str | None
    review_status: str | None
    availability_state: str


@dataclass(frozen=True)
class DecisionPacketRisk:
    risk_category: str
    risk_code: str
    risk_state: str
    subject_key: str
    constraint_key: str | None
    source_table: str | None
    source_record_key: Mapping[str, str]
    source_timestamp: str | None
    source_value: Any
    path_orders: tuple[int, ...]
    evidence_orders: tuple[int, ...]
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class DecisionPacket:
    packet_type: str
    subject_type: str
    subject_key: str
    coverage: float
    evidence_coverage: float
    payload: Mapping[str, Any]
    paths: tuple[DecisionPacketPath, ...]
    evidence: tuple[DecisionPacketEvidence, ...]
    risks: tuple[DecisionPacketRisk, ...]


@dataclass(frozen=True)
class DecisionPacketBuild:
    graph_snapshot_id: int
    graph_build_version: str
    controller_snapshot_id: int
    controller_version: str
    opportunity_snapshot_id: int
    opportunity_version: str
    algorithm_version: str
    packets: tuple[DecisionPacket, ...]


@dataclass(frozen=True)
class DecisionPacketFamily:
    packet_family_version: str
    packet_family_revision: int
    graph_snapshot_id: int
    controller_snapshot_id: int
    opportunity_snapshot_id: int
    algorithm_version: str
    status: str
    family_checksum: str
    packet_count: int
    path_count: int
    evidence_count: int
    risk_count: int
    activated_at: str | None = None
    created_at: str = ""
```

Add `packet_checksum()` and `packet_build_checksum()` using canonical JSON and excluding database IDs, status, timestamps, family version, and revision.

- [ ] **Step 5: Run model tests**

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/decision_packet_models.py test_decision_packet_models.py
git commit -m "feat: define decision packet models"
```

### Task 2: Add Additive Packet Persistence Schema

**Files:**
- Modify: `backend/theme_intelligence/storage/theme_repository.py`
- Create: `test_decision_packet_snapshot.py`

- [ ] **Step 1: Write failing schema tests**

Assert `ThemeRepository.initialize()` creates exactly the approved packet tables and indexes without changing existing schemas.

- [ ] **Step 2: Run and verify missing tables**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_decision_packet_snapshot.py::test_decision_packet_schema_is_additive -q
```

- [ ] **Step 3: Add schema**

```sql
CREATE TABLE IF NOT EXISTS decision_packets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    packet_family_version TEXT NOT NULL,
    packet_family_revision INTEGER NOT NULL,
    packet_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    graph_snapshot_id INTEGER NOT NULL,
    graph_build_version TEXT NOT NULL,
    controller_snapshot_id INTEGER NOT NULL,
    controller_version TEXT NOT NULL,
    opportunity_snapshot_id INTEGER NOT NULL,
    opportunity_version TEXT NOT NULL,
    packet_algorithm_version TEXT NOT NULL,
    status TEXT NOT NULL,
    coverage REAL NOT NULL,
    evidence_coverage REAL NOT NULL,
    payload_json TEXT NOT NULL,
    packet_checksum TEXT NOT NULL,
    family_checksum TEXT NOT NULL,
    activated_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(packet_family_version, packet_type, subject_key),
    UNIQUE(
        opportunity_snapshot_id, packet_family_revision,
        packet_type, subject_key
    ),
    FOREIGN KEY(graph_snapshot_id) REFERENCES graph_snapshots(id),
    FOREIGN KEY(controller_snapshot_id) REFERENCES controller_snapshots(id),
    FOREIGN KEY(opportunity_snapshot_id) REFERENCES opportunity_snapshots(id)
);

CREATE TABLE IF NOT EXISTS decision_packet_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    packet_id INTEGER NOT NULL,
    path_order INTEGER NOT NULL,
    path_kind TEXT NOT NULL,
    source_opportunity_path_order INTEGER NOT NULL,
    path_json TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(packet_id, path_order),
    FOREIGN KEY(packet_id) REFERENCES decision_packets(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS decision_packet_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    packet_id INTEGER NOT NULL,
    evidence_order INTEGER NOT NULL,
    evidence_kind TEXT NOT NULL,
    original_graph_evidence_id INTEGER,
    source_table TEXT NOT NULL,
    source_record_key_json TEXT NOT NULL,
    source_timestamp TEXT,
    source_value_json TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    citation TEXT,
    review_status TEXT,
    availability_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(packet_id, evidence_order),
    FOREIGN KEY(packet_id) REFERENCES decision_packets(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS decision_packet_risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    packet_id INTEGER NOT NULL,
    risk_order INTEGER NOT NULL,
    risk_category TEXT NOT NULL,
    risk_code TEXT NOT NULL,
    risk_state TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    constraint_key TEXT,
    source_table TEXT,
    source_record_key_json TEXT NOT NULL,
    source_timestamp TEXT,
    source_value_json TEXT NOT NULL,
    path_orders_json TEXT NOT NULL,
    evidence_orders_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(packet_id, risk_order),
    FOREIGN KEY(packet_id) REFERENCES decision_packets(id) ON DELETE RESTRICT
);
```

Indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_decision_packets_family_status
ON decision_packets(packet_family_version, status);

CREATE INDEX IF NOT EXISTS idx_decision_packets_active
ON decision_packets(status, packet_type, subject_key);

CREATE INDEX IF NOT EXISTS idx_decision_packets_opportunity_revision
ON decision_packets(opportunity_snapshot_id, packet_family_revision);

CREATE INDEX IF NOT EXISTS idx_decision_packet_paths_packet
ON decision_packet_paths(packet_id, path_order);

CREATE INDEX IF NOT EXISTS idx_decision_packet_evidence_packet
ON decision_packet_evidence(packet_id, evidence_order);

CREATE INDEX IF NOT EXISTS idx_decision_packet_risks_packet
ON decision_packet_risks(packet_id, risk_order);
```

- [ ] **Step 4: Run schema and existing repository tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_decision_packet_snapshot.py test_theme_repository.py test_opportunity_snapshot.py -q
```

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/storage/theme_repository.py test_decision_packet_snapshot.py
git commit -m "feat: add decision packet schema"
```

### Task 3: Add Snapshot-Bound Packet Source Queries

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/graph_repository.py`
- Create: `test_decision_packet_builder.py`

- [ ] **Step 1: Write failing lineage tests**

Test:

```python
context = repository.get_decision_packet_source_context(
    opportunity.opportunity_version
)

assert context.opportunity_snapshot.id == opportunity.id
assert context.controller_snapshot.id == opportunity.controller_snapshot_id
assert context.graph_snapshot.id == opportunity.graph_snapshot_id
assert context.opportunities
assert context.controllers
```

Corrupt one stored lineage field and assert the query fails instead of falling back to an active snapshot.

- [ ] **Step 2: Run and verify missing query**

- [ ] **Step 3: Implement source context**

Define a frozen `DecisionPacketSourceContext` in the model module and implement:

```python
def get_decision_packet_source_context(
    self,
    opportunity_version: str | None = None,
) -> DecisionPacketSourceContext:
    ...
```

The method loads the selected or active Opportunity snapshot once, then loads exact referenced Controller and Graph snapshots. It also loads Opportunity and Controller records for those exact versions.

- [ ] **Step 4: Add exact evidence and scalar queries**

```python
def get_graph_evidence_by_ids(
    self,
    evidence_ids: Iterable[int],
) -> tuple[IndustrialGraphEvidence, ...]: ...

def get_packet_theme_scalars(
    self,
    theme_names: Iterable[str],
) -> tuple[PersistedPacketScalar, ...]: ...

def get_packet_bottlenecks(
    self,
    theme_names: Iterable[str],
) -> tuple[PersistedPacketBottleneck, ...]: ...
```

Scalar query admits:

- lifecycle and crowding from `theme_discovery_scores`;
- `research_importance` only from `theme_final_scores`.

Do not select `score_components_json`.

- [ ] **Step 5: Run source-query tests**

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/graph_repository.py backend/theme_intelligence/industrial_graph/decision_packet_models.py test_decision_packet_builder.py
git commit -m "feat: expose decision packet source context"
```

### Task 4: Build Packet-Owned Complete Paths

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/decision_packet_builder.py`
- Create: `test_decision_packet_paths.py`

- [ ] **Step 1: Write failing path tests**

Assert:

- Opportunity packets contain every source Opportunity path;
- Company packets contain the deterministic union for that Company;
- Theme packets contain paths beginning with that Theme only;
- path contents are byte-equivalent after canonical serialization;
- no packet path is shorter than its source;
- duplicate paths are removed;
- packets without paths are rejected from the build.

- [ ] **Step 2: Run and verify missing builder**

- [ ] **Step 3: Implement path indexing**

```python
class DecisionPacketBuilder:
    ALGORITHM_VERSION = "decision-packet-v1"

    def _source_paths(
        self,
        opportunities: tuple[OpportunityIntelligence, ...],
    ) -> dict[NodeKey, tuple[DecisionPacketPath, ...]]:
        ...

    def _paths_for_theme(
        self,
        theme: NodeKey,
        source_paths: Mapping[NodeKey, tuple[DecisionPacketPath, ...]],
    ) -> tuple[DecisionPacketPath, ...]:
        ...
```

Path evidence IDs are copied from the source Opportunity record. Path order is recalculated deterministically inside each packet while `source_opportunity_path_order` preserves source position.

- [ ] **Step 4: Run path tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/decision_packet_builder.py test_decision_packet_paths.py
git commit -m "feat: preserve decision packet paths"
```

### Task 5: Copy Graph Evidence And Scalar Provenance

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/decision_packet_builder.py`
- Create: `test_decision_packet_evidence.py`

- [ ] **Step 1: Write failing evidence tests**

Required assertions:

```text
all source Opportunity evidence IDs are copied
graph evidence content hashes and citations match
scalar source table/timestamp/value are preserved
research_importance does not copy score_components_json
packet evidence survives later source-row mutation
missing graph evidence fails
evidence order is deterministic
```

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement evidence copies**

```python
def _graph_evidence(
    self,
    evidence_ids: Iterable[int],
) -> tuple[DecisionPacketEvidence, ...]:
    ...

def _scalar_evidence(
    self,
    packet_payload: Mapping[str, Any],
) -> tuple[DecisionPacketEvidence, ...]:
    ...
```

Graph evidence copies use:

```text
evidence_kind = graph_evidence
source_table = graph_evidence
original_graph_evidence_id = source ID
availability_state = available
```

Scalar evidence copies use:

```text
evidence_kind = persisted_scalar
original_graph_evidence_id = NULL
source table/key/timestamp/value copied exactly
```

- [ ] **Step 4: Implement evidence coverage**

```python
evidence_coverage = (
    100.0 * present_required_classes / applicable_required_classes
)
```

Store missing classes as structured evidence gaps in the payload and matching risk rows.

- [ ] **Step 5: Run evidence tests**

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/decision_packet_builder.py test_decision_packet_evidence.py
git commit -m "feat: freeze packet evidence"
```

### Task 6: Build Structured Theme, Bottleneck, Controller, And Opportunity Sections

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/decision_packet_builder.py`
- Extend: `test_decision_packet_builder.py`

- [ ] **Step 1: Write failing packet-cardinality tests**

Test:

```python
build = builder.build(opportunity.opportunity_version)

assert count(build, "OpportunityDecisionPacket") == len(source_opportunities)
assert count(build, "CompanyDecisionPacket") == len({
    row.company_key for row in source_opportunities
})
assert count(build, "ThemeDecisionPacket") == len(reachable_themes)
assert build == builder.build(opportunity.opportunity_version)
```

- [ ] **Step 2: Write failing structured-section tests**

Assert required keys exist, values equal selected snapshot records, coverage follows the approved minimum rule, unavailable values remain explicit, and no forbidden narrative keys occur.

- [ ] **Step 3: Implement `build()`**

```python
def build(
    self,
    opportunity_version: str | None = None,
) -> DecisionPacketBuild:
    ...
```

Use the exact packet cardinality, ordering, section fields, and coverage rules from the design.

- [ ] **Step 4: Implement Constraint sections**

Read Constraint nodes from retained paths and selected Graph metadata. Determine affected layers and explicit resolver state from selected Graph relationships only.

Do not infer resolution from:

- beneficiary records;
- exposure edges;
- Controller types alone;
- Opportunity types or scores.

- [ ] **Step 5: Run builder tests**

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/decision_packet_builder.py test_decision_packet_builder.py
git commit -m "feat: build structured decision packets"
```

### Task 7: Add Strict Risk Documentation And Bottleneck Matching

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/decision_packet_builder.py`
- Extend: `test_decision_packet_builder.py`
- Extend: `test_decision_packet_evidence.py`

- [ ] **Step 1: Write failing risk-policy tests**

Cover:

```text
canonical path Constraint creates CANONICAL_CONSTRAINT
unresolved explicit path creates UNRESOLVED_CONSTRAINT_PATH
unavailable valuation creates VALUATION_UNAVAILABLE
unavailable bubble creates BUBBLE_UNAVAILABLE
low coverage creates coverage risk
matched persisted bottleneck requires evidence
unmatched bottleneck is omitted
empty-evidence bottleneck is omitted
description/controller_entities/beneficiaries are not copied
```

- [ ] **Step 2: Run and verify failure**

- [ ] **Step 3: Implement deterministic bottleneck matching**

```python
candidate_key = constraint_key(
    persisted_constraint_name(row.theme_name, row.bottleneck_name)
)
```

Admit only when the key is present in both the selected Graph snapshot and retained packet paths, and evidence is non-empty.

- [ ] **Step 4: Implement risk records**

Create only approved risk codes. Use sorted path/evidence order references. Do not calculate severity, probability, or an aggregate risk score.

- [ ] **Step 5: Run risk and evidence tests**

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/decision_packet_builder.py test_decision_packet_builder.py test_decision_packet_evidence.py
git commit -m "feat: document decision packet risks"
```

### Task 8: Validate Packet Builds And Narrative Exclusion

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/decision_packet_validator.py`
- Create: `test_decision_packet_validator.py`

- [ ] **Step 1: Write failing validation tests**

Cover:

```text
missing Graph snapshot
missing Controller snapshot
missing Opportunity snapshot
lineage mismatch
missing paths
truncated/fabricated path
missing evidence
altered evidence copy
orphan path/evidence/risk
duplicate packet identity
unsupported packet/risk/status value
forbidden narrative key at any nesting depth
unmatched persisted bottleneck risk
missing scalar provenance
incorrect preserved coverage
packet checksum mismatch
non-deterministic build
```

- [ ] **Step 2: Run and verify missing validator**

- [ ] **Step 3: Implement validator**

```python
class DecisionPacketValidationError(ValueError):
    ...


class DecisionPacketValidator:
    def validate(
        self,
        build: DecisionPacketBuild,
        repository: IndustrialGraphRepository,
    ) -> None:
        ...
```

Validation reloads exact source snapshots and records. It compares complete paths and evidence copies to source rows and recursively scans payload, risk metadata, and scalar values for forbidden keys.

- [ ] **Step 4: Validate deterministic checksums**

Call packet and build checksum functions twice and compare results. Reconstruct expected packet checksums independently from canonical payloads.

- [ ] **Step 5: Run validator tests**

- [ ] **Step 6: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/decision_packet_validator.py test_decision_packet_validator.py
git commit -m "feat: validate decision packets"
```

### Task 9: Implement Packet Persistence And Immutable Round Trip

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/graph_repository.py`
- Extend: `test_decision_packet_snapshot.py`
- Create: `test_decision_packet_versioning.py`

- [ ] **Step 1: Write failing revision-allocation tests**

Inside separate stage transactions:

```python
first = repository.next_packet_family_revision(conn, opportunity_snapshot_id)
insert_family(first)
second = repository.next_packet_family_revision(conn, opportunity_snapshot_id)

assert first == 1
assert second == 2
assert family_version(snapshot_id, second).endswith("-r000002")
```

- [ ] **Step 2: Write failing round-trip tests**

Assert packet payloads, paths, evidence, risks, checksums, and ordering survive persistence unchanged. Assert no repository update/delete method exists for packet content.

- [ ] **Step 3: Implement repository methods**

```python
def next_packet_family_revision(
    self,
    conn: sqlite3.Connection,
    opportunity_snapshot_id: int,
) -> int: ...

def insert_decision_packets(...) -> dict[tuple[str, str], int]: ...
def insert_decision_packet_paths(...) -> int: ...
def insert_decision_packet_evidence(...) -> int: ...
def insert_decision_packet_risks(...) -> int: ...
def get_packet_family(...) -> DecisionPacketFamily | None: ...
def get_active_packet_family(...) -> DecisionPacketFamily | None: ...
def get_decision_packets(...) -> list[DecisionPacket]: ...
```

Family version:

```python
f"decision-{opportunity_snapshot_id}-r{revision:06d}"
```

- [ ] **Step 4: Run persistence and versioning tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/graph_repository.py test_decision_packet_snapshot.py test_decision_packet_versioning.py
git commit -m "feat: persist immutable decision packets"
```

### Task 10: Add Transactional Packet Lifecycle

**Files:**
- Create: `backend/theme_intelligence/industrial_graph/decision_packet_engine.py`
- Extend: `test_decision_packet_snapshot.py`
- Extend: `test_decision_packet_versioning.py`

- [ ] **Step 1: Write failing lifecycle tests**

Required behavior:

```python
first = engine.build_and_activate(opportunity.opportunity_version)
second = engine.build_and_activate(opportunity.opportunity_version)

assert first.packet_family_revision == 1
assert second.packet_family_revision == 2
assert first.family_checksum == second.family_checksum
assert second.status == "active"
```

Also test:

- stage finishes as `validated`;
- activation rollback preserves the previous family;
- checksum tampering rejects activation;
- archive rejects the active family and archives a validated/superseded family;
- source snapshot status/checksum/count rows remain unchanged.

- [ ] **Step 2: Run and verify missing engine**

- [ ] **Step 3: Implement engine**

```python
class DecisionPacketEngine:
    def build(
        self,
        opportunity_version: str | None = None,
    ) -> DecisionPacketBuild: ...

    def stage(self, build: DecisionPacketBuild) -> DecisionPacketFamily: ...
    def activate(self, packet_family_version: str) -> DecisionPacketFamily: ...
    def archive(self, packet_family_version: str) -> DecisionPacketFamily: ...
    def build_and_activate(
        self,
        opportunity_version: str | None = None,
    ) -> DecisionPacketFamily: ...
```

Stage transaction:

1. validate build;
2. `BEGIN IMMEDIATE`;
3. allocate next revision;
4. insert packet rows as `draft`;
5. insert paths, evidence, and risks;
6. reload and compare checksums/counts;
7. update only the family rows to `validated`;
8. commit or rollback.

Activation transaction:

1. require target family `validated` or `active`;
2. reload and validate family checksum;
3. supersede prior active family;
4. activate every target family packet with one timestamp;
5. commit or rollback.

- [ ] **Step 4: Run lifecycle tests**

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/decision_packet_engine.py test_decision_packet_snapshot.py test_decision_packet_versioning.py
git commit -m "feat: add decision packet lifecycle"
```

### Task 11: Add Internal Packet Queries And Exports

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/decision_packet_engine.py`
- Modify: `backend/theme_intelligence/industrial_graph/__init__.py`
- Extend: `test_decision_packet_snapshot.py`

- [ ] **Step 1: Write failing query tests**

```python
theme_packets = engine.get_packets(packet_type="ThemeDecisionPacket")
company = engine.get_packet(
    "CompanyDecisionPacket",
    "company:KLAC",
)

assert theme_packets == sorted(
    theme_packets,
    key=lambda row: (PACKET_TYPE_ORDER.index(row.packet_type), row.subject_key),
)
assert company is not None
```

Unknown subjects and no active family return `None`/`[]`.

- [ ] **Step 2: Implement internal queries**

```python
def get_packets(
    self,
    *,
    packet_type: str | None = None,
) -> list[DecisionPacket]: ...

def get_packet(
    self,
    packet_type: str,
    subject_key: str,
) -> DecisionPacket | None: ...
```

Do not add public routes.

- [ ] **Step 3: Export internal packet types**

Export models, builder, validator, engine, and checksum functions from `industrial_graph.__init__`.

- [ ] **Step 4: Run all seven packet suites**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest `
  test_decision_packet_models.py `
  test_decision_packet_builder.py `
  test_decision_packet_validator.py `
  test_decision_packet_paths.py `
  test_decision_packet_evidence.py `
  test_decision_packet_snapshot.py `
  test_decision_packet_versioning.py -q
```

- [ ] **Step 5: Commit**

```powershell
git add backend/theme_intelligence/industrial_graph/decision_packet_engine.py backend/theme_intelligence/industrial_graph/__init__.py test_decision_packet_snapshot.py
git commit -m "feat: query decision packets"
```

### Task 12: Regression, Full Verification, And Packet Audit

**Files:**
- No implementation files unless a verified root-cause defect is found.

- [ ] **Step 1: Run Industrial Intelligence regression**

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
  'test_opportunity_*.py', `
  'test_decision_packet_*.py'
.\backend\.venv\Scripts\python.exe -m pytest $tests -q
```

- [ ] **Step 2: Run complete backend suite**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest
```

- [ ] **Step 3: Run frontend safety checks**

```powershell
Set-Location frontend
npx tsc --noEmit
npm run build
```

- [ ] **Step 4: Audit a temporary packet family**

Report:

```text
Graph snapshot ID/version/checksum
Controller snapshot ID/version/checksum
Opportunity snapshot ID/version/checksum
Packet family version/revision/checksum
Theme packet count
Company packet count
Opportunity packet count
path/evidence/risk counts
packets without paths: 0
packets without evidence: 0
forbidden narrative keys: 0
unmatched bottlenecks admitted: 0
packet checksum mismatches: 0
source snapshot mutations: 0
```

- [ ] **Step 5: Inspect example packets**

Print one packet of each type as canonical structured JSON. Confirm:

- no recommendation fields;
- no generated narrative;
- complete Theme-to-Company paths;
- evidence citations and scalar provenance;
- explicit unavailable and missing states;
- structured risk records only.

- [ ] **Step 6: Confirm forbidden modules have no Phase 12.10 changes**

```powershell
git diff --name-only -- `
  backend/main.py `
  backend/theme_intelligence/aggregate.py `
  backend/theme_intelligence/portfolio `
  backend/quant_engine `
  frontend
```

- [ ] **Step 7: Final diff checks**

```powershell
git diff --check
git status --short
```

Do not revert unrelated user changes.

## Deliverables

Report:

- changed files;
- Decision Packet architecture;
- packet schema;
- Graph/Controller/Opportunity snapshot references;
- Theme, Bottleneck, Controller, Opportunity section behavior;
- evidence copies and scalar provenance;
- structured risk policy;
- complete reasoning paths;
- validation;
- immutable family versioning and activation;
- example Theme, Company, and Opportunity packets;
- backend, TypeScript, and build results;
- known limitations.

Known limitations must include:

- Theme scalar and matched bottleneck sources are copied from mutable latest-state tables at packet build time;
- unsupported or unmatched bottlenecks are omitted rather than guessed;
- no risk scoring, Committee, recommendation, signal, target price, portfolio, public API, or frontend is included;
- packet quality remains bounded by selected Graph, Controller, and Opportunity snapshot coverage.
