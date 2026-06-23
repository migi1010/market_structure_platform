# Phase 10.15 Theme Research Operating System Design

## Purpose

Phase 10.15 integrates existing persisted Phase 10 and Phase 12 intelligence into the Theme Workspace.

It does not create:

- new discovery;
- new scoring;
- new graph edges;
- generated narratives;
- investment recommendations;
- Phase 11 Committee behavior;
- Phase 12.11 behavior.

The Theme Workspace becomes a visual operating system for:

```text
Theme
  -> Industrial Dependency Graph
    -> Constraints
      -> Controllers
        -> Hidden Opportunities
          -> Decision Packets
```

The Industrial Graph remains the source of truth. SQLite remains persistence. NetworkX remains bounded traversal and projection preparation only.

## Product Outcome

The command workspace provides a compact integrated overview:

- Theme Summary;
- Industrial Graph summary;
- Constraint Intelligence;
- Controller Intelligence;
- Hidden Opportunity Intelligence;
- Decision Packet Intelligence;
- Coverage Audit;
- verified Research Gaps.

The existing Supply Chain tab becomes the expanded Industrial Dependency Graph investigation surface.

The UI must not display a generic unavailable state when the active Phase 12 lineage contains relevant evidence. When evidence is genuinely absent, the workspace displays a compact verified research gap.

## Existing Boundaries

### Phase 10 Aggregate

`ThemeIntelligenceAggregateService` currently returns:

- score and discovery records;
- lifecycle;
- catalysts;
- persisted Phase 10 bottlenecks;
- Phase 10 beneficiary classifications;
- portfolio context;
- a legacy entity-role supply-chain summary;
- Phase 10 theme-overlap relationships.

It does not query the Industrial Graph repository.

### Phase 12 Persistence

The Industrial Graph repository already exposes:

- one active graph snapshot;
- active graph edges and evidence;
- active controller snapshot and metrics;
- active opportunity snapshot and metrics;
- active Decision Packet family and packets;
- deterministic reasoning paths;
- bounded relationship-filtered graph traversal.

These systems remain unchanged. Phase 10.15 adds a read-only theme projection.

## Canonical Theme Identity

Backend identity resolution is authoritative.

Canonical identities required by this phase:

| Input | Canonical key | Display name |
|---|---|---|
| `HBM` | `hbm` | HBM |
| `CoWoS` | `cowos` | CoWoS |
| `Glass Substrate` | `glass_substrate` | Glass Substrate |
| `CPO`, `CPO Photonics`, `Co-Packaged Optics` | `cpo_photonics` | CPO Photonics |
| `AI Infrastructure` | `ai_infrastructure` | AI Infrastructure |
| `Data Center Cooling` | `data_center_cooling` | Data Center Cooling |

Resolution order:

1. normalize the request;
2. match exact canonical Theme key;
3. match exact normalized display name;
4. match exact normalized alias;
5. apply the approved deterministic alias registry;
6. return the normalized request only when no canonical graph Theme is matched.

The aggregate response always reports the resolved canonical key and graph display name when the graph contains the Theme.

Frontend aliases remain navigation conveniences and never override the returned backend identity.

## Industrial Intelligence Aggregate Extension

The existing aggregate contract gains one additive top-level field:

```text
industrial_intelligence
```

Existing fields and Phase 10 public routes remain compatible.

### Canonical Identity

```text
requested_theme_id
canonical_theme_key
display_name
aliases
resolution_state
```

`resolution_state` is one of:

- `canonical`;
- `alias`;
- `unresolved`.

### Active Lineage

```text
graph_snapshot_id
graph_build_version
controller_snapshot_id
controller_version
opportunity_snapshot_id
opportunity_version
packet_family_version
packet_family_revision
lineage_state
```

`lineage_state` is:

- `complete` when all active references align;
- `graph_only` when no downstream active lineage exists;
- `partial` when the lineage exists only through an intermediate layer;
- `unavailable` when no active graph exists.

The projection rejects mixed lineage. It never combines metrics or packets from snapshots that do not reference the selected active graph chain.

### Graph Projection

The graph projection contains:

- theme root node;
- admitted nodes;
- admitted edges;
- edge evidence counts;
- total distinct evidence count;
- deterministic dependency paths;
- snapshot metadata;
- per-node-type counts.

Node types displayed:

- Theme;
- Technology;
- Process;
- Material;
- Equipment;
- Constraint;
- Company;
- Industry when it is an admitted supply-chain role layer.

Nodes are included only when they are endpoints of active admitted edges for the active graph snapshot. Global reusable nodes from `get_nodes()` are never included merely because they exist.

## Theme-Scoped Path Admission

Naive reachability is forbidden because reusable Company, Constraint, Process, Material, Equipment, and Industry nodes can connect multiple themes.

The projection builds paths from the canonical Theme root using these rules:

1. active graph snapshot only;
2. active edges only;
3. directional traversal from the Theme root;
4. maximum path depth of seven edges;
5. no repeated node in a path;
6. stop traversal when another Theme node is reached;
7. do not continue beyond terminal Company nodes;
8. use only approved industrial dependency relationships;
9. deduplicate paths by ordered node and relationship sequence;
10. sort by path length, then canonical node and relationship sequence.

Approved path relationships are existing evidence-backed relationships that connect:

```text
Theme -> Industry role
Theme -> Technology
Theme -> Material
Theme -> Equipment
Theme -> Constraint
Technology -> Process
Process -> Process
Process -> Material
Process -> Equipment
Process -> Constraint
Material -> Company
Material -> Constraint
Equipment -> Company
Equipment -> Constraint
Constraint -> Company
Industry role -> Company
Company -> Company
```

No inverse edge is persisted or invented. Existing analytical reverse projections used internally by the Controller Engine are not exposed as graph facts.

The API may return a path only when every edge is present in the active snapshot and carries evidence.

## Constraint Projection

Constraint rows originate from admitted graph paths.

Each row contains:

- canonical key;
- display name;
- constraint category from structured metadata when available;
- evidence count;
- resolver Company keys;
- exposed Company keys;
- resolution state;
- optional severity;
- optional Phase 10 source match.

Resolution state:

- `resolved_evidence` when an explicit active resolver edge exists;
- `unresolved` when the constraint is admitted without explicit resolver evidence;
- `unknown` when resolution cannot be classified.

Severity is populated only when a persisted Phase 10 bottleneck is deterministically matched by canonical normalized identity or an approved exact mapping. Otherwise severity is `null`.

## Controller Projection

Controllers originate only from the active Phase 12.8 controller snapshot.

A controller is admitted when at least one retained controller reasoning path contains the canonical Theme root and every path edge belongs to the active graph snapshot.

Each row contains:

- canonical Company key;
- company name;
- global rank;
- controller score;
- controller types;
- coverage;
- coverage confidence;
- evidence count;
- retained theme-connected reasoning paths.

Legacy Phase 10 beneficiary controller labels are not used.

## Opportunity Projection

Opportunities originate only from the active Phase 12.9 opportunity snapshot.

An opportunity is admitted when at least one retained opportunity reasoning path contains the canonical Theme root and validates against the active graph snapshot.

Each row contains:

- canonical Company key;
- company name;
- global rank;
- opportunity score;
- opportunity types;
- coverage component;
- coverage confidence;
- controller contribution;
- constraint contribution;
- evidence count;
- market-component availability states;
- retained theme-connected reasoning paths.

No opportunity is inferred from graph reachability alone.

## Decision Packet Projection

Packets originate only from the active Phase 12.10 packet family whose lineage exactly matches the selected active graph, controller, and opportunity snapshots.

The projection includes:

- packet family version and revision;
- family packet, path, evidence, and risk counts;
- matching Theme packet;
- matching Company and Opportunity packets for admitted opportunities and controllers;
- packet coverage and evidence coverage;
- packet-owned path, evidence, and risk counts.

A packet is admitted only when:

- its Theme subject key equals the canonical Theme key; or
- one of its copied packet paths contains the canonical Theme root and its Company corresponds to an admitted controller or opportunity.

Packet payload remains structured. The frontend does not render generated narrative because the packet schema forbids it.

## Coverage Audit

Coverage is calculated separately for:

- Technology;
- Process;
- Material;
- Equipment;
- Constraint;
- Company;
- Evidence;
- Overall.

For each node type:

```text
denominator = all bounded theme-scoped reachable nodes of that type through active allowed edges
numerator   = those reachable nodes attached to at least one evidenced allowed edge
coverage    = numerator / denominator * 100
```

The bounded candidate traversal used for the denominator applies the same direction, depth, terminal, relationship, and cross-Theme rules as path admission. Evidence is not required to count a candidate reachable node. Visible dependency paths remain stricter and require evidence on every edge.

When the denominator is zero:

- numerator is zero;
- coverage is `null`;
- availability state is `not_applicable`.

Evidence coverage:

```text
denominator = all bounded theme-scoped active allowed edges
numerator   = those edges carrying at least one evidence record
```

Overall coverage is the weighted-free arithmetic mean of available node-type coverage percentages and evidence coverage. `not_applicable` components are excluded. No target denominator is invented.

## Verified Research Gaps

Research gaps replace repeated generic unavailable cards.

Gap codes:

- `NO_GRAPH_PATH`;
- `NO_TECHNOLOGY_EVIDENCE`;
- `NO_PROCESS_EVIDENCE`;
- `NO_MATERIAL_EVIDENCE`;
- `NO_EQUIPMENT_EVIDENCE`;
- `NO_CONSTRAINT_EVIDENCE`;
- `NO_COMPANY_EVIDENCE`;
- `NO_CONTROLLER_EVIDENCE`;
- `NO_OPPORTUNITY_EVIDENCE`;
- `NO_DECISION_PACKET_EVIDENCE`;
- `INCOMPLETE_LINEAGE`;
- `UNMATCHED_CONSTRAINT_SEVERITY`.

Each gap contains:

- code;
- layer;
- state;
- observed count;
- a deterministic label.

The labels are fixed UI copy, not generated analysis.

AI Infrastructure is expected to show graph and constraint evidence while reporting:

- `NO_CONTROLLER_EVIDENCE`;
- `NO_OPPORTUNITY_EVIDENCE`;
- `NO_DECISION_PACKET_EVIDENCE`.

## Backend Components

Create `theme_industrial_projection.py` with:

- `CanonicalThemeResolver`;
- `ThemeIndustrialProjectionService`;
- typed projection helpers;
- path admission and validation;
- coverage calculation;
- research-gap derivation.

`ThemeIntelligenceAggregateService` delegates all Phase 12 reading to this service and adds its result under `industrial_intelligence`.

The projection service is read-only and does not activate snapshots, write graph records, alter scores, or mutate packet data.

## Frontend Contract

Add strict interfaces for:

- canonical identity;
- active lineage;
- graph nodes and edges;
- graph paths;
- constraints;
- controllers;
- opportunities;
- packet family and packets;
- coverage components;
- research gaps.

`normalizeThemeAggregateResponse()` preserves and validates the additive field. Missing or malformed sections become explicit empty structures with `unavailable` states; they do not receive fabricated defaults.

## Frontend Components

Create focused components under:

```text
frontend/src/components/theme-industrial/
```

Components:

- `ThemeIndustrialOverview`;
- `IndustrialDependencyGraph`;
- `ConstraintIntelligencePanel`;
- `ControllerIntelligencePanel`;
- `OpportunityIntelligencePanel`;
- `DecisionPacketPanel`;
- `ThemeCoverageAudit`;
- `ThemeResearchGaps`;
- shared compact path and evidence primitives.

`ThemeResearchPage.tsx` selects data and composes these components. It does not calculate Phase 12 scores, infer paths, classify constraints, or derive gaps.

## Command Workspace Layout

The command workspace uses content-driven height:

1. compact Theme Summary, no more than approximately 20% of initial viewport;
2. Industrial Graph summary and mini dependency graph;
3. paired dense Constraint and Controller tables;
4. paired Opportunity and Decision Packet tables;
5. compact Coverage Audit;
6. Research Gaps only when gaps exist.

No giant empty placeholder is retained.

## Expanded Dependency Graph Layout

The Supply Chain tab is relabeled Industrial Dependency Graph.

It displays:

- lineage and graph snapshot;
- node and relationship counts;
- evidence count;
- relationship-filtered mini graph;
- deterministic dependency paths;
- node-type filters;
- constraint and company terminal endpoints;
- compact path evidence.

When a layer has no evidence, the graph omits that layer and the Research Gaps strip states the missing layer. It never renders a visual bridge across the gap.

## Interaction Rules

- single click opens ContextDock;
- double click drills into an existing destination;
- hover previews only;
- hover performs no aggregate fetch;
- aggregate fetching remains centralized and abortable;
- graph entity clicks use canonical keys;
- selected theme remains persistent.

## Error And Empty-State Policy

- no active graph: show compact graph-unavailable status and lineage gap;
- no downstream controller/opportunity/packet data: preserve graph and show verified gaps;
- malformed lineage: omit mismatched downstream records and show incomplete-lineage gap;
- missing severity: render `Not established`, not zero;
- missing score: render `Not established`, not zero;
- no admitted paths: render a compact gap row, not a fixed-height blank graph.

## Testing

Backend tests cover:

- canonical identity and CPO aliases;
- active-snapshot-only behavior;
- path boundaries and cross-theme prevention;
- evidence-backed path admission;
- controller filtering;
- opportunity filtering;
- packet filtering and lineage;
- coverage denominator and numerator semantics;
- verified gap derivation;
- aggregate contract compatibility;
- deterministic ordering.

Frontend tests cover:

- strict aggregate normalization;
- CPO canonical identity preservation;
- rendering available sections;
- compact research gaps;
- no legacy controller substitution;
- no fabricated path or score fallback;
- graph panel content-driven empty state;
- no duplicate aggregate request ownership.

Browser validation covers:

- HBM;
- CoWoS;
- Glass Substrate;
- CPO;
- AI Infrastructure;
- Data Center Cooling.

## Acceptance Criteria

- all six themes resolve to canonical backend identities;
- Phase 12 graph data appears in the command workspace;
- Industrial Dependency Graph paths appear when evidenced;
- Phase 12.8 controllers appear only when theme-connected;
- Phase 12.9 opportunities appear only when theme-connected;
- Phase 12.10 packet lineage and counts appear when matching;
- AI Infrastructure renders graph and constraints plus truthful downstream gaps;
- no generic unavailable block replaces existing evidence;
- no fabricated severity, score, relationship, path, or narrative;
- no unrelated-theme path leakage;
- no duplicate aggregate requests;
- no hydration errors;
- no mojibake;
- backend pytest, TypeScript, and production build pass.

## Non-Goals

- Phase 11 Investment Committee;
- Phase 12.11;
- LLM Theme Scout;
- research ingestion;
- graph editing;
- new public route family;
- new graph analytics or centrality;
- new persisted scoring;
- recommendations, targets, signals, or portfolio changes.
