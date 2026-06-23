# Phase 12.11G Institutional Research Operating System Final Refinement Design

## Status

Approved design direction. Implementation remains blocked until the executable TDD plan is reviewed and approved.

## Objective

Refine the existing frontend workspaces so MIJI reads as an institutional research operating system rather than a collection of equally weighted data panels.

This phase changes frontend composition, projection, interaction, typography, and styling only. It does not change persisted data, backend contracts, graph construction, lifecycle state, scoring, ranking, or downstream engines.

The four workspace questions remain distinct:

- Rotation: **Where is capital rotating now?**
- Theme: **Should research spend time on this theme?**
- Supply Chain: **How does this industry work, and where is the bottleneck?**
- Scout: **What should research investigate next?**

## Constraints

The implementation must not modify:

- backend code;
- database schema or data;
- graph node, edge, evidence, or snapshot generation;
- Controller, Opportunity, or Decision Packet engines;
- Scout lifecycle, provider, proposal, or activation behavior;
- persisted scoring or ranking formulas;
- Phase 12.12 or Committee behavior.

The frontend must not:

- fabricate data;
- infer graph edges from visual adjacency;
- infer company roles without an admitted persisted role source;
- create synthetic metrics;
- promote unavailable values into favorable states;
- use generated narrative as evidence.

All graph lines displayed in the Supply Chain map must correspond to persisted `industrial_intelligence.graph.edges`. Dependency paths may determine focus and ordering, but may not create additional edges.

## Existing Architecture

Route-level ownership remains unchanged:

- `ThemeResearchPage.tsx` owns Theme and Supply Chain selection and aggregate consumption.
- `ThemeScoutPage.tsx` owns Scout fetching and selected-candidate state.
- `MarketTreemap.tsx` renders the Rotation map from persisted sector values.

Existing independent workspace components remain the implementation boundaries:

- `ThemeInvestmentWorkflow.tsx`
- `IndustrialDependencyWorkflow.tsx`
- `IndustrialDependencyGraph.tsx`
- `ScoutDiscoveryWorkflow.tsx`

Pure projection modules remain responsible for deterministic, testable transformations:

- `rotationWorkspace.ts`
- `industrialGraphProjection.ts`
- `workflowArchitecture.ts`

No shared primary composition will be introduced between Theme and Supply Chain.

## Rotation Design

### Encoding

Rotation retains its existing persisted inputs:

| Visual property | Persisted input |
|---|---|
| Tile area | Absolute capital-flow magnitude |
| State family | Existing deterministic score, momentum, and flow projection |
| Fill intensity | Score normalized within the assigned visual state band |
| Border and glow | Momentum direction and magnitude |

The five state families are:

| State | Score/state range | Fill family |
|---|---|---|
| Strong Leader | Existing `strong-leader` projection | Bright cyan-green |
| Improving | Existing `improving` projection | Teal/blue-green |
| Neutral | Existing `neutral` projection | Dark graphite/slate |
| Weakening | Existing `weakening` projection | Amber/orange |
| Laggard | Existing `laggard` projection | Red/magenta-red |

### Within-Band Intensity

Score intensity will be normalized against the visual state's score band instead of globally against `0..100`.

The normalization contract is:

```text
normalized = clamp((score - band_min) / (band_max - band_min), 0, 1)
```

The state projection itself is not changed. Band normalization only controls shade strength inside the already assigned color family.

Neutral tiles remain dark and muted across their full intensity range. A high-neutral score may become a lighter slate, but never yellow, olive, amber, green, or teal.

### Readability

- State hue communicates direction before the user reads numbers.
- Score strength controls contrast within the state family.
- Momentum controls border and glow without changing the fill family.
- Tile size continues to communicate absolute persisted flow magnitude.
- The existing five-state legend remains visible and is updated to match the final palette.
- When every sector is neutral, relative score and tile area still distinguish stronger and weaker sectors without reclassifying them.

## Theme Decision-Spine Dossier

### Reading Order

The Theme workspace uses this fixed research sequence:

1. 主題論點 / Thesis
2. 為何現在 / Why Now
3. 關鍵瓶頸 / Bottleneck
4. 控制層 / Controller
5. 受益者 / Beneficiary
6. 機會 / Opportunity
7. 驗證 / Validation
8. 決策 / Decision

DOM order and keyboard reading order must follow this sequence.

### Visual Hierarchy

The stages no longer receive equal visual weight.

Primary judgment surfaces:

- Why Now;
- Bottleneck;
- Controller;
- Beneficiary;
- Opportunity.

Compact framing surfaces:

- Thesis becomes a concise identity and thesis strip.
- Validation becomes a status rail with coverage and research gaps.
- Decision becomes a compact Decision Packet and lineage close.

Bottleneck is the strongest visual anchor in the dossier. Controller, Beneficiary, and Opportunity form the decision bridge after the bottleneck. Raw rank, lifecycle, conviction, and research-importance values remain available as compact metadata but do not become hero cards.

### Data Admission

| Stage | Admitted persisted source |
|---|---|
| Thesis | Theme identity, lifecycle, conviction, rank, research importance |
| Why Now | Persisted discovery brief and catalyst records |
| Bottleneck | Canonical industrial constraints |
| Controller | Phase 12.8 controller records |
| Beneficiary | Persisted direct, resolution-enabler, and indirect beneficiary records |
| Opportunity | Phase 12.9 opportunity records |
| Validation | Industrial coverage, research gaps, graph evidence, lineage state |
| Decision | Phase 12.10 packet family and revision fields |

Unavailable values remain explicitly unavailable. The Theme dossier does not render the Supply Chain graph or duplicate its map composition.

## Bottleneck-Centered Supply Chain Map

### Projection Boundary

`projectIndustrialGraph()` will be replaced by a deterministic bottleneck-centered frontend projection.

It will return:

- positioned persisted nodes;
- positioned persisted edges;
- one or more constraint anchors;
- upstream dependency groups;
- right-side company role groups;
- deterministic focus-path metadata;
- bounded viewport dimensions.

The projection does not alter the graph contract and is not persisted.

### Focus Selection

The map selects a primary focus deterministically:

1. Prefer a persisted dependency path containing a `Constraint` node.
2. Prefer the path with the greatest number of referenced evidence IDs.
3. Prefer the path with the greatest persisted depth.
4. Break remaining ties lexically by `path_id` and canonical node keys.

If no dependency path contains a constraint:

1. Prefer a persisted constraint node with the most incident persisted edges.
2. Break ties lexically by canonical key.

If no constraint node exists, the map renders an evidence-backed dependency layout without inventing a bottleneck and labels the anchor as unavailable.

### Spatial Model

The main viewport uses three visual zones:

| Zone | Content |
|---|---|
| Left | Theme, Technology, Process, Material, and Equipment dependencies that reach the selected constraint through persisted edges |
| Center | Selected Constraint or explicit unavailable anchor |
| Right | Companies and other downstream nodes connected by persisted edges, visually grouped by admitted role |

The map is not a seven-column schema diagram. Node type may influence local ordering, but it does not create seven equal lanes.

### Company Role Grouping

Company placement may use only admitted persisted information:

- controller records from `industrial_intelligence.controllers`;
- beneficiary classifications from the persisted aggregate;
- explicit graph relationship types such as supplier, producer, resolver, exposure, dependency, or customer relationships.

Role grouping affects position and labels only. It never creates an edge. When no admitted role exists, the company appears in an `其他關聯公司 / Other linked companies` group.

`COMPANY_EXPOSED_TO_CONSTRAINT` produces an exposed-company display group, not a beneficiary group. Legacy `CONTROLS` edges remain renderable as persisted graph relationships but do not establish the controller display group; that group requires an admitted Phase 12.8 controller record.

### Edge Admission

The displayed edge set is:

```text
projected_edges = persisted graph.edges whose source and target nodes are displayed
```

No edge is created from:

- dependency-path adjacency;
- adjacent visual zones;
- shared node type;
- shared theme;
- company role proximity;
- Controller or Opportunity reasoning-path text.

Every projected edge preserves:

- source canonical key;
- target canonical key;
- relationship type;
- evidence IDs;
- original direction.

### Progressive Disclosure

- The default view emphasizes the deterministic focus path and directly connected bottleneck relationships.
- Non-focus edges remain visible at reduced opacity or are revealed through node selection according to density.
- Edge labels are hidden by default.
- Hover, focus, or selection reveals relationship type and evidence IDs.
- Selecting a node highlights only persisted incident edges.
- The interaction state is frontend-local and does not mutate persisted data.
- The viewport must fit the main map without requiring a giant horizontal scrollbar.

### Secondary Surfaces

Constraints, controllers, dependency paths, coverage, and evidence remain available as compact inspection rails below or beside the map. They support the map and do not compete with it as equal dashboard panels.

## Scout Research-Queue-First Workflow

### Reading Order

Scout retains the persisted lifecycle and uses this research flow:

1. 訊號 / Signals
2. 叢集 / Clusters
3. 瓶頸觀察 / Constraint Watch
4. 研究佇列 / Research Queue
5. 驗證 / Validation
6. 審核 / Approval

### Hierarchy

Research Queue becomes the dominant action surface:

- it receives the greatest width and strongest visual emphasis;
- each task shows its persisted state and evidence references;
- Constraint Watch feeds directly into the queue;
- Validation and Approval follow as compact downstream stages.

The candidate selector remains narrow. Confidence, coverage, readiness, novelty availability, snapshot metadata, and checksums remain compact metadata. They do not precede or visually outweigh the queue.

No Scout signal, hypothesis, or task becomes graph evidence or a downstream record.

## Chinese-First Institutional Typography

Primary workflow headings use Chinese first and English second:

- 主題論點 / Thesis
- 為何現在 / Why Now
- 關鍵瓶頸 / Bottleneck
- 控制層 / Controller
- 受益者 / Beneficiary
- 機會 / Opportunity
- 驗證 / Validation
- 決策 / Decision
- 資金輪動 / Rotation
- 供應鏈地圖 / Supply Chain Map
- 產業依賴圖 / Industrial Dependency Map
- 主題偵察 / Scout
- 研究佇列 / Research Queue
- 證據 / Evidence
- 研究缺口 / Research Gaps
- 決策封包 / Decision Packet

Chinese receives the primary size, weight, and contrast. English appears as smaller secondary context. Snapshot IDs, checksums, scores, and coverage values use compact monospace metadata styling.

The implementation must preserve UTF-8 source text and remove mojibake from modified primary surfaces.

## Workspace Differentiation

Each workspace receives a distinct composition:

- Rotation: dense spatial heatmap and state legend.
- Theme: vertical decision spine with an anchored research judgment sequence.
- Supply Chain: bottleneck-centered network map with progressive inspection.
- Scout: queue-dominant research workflow with a narrow candidate selector.

Theme and Supply Chain must not share their primary composition. Scout must not resemble a score dashboard. Rotation must remain visually legible without opening detail panels.

## Error and Empty-State Behavior

- Existing persisted intelligence must never produce a false empty state.
- Missing Theme-stage data renders a compact unavailable row inside that stage.
- Missing Supply Chain constraints render a truthful no-canonical-bottleneck anchor while preserving available persisted nodes and edges.
- An empty persisted graph renders the existing graph-unavailable message.
- Missing Scout metadata remains unavailable and does not suppress available queue evidence.

## Testing Strategy

Tests are written and observed failing before production changes.

Required contracts:

- Rotation state intensity is normalized inside each visual band.
- Neutral fill remains graphite/slate and excludes yellow or olive.
- The five Rotation states produce distinct fill families and CSS values.
- Theme stages appear in the approved decision-spine order.
- Theme does not import or render the industrial graph.
- Supply Chain projection exposes a constraint-centered anchor and non-column zones.
- Every projected edge maps to a persisted graph edge.
- Dependency-path adjacency alone never creates an edge.
- Scout places Research Queue before score metadata in visual and source hierarchy.
- Chinese labels precede English labels on primary surfaces.
- Rotation, Theme, Supply Chain, and Scout retain distinct root compositions.

## Changed-File Plan

### Modify

- `frontend/src/lib/rotationWorkspace.ts`
- `frontend/src/lib/rotationWorkspace.test.ts`
- `frontend/src/components/terminal/MarketTreemap.tsx`
- `frontend/src/components/theme-workspace/ThemeInvestmentWorkflow.tsx`
- `frontend/src/components/theme-workspace/IndustrialDependencyWorkflow.tsx`
- `frontend/src/components/theme-workspace/IndustrialDependencyGraph.tsx`
- `frontend/src/components/scout-workspace/ScoutDiscoveryWorkflow.tsx`
- `frontend/src/lib/industrialGraphProjection.ts`
- `frontend/src/lib/industrialGraphProjection.test.ts`
- `frontend/src/lib/workflowArchitecture.ts`
- `frontend/src/lib/workflowArchitecture.test.ts`
- `frontend/src/app/globals.css`
- `test_final_acceptance_frontend_contracts.py`

### Create only if component size requires separation

- `frontend/src/components/theme-workspace/IndustrialGraphInspector.tsx`

No backend file is in the changed-file plan.

## Screenshot Plan

Use only `http://localhost:3000` at the same desktop viewport for before and after captures.

Before references:

- `reports/phase1211f-after/rotation.png`
- `reports/phase1211f-after/theme.png`
- `reports/phase1211f-after/supply-chain.png`
- `reports/phase1211f-after/scout.png`

After captures:

- `reports/phase1211g-after/rotation.png`
- `reports/phase1211g-after/theme-hbm.png`
- `reports/phase1211g-after/supply-chain-hbm.png`
- `reports/phase1211g-after/scout.png`

Six-theme validation captures or audit records:

- HBM
- CoWoS
- Glass Substrate
- CPO
- AI Infrastructure
- Data Center Cooling

Each screenshot audit records viewport, selected workspace, selected theme, visible primary stages, false-empty-state status, and browser-console status.

## Acceptance Criteria

### Rotation

- Five state families are visually distinct.
- Neutral is dark graphite/slate and never yellow or olive.
- Strongest and weakest persisted states are recognizable without reading numbers.
- State, score intensity, momentum accent, and flow area remain separate encodings.

### Theme

- The approved eight-stage decision spine is preserved.
- Above the fold contains Theme, Why Now, Bottleneck, Controller, Beneficiary, Opportunity, and Validation status at the target desktop viewport.
- Bottleneck and evidence-backed decision stages dominate metadata.
- The primary Supply Chain graph is absent.

### Supply Chain

- A persisted Constraint anchors the main view when available.
- Upstream dependencies appear left and linked companies appear right.
- The map does not render seven equal primary columns.
- The main experience does not require a giant horizontal scrollbar.
- Edge labels and evidence use progressive disclosure.
- Every displayed line maps to a persisted graph edge.

### Scout

- Research Queue is the dominant surface.
- Candidate ranking remains a compact selector.
- Signals, Clusters, Constraint Watch, Queue, Validation, and Approval define the workflow.
- Scores and gauges do not dominate.

### Cross-Workspace

- Chinese is primary and English is secondary.
- The four workspaces are visually distinguishable without relying on their page titles.
- No backend, schema, graph generation, lifecycle, scoring, ranking, provider, Phase 12.12, or Committee changes occur.
- Frontend tests, TypeScript, production build, backend regression pytest, and browser validation pass before completion is claimed.
