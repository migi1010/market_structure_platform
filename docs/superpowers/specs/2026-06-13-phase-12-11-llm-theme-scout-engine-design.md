# Phase 12.11 LLM Theme Scout Engine Design

## Purpose

Theme Scout is a pre-graph research system that discovers and ranks emerging
industrial theme candidates before they become verified Industrial Graph
themes.

Its output is a research candidate, not:

- a verified Theme node;
- a graph edge;
- graph evidence;
- a Controller;
- an Opportunity;
- a Decision Packet;
- a recommendation, signal, target price, or allocation.

The platform flow is:

```text
Persisted research sources
  -> Theme Scout
    -> Theme Candidates
      -> explicit research review
        -> Research Pipeline
          -> Industrial Graph
            -> Controller
              -> Opportunity
                -> Decision Packet
                  -> Committee
```

## Architecture Findings

### Persistence and snapshots

- `ThemeRepository.initialize()` owns additive SQLite schema creation.
- The canonical local database is `backend/.cache/market_cache.sqlite3`.
- Phase 12 already uses immutable snapshot families with deterministic
  checksums, validation before activation, transactional activation, and
  rollback.
- Graph, Controller, Opportunity, and Decision Packet snapshots are downstream
  of verified graph evidence and must not be modified by Scout.

### Existing discovery system

- The Phase 10 discovery engine can perform live provider collection.
- Its extractor resolves aliases into a fixed canonical theme set.
- It is therefore unsuitable as the Scout build engine:
  - Scout builds must use persisted source rows only;
  - Scout must be able to propose previously unknown candidate names;
  - Scout must preserve exact evidence identifiers and citations;
  - Scout must not write approved graph evidence.

Existing discovery tables remain eligible source tables only when a row has:

- a persisted source table and row identifier;
- a source timestamp;
- a stable source identifier;
- a citation or URL;
- sufficient source content to support the admitted claim.

Rows missing any required provenance field are unavailable to Scout. Scout does
not synthesize missing provenance.

### Current source coverage

The current repository contains persisted Phase 10 mentions, entities,
catalysts, bottlenecks, discovery scores, final scores, and approved graph
evidence. It does not contain dedicated normalized tables for:

- patents;
- conference observations;
- earnings-call transcripts;
- technology observations;
- generic reviewed research notes.

The first production Scout snapshot may therefore be empty or narrow. The six
approved UX examples are validation labels only and must not be seeded as
candidate records without persisted evidence.

### Frontend boundaries

- Primary navigation is registered in `frontend/src/modules/terminalModules.ts`.
- Workspace routing is owned by `WorkspaceContext` and `Dashboard`.
- Universal search uses typed result identities and target tabs.
- Scout must be a separate workspace between Themes and Supply Chain.
- It must not be embedded in `ThemeResearchPage`, because candidates and
  verified graph Themes have different truth states.

## Root Causes Addressed

1. Fixed-taxonomy extraction cannot discover a novel candidate identity.
2. Live provider collection cannot produce a reproducible Scout snapshot.
3. Existing graph evidence cannot be reclassified as candidate evidence without
   retaining its original source identity and truth state.
4. Repeated live LLM calls are not deterministic enough to be snapshot inputs.
5. No current schema separates candidate hypotheses from verified graph facts.
6. No current lifecycle records explicit human approval before graph handoff.
7. No current UI exposes evidence clusters, readiness, or candidate evolution.

## Core Boundary

Theme Scout has two stages:

```text
Frozen persisted evidence bundle
  -> proposal provider
    -> frozen structured proposal payload
      -> deterministic admission, scoring, validation, and snapshot activation
```

The proposal provider may use an LLM, but:

- it receives persisted evidence only;
- it returns structured proposals only;
- its prose is not evidence;
- it cannot create citations;
- it cannot create graph nodes or edges;
- it cannot approve a candidate;
- it cannot invoke quote, enrichment, ranking, Controller, Opportunity,
  Decision Packet, or Committee systems.

Determinism is defined as:

> identical persisted evidence bundle, frozen proposal payload, algorithm
> version, and configuration produce identical candidate records, ordering,
> paths, and checksums.

The engine never claims that two independent model calls must produce identical
proposal payloads. The proposal payload is frozen and checksummed before the
deterministic build begins.

## Proposal Provider

Define a `ThemeScoutProposalProvider` protocol. The core engine depends on this
protocol rather than a vendor SDK.

Production configuration is optional and explicit:

```text
THEME_SCOUT_LLM_BASE_URL
THEME_SCOUT_LLM_API_KEY
THEME_SCOUT_LLM_MODEL
THEME_SCOUT_LLM_PROMPT_VERSION
```

An OpenAI-compatible structured JSON adapter may be configured through these
settings. No provider call occurs:

- during application startup;
- during an HTTP GET;
- during graph seed activation;
- when configuration is unavailable.

An explicit Scout build fails clearly when no proposal provider is configured.
Tests use a fixed proposal provider.

## Additive Schema

Schema is added only through `ThemeRepository.initialize()`.

### `theme_scout_snapshots`

Required columns:

```text
id
scout_version
algorithm_version
prompt_version
provider_name
provider_model
weights_json
source_watermark
evidence_bundle_checksum
proposal_checksum
content_checksum
candidate_count
status
created_at
validated_at
activated_at
superseded_at
failure_code
failure_detail
```

Snapshot statuses:

```text
building
validated
active
superseded
failed
```

Only one Scout snapshot may be active.

### `theme_candidates`

Required columns:

```text
id
snapshot_id
candidate_key
display_name
description
lifecycle_status
status_actor
status_reason
status_changed_at
raw_metrics_json
normalized_metrics_json
applied_weights_json
confidence_score
novelty_score
velocity_score
breadth_score
capital_score
bottleneck_potential_score
serendipity_score
theme_score
signal_count
evidence_count
source_count
source_types_json
research_readiness_json
generated_candidate_summary
rank
content_checksum
created_at
```

`generated_candidate_summary` is explicitly generated candidate context. It is
never evidence and is not admitted to graph construction.

Uniqueness:

```text
(snapshot_id, candidate_key)
(snapshot_id, rank)
```

### `theme_candidate_evidence`

Required columns:

```text
id
candidate_id
evidence_order
source_table
source_record_id
source_type
source_timestamp
source_identifier
citation
content_hash
domain_type
cluster_key
source_value_json
availability_state
created_at
```

Allowed domain types:

```text
Technology
Process
Material
Equipment
Constraint
Company
Other
```

`availability_state` is `available` or `unavailable`. Only available evidence
can support metrics or paths. Unavailable rows may be retained only to make a
known gap explicit.

### `theme_candidate_paths`

Required columns:

```text
id
candidate_id
path_order
path_type
path_payload_json
evidence_orders_json
content_checksum
created_at
```

Allowed path types:

```text
SIGNAL_CLUSTER
THEME_EVOLUTION
POTENTIAL_BOTTLENECK
RESEARCH_HANDOFF
```

Every path step must reference candidate-owned evidence orders. There are no
unreferenced generated steps.

### `theme_candidate_influence_maps`

Required columns:

```text
id
candidate_id
influence_order
target_type
target_label
hypothesis_state
evidence_orders_json
source_cluster_keys_json
content_checksum
created_at
```

Every influence-map item is a Scout hypothesis, not a graph node, graph edge,
canonical constraint, Controller, Opportunity, or Decision Packet fact. It must
reference admitted candidate evidence and at least one valid signal cluster.

## Candidate Identity

Candidate keys are deterministic:

```text
candidate:<normalized-slug>
```

Normalization uses Unicode normalization, case folding, punctuation removal,
whitespace collapse, and ASCII slug generation consistent with repository
canonical-key patterns.

Duplicate aliases inside one proposal payload resolve to one candidate only
when the provider explicitly supplies the same canonical identity and the
evidence sets are compatible. Otherwise validation fails.

Scout does not register the candidate in the Industrial Graph canonical Theme
taxonomy.

## Candidate Lifecycle

Allowed states:

```text
DISCOVERED
OBSERVING
VALIDATING
APPROVED
REJECTED
```

Allowed transitions:

```text
DISCOVERED -> OBSERVING | REJECTED
OBSERVING  -> VALIDATING | REJECTED
VALIDATING -> OBSERVING | APPROVED | REJECTED
APPROVED   -> REJECTED
REJECTED   -> OBSERVING
```

Every transition requires:

- an explicit actor;
- an explicit reason;
- an explicit timestamp;
- a new immutable Scout snapshot.

The LLM provider and deterministic builder can create `DISCOVERED` records only.
They cannot create `APPROVED` records. Approval is a separate explicit
repository operation that clones the active snapshot, applies one validated
transition, recomputes checksums, and activates the new revision
transactionally.

## Evidence Admission

An evidence adapter converts eligible persisted rows into immutable
`ScoutSourceEvidence` records.

Admission requires:

- recognized source table;
- recognized source type;
- stable source record ID;
- non-empty source timestamp;
- non-empty source identifier;
- non-empty citation;
- content hash derived from persisted source value;
- no runtime provider or cache read.

Rejected source rows do not silently become evidence. Rejection counts and
reason codes are recorded in snapshot failure detail or build audit output.

Duplicate evidence is identified by:

```text
(source_table, source_record_id, content_hash)
```

Duplicate evidence contributes once to counts and scores.

## Signal Clusters

Signal clusters are not keyword buckets.

A valid cluster requires:

- at least two distinct evidence records;
- at least two distinct source identifiers;
- evidence from at least two source types or two different domain types;
- no duplicate content hashes;
- one explicit cluster label from the frozen proposal payload.

Candidate admission requires at least two independent valid clusters.

Two clusters are independent when:

- neither cluster's evidence set is a subset of the other; and
- shared evidence is less than half of the smaller cluster.

Source spam therefore cannot increase signal, evidence, breadth, confidence, or
serendipity counts.

## Metrics

Persist raw inputs, normalized values, and applied configuration.

All displayed scores are bounded to `0..100`.

### Novelty

Raw novelty is inverse persisted-theme overlap:

```text
1 - maximum weighted token/domain overlap with existing canonical themes
```

The comparison corpus is frozen at the source watermark. The provider cannot
assign novelty directly.

### Velocity

Velocity uses the evidence arrival slope across the configured observation
window. It compares the newest half-window with the oldest half-window and
normalizes by unique evidence count. Duplicate evidence does not contribute.

### Breadth

Breadth is the proportion of represented Scout domains:

```text
represented domain types / 7
```

Source-type diversity is persisted as a raw supporting value.

### Capital

Capital measures admitted capital-related evidence only. It uses persisted
capital expenditure, funding, filing, or investment observations with explicit
source values. Missing capital evidence produces unavailable raw inputs and a
normalized score of zero; it is not treated as favorable.

### Bottleneck Potential

Bottleneck Potential uses explicit admitted Constraint-domain evidence and
multi-cluster recurrence. It cannot be inferred from a company beneficiary,
stock performance, or generated narrative.

### Confidence

Confidence combines:

```text
40% evidence completeness
30% source diversity
20% cluster independence
10% citation completeness
```

All inputs are persisted in raw metrics.

### Serendipity

Serendipity rewards independent cross-domain convergence:

```text
domain diversity * cluster independence * source diversity
```

It is persisted and displayed as a diagnostic metric. It is not part of the
approved Theme Score formula and does not override default ranking.

### Theme Score

Default configured weights:

```text
Novelty              25%
Velocity             20%
Breadth              15%
Capital              15%
Bottleneck Potential 25%
```

```text
Theme Score =
    0.25 * Novelty
  + 0.20 * Velocity
  + 0.15 * Breadth
  + 0.15 * Capital
  + 0.25 * Bottleneck Potential
```

Weights are persisted on each snapshot and candidate.

### Default Ranking

Default ordering is lexicographic:

```text
Bottleneck Potential descending
Confidence descending
Velocity descending
Novelty descending
Breadth descending
Capital descending
candidate_key ascending
```

Theme Score is displayed but does not replace the approved default sort.

## Research Readiness

Readiness is evidence readiness, not graph coverage.

For each required domain:

```text
evidence_strength = min(100, unique_evidence_count / 3 * 100)
source_diversity  = min(100, unique_source_type_count / 2 * 100)
domain_readiness  = 0.60 * evidence_strength + 0.40 * source_diversity
```

Persist readiness for:

- Technology;
- Process;
- Material;
- Equipment;
- Constraint;
- Company.

Overall readiness is the arithmetic mean of the six domain readiness scores.

Research Pipeline handoff is eligible only when:

- lifecycle status is `APPROVED`;
- overall readiness is at least the persisted configured threshold, default
  `60`;
- Technology, Process, Constraint, and Company readiness are non-zero;
- all retained evidence and paths validate.

Eligibility does not perform the handoff and does not create graph records.

## Theme Evolution

Theme Evolution is an ordered candidate-owned path.

Each step contains:

- a short structured label;
- an evidence timestamp;
- one or more candidate evidence orders.

Validation requires chronological ordering and evidence support for every step.
The LLM may propose labels and ordering, but no unsupported history is retained.

## Potential Bottlenecks

Potential bottlenecks are candidate hypotheses. Each path must:

- reference explicit Constraint-domain evidence;
- retain the `potential` truth state;
- avoid canonical graph Constraint identity unless that identity already exists
  in the source evidence;
- never create a Constraint node or resolver relationship.

## Snapshot Build

Build sequence:

1. open one read transaction;
2. select eligible persisted source rows up to a source watermark;
3. canonicalize and checksum the evidence bundle;
4. call the configured proposal provider explicitly;
5. freeze and checksum the structured proposal payload;
6. deterministically admit evidence references;
7. construct candidates, clusters, paths, metrics, and readiness;
8. validate the complete in-memory snapshot;
9. stage immutable rows with status `validated`;
10. activate in `BEGIN IMMEDIATE`;
11. mark the previous Scout snapshot `superseded`;
12. commit.

Provider failure, validation failure, staging failure, or activation failure does
not alter the active Scout snapshot.

Scout activation is independent from Graph, Controller, Opportunity, and
Decision Packet activation.

## Repository API

Add internal repository operations:

```text
stage_theme_scout_snapshot()
activate_theme_scout_snapshot()
rollback_theme_scout_snapshot()
get_active_theme_scout_snapshot()
list_theme_candidates()
get_theme_candidate()
transition_theme_candidate()
export_theme_scout_snapshot()
```

Reads are active-snapshot-only by default and deterministically ordered.

## Public Read API

Add read-only endpoints:

```text
GET /api/theme/scout
GET /api/theme/scout/{candidate_key}
```

The list endpoint returns:

- snapshot metadata;
- ranked candidate summaries;
- explicit empty-state and availability metadata.

The detail endpoint returns:

- candidate metrics;
- lifecycle audit fields;
- evidence;
- signal clusters;
- theme evolution;
- potential bottlenecks;
- influence map;
- readiness;
- handoff eligibility.

No public build, approval, rejection, handoff, graph-write, or LLM endpoint is
added in this phase.

## Frontend Design

### Navigation

Primary order:

```text
Themes
Scout
Supply Chain
Stocks
```

Scout is a distinct target tab and workspace.

### Ranking pane

The default view is a dense table with:

- rank;
- candidate name;
- lifecycle status;
- Bottleneck Potential;
- Confidence;
- Velocity;
- Novelty;
- Breadth;
- Capital;
- Theme Score;
- Evidence Count;
- Source Count;
- Research Readiness.

No invented placeholder values are shown. Missing fields display `Unavailable`
or an em dash with an availability label.

### Detail pane

The detail view contains:

- Overview;
- Signals;
- Evidence;
- Theme Evolution;
- Potential Bottlenecks;
- Research Readiness;
- Research Pipeline Handoff.

It must visibly state:

```text
Candidate intelligence is unverified research.
It is not an Industrial Graph edge or investment recommendation.
```

Verified Controller, Opportunity, and Decision Packet sections are absent until
the candidate is handed through the Research Pipeline in a later phase.

### Empty state

When no active Scout snapshot exists:

- show the approved example candidate labels as examples only;
- show all metrics as unavailable;
- state that no candidate records have been admitted;
- do not fabricate statuses, scores, evidence, or timelines.

## Search Integration

Add a typed `scout` search result kind and target tab.

Rules:

- active Scout candidate exact matches may route to Scout;
- verified Theme exact matches continue to route to Themes;
- known ticker exact matches continue to route to Stocks;
- supply-chain and graph entity behavior remains unchanged;
- example labels without active candidate records are not searchable records.

Candidate search results must display candidate status to avoid confusing them
with verified themes.

## Cache and Rendering

- The backend reads immutable active Scout snapshot rows directly.
- Any cache key includes `scout_version`.
- A newly activated snapshot cannot reuse the prior snapshot's response.
- The frontend request aborts on candidate switch and never renders stale detail.
- Scout state is not derived from Theme Workspace state.
- The page uses content-driven height, dense tables, and compact panes.

## Validation

Reject:

- unknown lifecycle status or invalid transition;
- automatic `APPROVED` creation;
- duplicate candidate identity or rank;
- score outside `0..100`;
- negative counts;
- unknown source table or source type;
- missing source timestamp, identifier, citation, or content hash;
- runtime provider data admitted as persisted evidence;
- duplicate evidence contributing more than once;
- invalid or non-independent clusters;
- unsupported Theme Evolution step;
- unsupported Potential Bottleneck;
- unsupported influence-map item;
- influence-map item presented as verified graph intelligence;
- missing candidate path evidence;
- readiness inconsistent with admitted evidence;
- generated summary treated as evidence;
- graph, Controller, Opportunity, Packet, or Committee writes;
- checksum mismatch;
- non-deterministic ordering.

## Testing

Required backend suites:

- `test_theme_scout_models.py`
- `test_theme_scout_engine.py`
- `test_theme_scout_builder.py`
- `test_theme_scout_validator.py`
- `test_theme_scout_repository.py`
- `test_theme_scout_snapshots.py`
- `test_theme_scout_integration.py`

Frontend tests cover:

- Scout navigation order;
- typed search routing;
- ranking order;
- truthful empty state;
- candidate-versus-graph labels;
- stale detail request cancellation;
- readiness and lifecycle rendering.

Browser validation covers:

- Reusable Rockets;
- Starlink Economy;
- AI Power Grid;
- Nuclear SMR;
- Humanoid Robotics;
- Defense Drones.

Without a valid active snapshot, these remain truthful examples with unavailable
metrics.

## Explicit Non-Goals

- no automatic graph ingestion;
- no automatic evidence creation;
- no automatic approval;
- no stock recommendations;
- no target prices;
- no allocations;
- no quote or market-data reads;
- no Controller, Opportunity, Decision Packet, or Committee changes;
- no Phase 12.12 implementation.

## Known Limitations

- Current persisted source coverage is insufficient for broad production
  discovery.
- Model proposal reproducibility depends on freezing the returned structured
  payload; independent model calls may differ.
- Research readiness measures evidence coverage, not scientific validity.
- Potential bottlenecks remain hypotheses until reviewed and promoted through a
  later Research Pipeline phase.
- This phase does not implement the graph handoff itself.
