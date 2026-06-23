# Phase 12.10 Decision Packet Engine Design

## Purpose

The Decision Packet Engine freezes validated Industrial Graph, Controller, and Opportunity intelligence into immutable, structured dossiers for future Committee agents.

A packet is not:

- a recommendation;
- a signal;
- a trade;
- a target price;
- a generated narrative.

A packet is a reproducible evidence object that answers, with explicit availability:

- what Theme is involved;
- what Constraint is involved;
- which Company controls or resolves it;
- what Opportunity was calculated;
- which evidence and paths support the conclusion;
- what evidence is missing;
- which risks remain unresolved.

## Scope

Create:

- `ThemeDecisionPacket`
- `CompanyDecisionPacket`
- `OpportunityDecisionPacket`
- immutable packet-family versioning;
- packet-owned path, evidence, and risk copies;
- validation and transactional activation.

Do not modify:

- Industrial Graph construction, schema contracts, or activation behavior;
- Controller formulas, persistence, or activation behavior;
- Opportunity formulas, persistence, or activation behavior;
- frontend code;
- public APIs;
- portfolio logic;
- Investment Committee behavior;
- quote, cache, search, enrichment, or provider systems.

## Source Lineage

Every packet family references exactly one:

```text
Graph snapshot
  -> Controller snapshot
    -> Opportunity snapshot
      -> Decision Packet family
```

The builder starts from one persisted Opportunity snapshot. It verifies:

1. the Opportunity snapshot exists;
2. its Controller snapshot exists;
3. the Controller snapshot ID and version match the Opportunity snapshot;
4. the Controller snapshot's Graph snapshot ID and version match the Opportunity snapshot;
5. all three checksums and source records are readable.

No active-snapshot lookup is performed after the source lineage has been selected. This prevents a packet build from mixing versions while another snapshot activates.

## Packet Cardinality

One packet family contains:

- one `OpportunityDecisionPacket` per Opportunity record;
- one `CompanyDecisionPacket` per distinct Company in the Opportunity snapshot;
- one `ThemeDecisionPacket` per distinct reachable Theme in retained Opportunity reasoning paths.

Current Opportunity snapshots have one record per Company, but Company packet construction deduplicates by canonical Company key rather than relying on that incidental property.

Deterministic identities:

```text
Theme packet subject:       Theme canonical key
Company packet subject:     Company canonical key
Opportunity packet subject: opportunity:<company canonical key>
```

Packet ordering:

```text
packet type order
subject canonical key
```

Packet type order:

```python
PACKET_TYPE_ORDER = (
    "ThemeDecisionPacket",
    "CompanyDecisionPacket",
    "OpportunityDecisionPacket",
)
```

## Structured Packet Sections

Every packet payload uses explicit dataclasses and canonical JSON. No free-form summary or explanation field exists.

### Snapshot Section

```text
graph_snapshot_id
graph_build_version
graph_checksum
controller_snapshot_id
controller_version
controller_algorithm_version
controller_checksum
opportunity_snapshot_id
opportunity_version
opportunity_algorithm_version
opportunity_checksum
packet_algorithm_version
```

### Theme Section

```text
theme_key
theme_name
theme_id
lifecycle_stage
lifecycle_confidence
research_importance
crowding
availability states
source records for each admitted scalar
```

Allowed sources:

- Theme identity and name: selected Graph snapshot;
- lifecycle and crowding: `theme_discovery_scores`;
- research importance: `theme_final_scores.research_importance` only.

For `research_importance`, copy:

```text
source_table
source_record_key
source_timestamp
source_value
availability_state
```

Do not read or copy `score_components_json` narrative fields.

### Bottleneck Section

Each entry contains:

```text
constraint_key
constraint_name
constraint_category
affected_layers
constraint_coverage
resolution_state
path references
evidence references
matched persisted bottleneck record, when allowed
```

`affected_layers` is the sorted set of non-Theme, non-Company node types adjacent to the Constraint inside retained packet paths.

`resolution_state` is one of:

```text
resolved_by_packet_company
resolved_by_other_company
unresolved
unknown
```

It is derived only from explicit resolver relationships in the selected Graph snapshot:

```text
CONSTRAINT_RESOLVED_BY_COMPANY
PROCESS_RESOLVED_BY_COMPANY
MATERIAL_RESOLVED_BY
EQUIPMENT_RESOLVED_BY
```

No beneficiary, exposure, controller label, or Opportunity score implies resolution.

### Controller Section

```text
company_key
company_name
controller_types
dependency_score
controller_score
base_score
constraint_influence
material_control
equipment_control
process_control
technology_control
resolution_influence
supply_chain_influence
coverage
coverage_confidence
path references
evidence references
```

Values are copied from the selected Controller snapshot. They are not recalculated.

### Opportunity Section

```text
company_key
opportunity_types
rank
controller_component
constraint_component
dependency_component
resolution_component
criticality_component
market_attention component and availability
valuation component and availability
bubble-risk component and availability
configured weights
applied weights
coverage_component
coverage_confidence
base_score
opportunity_score
path references
evidence references
```

Values are copied from the selected Opportunity snapshot. They are not recalculated.

### Evidence Section

```text
evidence_count
graph_evidence_count
persisted_scalar_count
evidence_coverage
evidence_source_types
evidence gaps
missing evidence
packet-owned evidence row references
```

Graph evidence is copied from `graph_evidence` by approved evidence ID.

Persisted scalar evidence is copied from:

- `theme_discovery_scores`;
- `theme_final_scores.research_importance`;
- Opportunity market-component source records.

`evidence_coverage` is documentation coverage, not risk scoring:

```python
evidence_coverage = 100 * present_required_evidence_classes / applicable_evidence_classes
```

Applicable evidence classes:

- Graph evidence;
- complete reasoning paths;
- lifecycle source, when a Theme is present;
- crowding source, when a Theme is present;
- research-importance source, when a Theme is present;
- Controller record, for Company and Opportunity packets;
- Opportunity record, for Company and Opportunity packets.

Unavailable classes create explicit gaps and remain in the denominator.

### Risk Section

Risk records are structured documentation only. There is no risk score.

Allowed risk categories and codes:

```text
constraint / CANONICAL_CONSTRAINT
constraint / UNRESOLVED_CONSTRAINT_PATH
constraint / MATCHED_PERSISTED_BOTTLENECK
availability / MARKET_ATTENTION_UNAVAILABLE
availability / VALUATION_UNAVAILABLE
availability / BUBBLE_UNAVAILABLE
coverage / LOW_CONTROLLER_COVERAGE
coverage / LOW_OPPORTUNITY_COVERAGE
evidence / MISSING_GRAPH_EVIDENCE
evidence / MISSING_PATH_EVIDENCE
validation / SOURCE_RECORD_UNAVAILABLE
```

Risk state:

```text
known
unresolved
unknown
missing
unavailable
```

Each risk record contains only:

```text
risk category
risk code
risk state
subject key
constraint key, when applicable
source table and record key, when applicable
source timestamp and value, when applicable
path references
evidence references
structured metadata
```

No severity, probability, recommendation, or generated explanation is introduced.

## Strict Narrative Policy

The builder must not read or persist:

- `theme_final_scores.major_risks`;
- `why_high_score`;
- `why_low_score`;
- conviction text;
- allocation notes;
- generated explanations;
- LLM summaries;
- recommendation text.

The packet schema has no summary, thesis, recommendation, rationale, or narrative column.

Source citations from `graph_evidence` and exact persisted evidence payload fields are allowed because they are provenance, not engine-authored prose.

## Persisted Bottleneck Admission

A `theme_bottlenecks` record is admitted only when all conditions pass:

1. its Theme matches the packet Theme display name exactly;
2. its deterministic canonical candidate key is calculated with:

```python
constraint_key(
    persisted_constraint_name(theme_name, bottleneck_name)
)
```

3. that key equals a Constraint node in the selected Graph snapshot;
4. the Constraint appears in a retained packet path;
5. `evidence_json` is a non-empty list;
6. `updated_at` is non-empty.

Copy:

- table and row ID;
- Theme name;
- bottleneck name and type;
- timeline status;
- persisted numeric fields;
- updated timestamp;
- evidence payload and content hash.

Do not copy:

- `description`;
- controller entities;
- beneficiary classifications;
- any inferred resolver status.

Unsupported or unmatched bottlenecks are omitted and recorded as no packet fact. They are not silently remapped.

## Reasoning Paths

Packets copy complete persisted Opportunity paths. They do not run a new graph search.

Rules:

- every Opportunity packet receives all paths for its Opportunity record;
- every Company packet receives the union of paths for that Company;
- every Theme packet receives paths beginning with that Theme;
- packet paths remain bounded by the source Opportunity snapshot;
- duplicate paths are removed;
- paths are sorted by length, path kind, and full canonical tuple;
- every path stores the source Opportunity path order and associated evidence IDs;
- no path splicing, shortening, or inferred inverse edge is allowed.

If a packet has no complete path, validation fails. A packet is not created from partial endpoint matching.

## Packet Coverage

Coverage is preserved, not rescored.

- Opportunity packet coverage: copied Opportunity `coverage_confidence`.
- Company packet coverage: minimum Opportunity `coverage_confidence` among that Company's records.
- Theme packet coverage: minimum Opportunity `coverage_confidence` among records whose retained paths reach that Theme.

Using the minimum prevents an aggregate packet from hiding its weakest included evidence chain.

Evidence coverage is stored separately and follows the documentation formula above.

## Immutability And Versioning

Packet content is immutable after insertion.

The database does not expose update methods for packet payload, paths, evidence, or risks.

Each build creates one packet family:

```text
packet_family_revision: positive integer
packet_family_version:
decision-<opportunity_snapshot_id>-r<revision padded to 6 digits>
```

Revision allocation occurs inside `BEGIN IMMEDIATE`:

```sql
SELECT COALESCE(MAX(packet_family_revision), 0) + 1
FROM decision_packets
WHERE opportunity_snapshot_id = ?
```

Identical source snapshots produce:

- identical packet build objects;
- identical packet checksums;
- a new immutable family revision and version when staged again.

The family checksum is the hash of all packet checksums and source lineage. Each packet also has its own content checksum.

Statuses:

```text
draft
validated
active
superseded
archived
```

Lifecycle:

1. stage inserts all rows as `draft`;
2. persistence round-trip and checksum validation promote the family to `validated`;
3. activation supersedes the prior active family and activates the target family in one transaction;
4. archive is an explicit internal operation on a non-active family;
5. no Graph, Controller, or Opportunity status is modified.

## Persistence Schema

Add only through `ThemeRepository.initialize()`.

### `decision_packets`

One row per packet:

```text
id
packet_family_version
packet_family_revision
packet_type
subject_type
subject_key
graph_snapshot_id
graph_build_version
controller_snapshot_id
controller_version
opportunity_snapshot_id
opportunity_version
packet_algorithm_version
status
coverage
evidence_coverage
payload_json
packet_checksum
family_checksum
activated_at
created_at
```

Uniqueness:

```text
packet_family_version + packet_type + subject_key
opportunity_snapshot_id + packet_family_revision + packet_type + subject_key
```

### `decision_packet_paths`

```text
id
packet_id
path_order
path_kind
source_opportunity_path_order
path_json
evidence_ids_json
created_at
```

### `decision_packet_evidence`

Packet-owned immutable copies:

```text
id
packet_id
evidence_order
evidence_kind
original_graph_evidence_id
source_table
source_record_key_json
source_timestamp
source_value_json
source_type
source_record_id
content_hash
citation
review_status
availability_state
created_at
```

### `decision_packet_risks`

```text
id
packet_id
risk_order
risk_category
risk_code
risk_state
subject_key
constraint_key
source_table
source_record_key_json
source_timestamp
source_value_json
path_orders_json
evidence_orders_json
metadata_json
created_at
```

All child tables use `ON DELETE RESTRICT`. Packet rows are never deleted through the engine.

## Builder Components

### `decision_packet_models.py`

Owns:

- packet and section dataclasses;
- risk/evidence/path records;
- allowed enums and forbidden payload keys;
- canonical serialization;
- packet and family checksums.

### `decision_packet_builder.py`

Owns:

- snapshot-lineage loading;
- packet cardinality;
- section assembly;
- scalar-source copying;
- canonical Constraint extraction;
- strict bottleneck matching;
- path/evidence/risk construction;
- deterministic ordering.

### `decision_packet_validator.py`

Owns:

- snapshot reference validation;
- packet cardinality and orphan checks;
- path reproduction;
- evidence existence and copy validation;
- forbidden narrative key scanning;
- risk-source policy;
- checksum and determinism validation.

### `decision_packet_engine.py`

Owns:

- build;
- stage;
- validate staged family;
- activate;
- archive;
- internal packet queries.

## Validation

Reject:

- missing Graph, Controller, or Opportunity snapshot;
- mismatched snapshot lineage;
- missing reasoning paths;
- truncated or fabricated paths;
- missing evidence references;
- graph evidence copies that differ from their source row;
- orphan path, evidence, risk, or packet section;
- duplicate packet identity or family version;
- unsupported packet/risk/evidence/status values;
- generated narrative fields anywhere in payload or metadata;
- persisted bottleneck risk without deterministic Constraint match and evidence;
- missing required scalar provenance;
- invalid coverage preservation;
- checksum mismatch;
- non-deterministic build output.

Forbidden payload-key scan is recursive and case-insensitive:

```text
summary
narrative
recommendation
buy
sell
target_price
why_high_score
why_low_score
major_risks
conviction_reason
allocation_notes
generated_explanation
```

Evidence citations are exempt only in the dedicated citation field of packet-owned evidence records.

## Testing

Create:

- `test_decision_packet_models.py`
- `test_decision_packet_builder.py`
- `test_decision_packet_validator.py`
- `test_decision_packet_paths.py`
- `test_decision_packet_evidence.py`
- `test_decision_packet_snapshot.py`
- `test_decision_packet_versioning.py`

Required assertions:

- identical source snapshots produce identical builds and checksums;
- packet cardinality is deterministic;
- paths are complete and preserved;
- evidence is copied and remains valid if source tables later change;
- scalar provenance is preserved;
- generated narrative keys are rejected;
- unmatched persisted bottlenecks are omitted;
- matched bottlenecks require evidence;
- coverage is preserved;
- packet rows are immutable through engine APIs;
- repeated staging creates deterministic increasing revisions;
- activation rollback preserves the previous active family;
- Graph, Controller, and Opportunity snapshots remain unchanged.

## Known Limitations

- Packets freeze only evidence available in the selected snapshots and admitted persisted scalar tables.
- Theme lifecycle, crowding, importance, and matched bottlenecks are latest-state rows copied at packet build time; they do not yet have independent historical source snapshots.
- There is no risk score, risk probability, or severity normalization.
- There is no Committee, recommendation, target price, portfolio construction, frontend, or public API.
- No packet is created for a Theme that is absent from retained Opportunity reasoning paths.
