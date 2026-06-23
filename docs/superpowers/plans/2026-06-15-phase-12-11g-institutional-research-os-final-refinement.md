# Phase 12.11G Institutional Research Operating System Final Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine Rotation, Theme, Supply Chain, and Scout into visually distinct institutional research workspaces while preserving all existing persisted data and backend behavior.

**Architecture:** Route-level data ownership remains unchanged. Pure frontend projection functions provide deterministic state-band color intensity and a bottleneck-centered industrial map; independent workspace components apply distinct visual hierarchies. Supply Chain lines remain a strict projection of persisted `graph.edges`.

**Tech Stack:** Next.js 14, React 18, TypeScript, CSS, SVG, Python pytest source-contract tests, in-app browser.

---

## File Structure

### Rotation

- Modify `frontend/src/lib/rotationWorkspace.ts`: state-band intensity projection.
- Modify `frontend/src/lib/rotationWorkspace.test.ts`: pure Rotation contracts.
- Modify `frontend/src/components/terminal/MarketTreemap.tsx`: expose visual-state attributes and variables.
- Modify `frontend/src/app/globals.css`: final state palette and legend.

### Theme

- Modify `frontend/src/components/theme-workspace/ThemeInvestmentWorkflow.tsx`: decision-spine hierarchy.
- Modify `frontend/src/lib/workflowArchitecture.ts`: approved Chinese-first stage labels.
- Modify `frontend/src/lib/workflowArchitecture.test.ts`: stage-order and language contracts.
- Modify `frontend/src/app/globals.css`: dossier composition.

### Supply Chain

- Modify `frontend/src/lib/industrialGraphProjection.ts`: bottleneck-centered deterministic projection.
- Modify `frontend/src/lib/industrialGraphProjection.test.ts`: projection and non-inference contracts.
- Modify `frontend/src/components/theme-workspace/IndustrialDependencyGraph.tsx`: interactive progressive-disclosure SVG.
- Modify `frontend/src/components/theme-workspace/IndustrialDependencyWorkflow.tsx`: map-first composition and compact inspector.
- Optionally create `frontend/src/components/theme-workspace/IndustrialGraphInspector.tsx` only if the existing workflow component becomes difficult to understand.
- Modify `frontend/src/app/globals.css`: centered map and role-zone styling.

### Scout

- Modify `frontend/src/components/scout-workspace/ScoutDiscoveryWorkflow.tsx`: queue-first composition.
- Modify `frontend/src/app/globals.css`: queue-dominant visual hierarchy.

### Acceptance Contracts

- Modify `test_final_acceptance_frontend_contracts.py`: frontend-only structural regressions.

No backend source file may be modified.

## Task 1: Lock the Phase 12.11G Frontend Contracts

**Files:**
- Modify: `test_final_acceptance_frontend_contracts.py`
- Modify: `frontend/src/lib/workflowArchitecture.test.ts`

- [ ] **Step 1: Add failing Rotation contrast assertions**

Add source-contract assertions requiring:

```python
assert "normalizeRotationBandIntensity" in rotation_source
assert 'fillFamily: "graphite"' in rotation_source
assert "yellow" not in neutral_palette_source.lower()
assert "olive" not in neutral_palette_source.lower()
```

The test must inspect only the neutral palette block rather than banning approved Weakening amber styling.

- [ ] **Step 2: Add failing Theme decision-spine assertions**

Require the ordered stages:

```python
expected = (
    "thesis",
    "why-now",
    "bottleneck",
    "controller",
    "beneficiary",
    "opportunity",
    "validation",
    "decision",
)
```

Also require a `theme-decision-spine` root and reject `IndustrialDependencyGraph` inside `ThemeInvestmentWorkflow.tsx`.

- [ ] **Step 3: Add failing Supply Chain structure assertions**

Require:

```python
assert "constraintAnchor" in projection
assert "upstreamNodes" in projection
assert "companyGroups" in projection
assert "selectedNodeKey" in graph_component
assert "SUPPLY_WORKFLOW_STAGES.map" not in graph_component
assert "industrial-graph-layer-labels" not in graph_component
```

Require the test fixture to prove that a dependency-path-only adjacency does not enter `projection.edges`.

- [ ] **Step 4: Add failing Scout hierarchy assertions**

Require a queue-dominant class and confirm that the Research Queue section appears before the compact metrics section in component source:

```python
assert source.index('data-workflow-stage="research-queue"') < source.index('className="scout-metadata-strip"')
```

- [ ] **Step 5: Add failing Chinese-first and differentiation assertions**

Require the approved UTF-8 Chinese labels before their English equivalents and distinct root classes for all four workspaces.

- [ ] **Step 6: Run focused tests and verify RED**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_final_acceptance_frontend_contracts.py -q
cd frontend
npx tsc --noEmit
```

Expected: Phase 12.11G assertions fail because band normalization, bottleneck-centered fields, queue-first metadata order, and final root classes do not yet exist.

## Task 2: Normalize Rotation Intensity Within State Bands

**Files:**
- Modify: `frontend/src/lib/rotationWorkspace.test.ts`
- Modify: `frontend/src/lib/rotationWorkspace.ts`

- [ ] **Step 1: Add pure failing tests**

Add tests for:

```ts
normalizeRotationBandIntensity("neutral", 50) === 0.5
normalizeRotationBandIntensity("neutral", 40) === 0
normalizeRotationBandIntensity("neutral", 60) === 1
normalizeRotationBandIntensity("strong-leader", 90) > normalizeRotationBandIntensity("strong-leader", 82)
```

Add a five-state fixture and assert that `fillFamily`, `fill`, `border`, and `glow` are not identical across adjacent states.

- [ ] **Step 2: Run TypeScript and verify RED**

Run:

```powershell
cd frontend
npx tsc --noEmit
```

Expected: missing `normalizeRotationBandIntensity`.

- [ ] **Step 3: Implement the minimal band normalizer**

Define explicit frontend-only visual bands:

```ts
const ROTATION_VISUAL_BANDS = {
  "strong-leader": [80, 100],
  improving: [60, 80],
  neutral: [40, 60],
  weakening: [30, 50],
  laggard: [0, 30],
  unavailable: [0, 1],
} as const;
```

Implement:

```ts
export function normalizeRotationBandIntensity(
  state: InstitutionalRotationState,
  scoreValue: number | null | undefined,
): number {
  const score = finite(scoreValue);
  if (score === null || state === "unavailable") return 0;
  const [minimum, maximum] = ROTATION_VISUAL_BANDS[state];
  return clamp01((score - minimum) / Math.max(1, maximum - minimum));
}
```

These bands control shade only and must not replace `projectRotationState()`.

- [ ] **Step 4: Use normalized intensity in `projectRotationVisual()`**

Replace global `score / 100` intensity with:

```ts
const intensity = normalizeRotationBandIntensity(state, score);
```

Keep the neutral palette within dark graphite values. Do not introduce yellow or olive into the neutral palette.

- [ ] **Step 5: Run focused checks and verify GREEN**

Run:

```powershell
cd frontend
npx tsc --noEmit
```

Expected: Rotation projection tests compile and all pure contract booleans remain true.

## Task 3: Refine Rotation Rendering and Legend

**Files:**
- Modify: `frontend/src/components/terminal/MarketTreemap.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] **Step 1: Add failing rendering assertions**

Require each tile to expose:

```tsx
data-rotation-state={visual.state}
data-fill-family={visual.fillFamily}
data-momentum-accent={visual.momentumAccent}
```

Require the legend to expose all five `data-state` values.

- [ ] **Step 2: Run focused pytest and verify RED**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_final_acceptance_frontend_contracts.py -q
```

- [ ] **Step 3: Render the projected state directly**

In `MarketTreemap.tsx`, use `visual.state` instead of recomputing state multiple times. Preserve existing persisted labels, flow, score, and momentum values.

- [ ] **Step 4: Apply decisive but truthful CSS**

Set:

- Strong Leader: cyan-green fill with bright positive edge.
- Improving: darker teal with a distinct hue.
- Neutral: dark slate with muted gray border.
- Weakening: amber/orange.
- Laggard: magenta-red.

Do not use a single-tone red palette. Keep selected and focus outlines visually separate from momentum accents.

- [ ] **Step 5: Verify GREEN**

Run focused pytest and `npx tsc --noEmit`.

## Task 4: Build the Theme Decision-Spine Hierarchy

**Files:**
- Modify: `frontend/src/lib/workflowArchitecture.ts`
- Modify: `frontend/src/lib/workflowArchitecture.test.ts`
- Modify: `frontend/src/components/theme-workspace/ThemeInvestmentWorkflow.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Add failing UTF-8 label tests**

Require:

```ts
THEME_WORKFLOW_STAGES.map(({ zh }) => zh).join(",")
  === "主題論點,為何現在,關鍵瓶頸,控制層,受益者,機會,驗證,決策"
```

- [ ] **Step 2: Add failing hierarchy tests**

Require:

- `theme-decision-spine`;
- compact Thesis metadata;
- primary `bottleneck` anchor;
- a `theme-decision-bridge` containing Controller, Beneficiary, and Opportunity;
- compact Validation and Decision close.

- [ ] **Step 3: Run focused checks and verify RED**

Run TypeScript and focused pytest.

- [ ] **Step 4: Replace mojibake labels with approved Chinese**

Update only Phase 12.11G primary surfaces. Preserve English as secondary labels through `BilingualLabel`.

- [ ] **Step 5: Recompose without changing admitted data**

Keep the same aggregate sources, but group the DOM into:

```tsx
<section className="theme-decision-spine">
  <ThemeThesisStrip />
  <WhyNowStage />
  <BottleneckAnchor />
  <div className="theme-decision-bridge">
    <ControllerStage />
    <BeneficiaryStage />
    <OpportunityStage />
  </div>
  <ValidationStage />
  <DecisionStage />
</section>
```

Local helper components may remain in the same file unless extraction materially improves readability.

- [ ] **Step 6: Apply hierarchy CSS**

Use:

- a compact Thesis strip;
- a larger Bottleneck anchor;
- a three-part decision bridge;
- compact Validation and Decision rails;
- content-driven height;
- no fixed-height empty cards.

- [ ] **Step 7: Verify Theme contracts**

Run focused pytest and TypeScript. Confirm `IndustrialDependencyGraph` is absent from the Theme component.

## Task 5: Define the Bottleneck-Centered Projection Contract

**Files:**
- Modify: `frontend/src/lib/industrialGraphProjection.test.ts`
- Modify: `frontend/src/lib/industrialGraphProjection.ts`

- [ ] **Step 1: Replace column-layout fixture expectations**

Build a fixture containing:

- Theme → Technology;
- Technology → Process;
- Process → Constraint;
- Company → Constraint resolver edge;
- one dependency path containing all four non-company nodes;
- one extra dependency-path adjacency with no persisted edge.

- [ ] **Step 2: Add failing focus-selection tests**

Assert:

```ts
projection.constraintAnchor?.node.canonical_key === "constraint:capacity"
projection.upstreamNodes.every((node) => node.x < projection.constraintAnchor!.x)
projection.companyGroups.flatMap((group) => group.nodes).every(
  (node) => node.x > projection.constraintAnchor!.x,
)
```

- [ ] **Step 3: Add failing strict-edge tests**

Assert:

```ts
projection.edges.length === graph.edges.length
projection.edges.every((edge) =>
  graph.edges.some((persisted) =>
    persisted.source_key === edge.sourceKey
    && persisted.target_key === edge.targetKey
    && persisted.relationship_type === edge.relationshipType
  )
)
```

Assert that the path-only adjacency is absent.

- [ ] **Step 4: Add deterministic tie-break tests**

Provide two constraint-bearing paths with equal evidence counts and depth. Verify lexical `path_id` selection.

- [ ] **Step 5: Run TypeScript and verify RED**

Expected: old projection lacks `constraintAnchor`, `upstreamNodes`, `companyGroups`, and `focusPathId`.

## Task 6: Implement the Bottleneck-Centered Projection

**Files:**
- Modify: `frontend/src/lib/industrialGraphProjection.ts`

- [ ] **Step 1: Define focused projection types**

Add:

```ts
export interface IndustrialCompanyGroup {
  role: "controller" | "resolver" | "supplier" | "beneficiary" | "customer" | "exposed" | "other";
  labelZh: string;
  labelEn: string;
  nodes: ProjectedIndustrialNode[];
}

export interface IndustrialGraphProjection {
  nodes: ProjectedIndustrialNode[];
  upstreamNodes: ProjectedIndustrialNode[];
  constraintAnchor: ProjectedIndustrialNode | null;
  companyGroups: IndustrialCompanyGroup[];
  edges: ProjectedIndustrialEdge[];
  focusPathId: string | null;
  width: number;
  height: number;
}
```

- [ ] **Step 2: Implement deterministic focus-path selection**

Sort candidate paths by:

1. contains Constraint;
2. descending unique evidence count;
3. descending depth;
4. lexical `path_id`;
5. lexical canonical-key chain.

- [ ] **Step 3: Position the constraint anchor**

Place the selected constraint near the horizontal center. If no constraint exists, set `constraintAnchor` to `null` and preserve available nodes.

- [ ] **Step 4: Position upstream dependencies**

Use persisted directed reachability toward the anchor to assign upstream depth. Order nodes by depth, node type, then canonical key. Fit them into bounded left-side bands rather than seven equal columns.

- [ ] **Step 5: Position companies and downstream nodes**

Accept a display-only role context alongside the graph:

```ts
export interface IndustrialGraphRoleContext {
  controllerCompanyKeys: ReadonlySet<string>;
  beneficiaryCompanyKeys: ReadonlySet<string>;
  resolutionEnablerCompanyKeys: ReadonlySet<string>;
}
```

Group companies from this persisted role context and explicit graph relationship families. The initial relationship mapping is display-only:

```ts
EQUIPMENT_PRODUCED_BY -> supplier
MATERIAL_SUPPLIED_BY -> supplier
CONSTRAINT_RESOLVED_BY_COMPANY -> resolver
PROCESS_RESOLVED_BY_COMPANY -> resolver
COMPANY_EXPOSED_TO_CONSTRAINT -> exposed
CUSTOMER_OF -> customer
```

Use `controllerCompanyKeys` to establish the controller group, `resolutionEnablerCompanyKeys` to establish resolver/enabler placement, and `beneficiaryCompanyKeys` to establish beneficiary placement. Legacy `CONTROLS` may retain its persisted edge rendering but must not establish controller grouping.

Any unmatched company enters `other`.

- [ ] **Step 6: Project only persisted edges**

Build `edges` exclusively from `graph.edges`. Preserve source, target, direction, relationship type, and evidence IDs.

- [ ] **Step 7: Run projection tests and verify GREEN**

Run `npx tsc --noEmit`.

## Task 7: Render the Progressive-Disclosure Industrial Map

**Files:**
- Modify: `frontend/src/components/theme-workspace/IndustrialDependencyGraph.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Add failing interaction source contracts**

Require local selected-node and selected-edge state:

```tsx
const [selectedNodeKey, setSelectedNodeKey] = useState<string | null>(null);
const [selectedEdgeKey, setSelectedEdgeKey] = useState<string | null>(null);
```

Require edge details to render only for hovered, focused, or selected relationships.

- [ ] **Step 2: Run focused pytest and verify RED**

- [ ] **Step 3: Replace permanent labels**

Remove permanent `<text>` labels for every edge. Keep `<title>` for accessible fallback and render a compact relationship inspector for selected edges.

- [ ] **Step 4: Render three visual zones**

Render:

- upstream dependency field;
- central constraint anchor;
- right-side company role clusters.

Use one bounded responsive canvas. Do not render `SUPPLY_WORKFLOW_STAGES.map()` or seven layer headers.

- [ ] **Step 5: Add node and edge selection**

Selecting a node highlights persisted incident edges. Selecting an edge shows:

- relationship type;
- source and target names;
- evidence IDs.

Do not create derived lines.

- [ ] **Step 6: Apply density controls**

Default:

- focus-path and anchor edges at full opacity;
- secondary persisted edges at reduced opacity;
- compact nodes;
- no horizontal page scrollbar.

- [ ] **Step 7: Verify GREEN**

Run focused pytest and TypeScript.

## Task 8: Recompose the Supply Chain Workspace

**Files:**
- Modify: `frontend/src/components/theme-workspace/IndustrialDependencyWorkflow.tsx`
- Optionally create: `frontend/src/components/theme-workspace/IndustrialGraphInspector.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Add failing composition assertions**

Require:

- `industrial-bottleneck-workspace`;
- map before inspection rails;
- no seven-column layer summary;
- no Theme dossier stages;
- compact constraints, controllers, paths, and coverage inspector.

- [ ] **Step 2: Run focused pytest and verify RED**

- [ ] **Step 3: Pass admitted role context to the map**

Extend the graph component props only with already persisted aggregate values needed for display grouping:

```tsx
<IndustrialDependencyGraph
  graph={industrial.graph}
  controllers={industrial.controllers}
  beneficiaries={aggregate.beneficiaries}
/>
```

Convert these persisted records into canonical-key sets and pass them to `projectIndustrialGraph(graph, roleContext)`. Role context may position existing nodes but may not add nodes or edges.

- [ ] **Step 4: Make the map primary**

Render the bottleneck-centered map immediately after a compact summary strip. Move constraints, controllers, path highlights, and coverage into a compact inspector.

- [ ] **Step 5: Preserve truthful empty states**

If `view.hasGraph` is true, never show the legacy false-empty message. If constraints are absent, show `尚無已驗證瓶頸 / Verified bottleneck unavailable` inside the map while retaining available graph content.

- [ ] **Step 6: Verify Supply Chain contracts**

Run focused pytest and TypeScript.

## Task 9: Make Scout Research Queue the Primary Surface

**Files:**
- Modify: `frontend/src/components/scout-workspace/ScoutDiscoveryWorkflow.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] **Step 1: Add failing queue-first assertions**

Require:

- Research Queue appears before compact score metadata in DOM order.
- Candidate selector remains narrow.
- Signals and Clusters feed Constraint Watch.
- Constraint Watch and Research Queue occupy the primary content region.
- Validation and Approval appear after Queue.

- [ ] **Step 2: Run focused pytest and verify RED**

- [ ] **Step 3: Reorder component DOM**

Use:

```tsx
<CandidateSelector />
<CandidateContext />
<SignalsAndClusters />
<ConstraintWatch />
<ResearchQueue />
<Validation />
<Approval />
<CompactMetadata />
```

The metadata strip includes confidence, coverage, readiness, novelty availability, provider, and checksums.

- [ ] **Step 4: Apply queue-dominant CSS**

Give Research Queue the largest primary grid area and strongest border/title hierarchy. Keep signal evidence accessible without making it larger than the queue.

- [ ] **Step 5: Preserve Scout isolation copy**

Retain the explicit statement that Scout candidates are not verified graph evidence and create no downstream records.

- [ ] **Step 6: Verify GREEN**

Run focused pytest and TypeScript.

## Task 10: Chinese-First and Workspace-Differentiation Audit

**Files:**
- Modify: `frontend/src/lib/workflowArchitecture.ts`
- Modify: `frontend/src/components/theme-workspace/ThemeInvestmentWorkflow.tsx`
- Modify: `frontend/src/components/theme-workspace/IndustrialDependencyWorkflow.tsx`
- Modify: `frontend/src/components/theme-workspace/IndustrialDependencyGraph.tsx`
- Modify: `frontend/src/components/scout-workspace/ScoutDiscoveryWorkflow.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] **Step 1: Scan modified primary surfaces for mojibake**

Run:

```powershell
rg -n "銝|憿|閬|撽|蝝|頛|靘|璈" frontend/src/components/theme-workspace frontend/src/components/scout-workspace frontend/src/lib/workflowArchitecture.ts
```

Inspect every match. Replace corrupted primary labels with approved UTF-8 Chinese; retain legitimate Chinese text.

- [ ] **Step 2: Add root identity assertions**

Require:

```text
rotation-workspace
theme-decision-spine
industrial-bottleneck-workspace
scout-research-queue-workspace
```

Each root must use a distinct primary layout model in CSS.

- [ ] **Step 3: Apply typography hierarchy**

Primary Chinese headings use stronger size and contrast. English labels use smaller secondary styling. Metadata remains compact monospace.

- [ ] **Step 4: Verify no cross-workspace composition duplication**

Confirm:

- Theme has no industrial graph import.
- Supply Chain has no Theme decision stages.
- Scout has no Rotation treemap or Theme dossier.
- Rotation has no research queue or graph composition.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run focused pytest and TypeScript.

## Task 11: Full Automated Verification

**Files:**
- No production changes unless verification exposes a proven regression.

- [ ] **Step 1: Run frontend contract tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_final_acceptance_frontend_contracts.py -q
```

Expected: all frontend source contracts pass.

- [ ] **Step 2: Run frontend TypeScript tests**

```powershell
cd frontend
npx tsc --noEmit
```

Expected: exit code `0`.

- [ ] **Step 3: Run frontend production build**

```powershell
cd frontend
npm run build
```

Expected: Next.js production build exits `0`.

- [ ] **Step 4: Run backend regression suite**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest
```

Expected: no backend regressions. This phase makes no backend changes.

- [ ] **Step 5: Inspect the final diff**

Run:

```powershell
git diff -- frontend/src/lib/rotationWorkspace.ts frontend/src/lib/rotationWorkspace.test.ts frontend/src/components/terminal/MarketTreemap.tsx frontend/src/components/theme-workspace frontend/src/components/scout-workspace frontend/src/lib/industrialGraphProjection.ts frontend/src/lib/industrialGraphProjection.test.ts frontend/src/lib/workflowArchitecture.ts frontend/src/lib/workflowArchitecture.test.ts frontend/src/app/globals.css test_final_acceptance_frontend_contracts.py
```

Confirm no backend file is part of the Phase 12.11G implementation diff.

## Task 12: Browser Acceptance and Screenshot Proof

**Files:**
- Create: `reports/phase1211g-after/rotation.png`
- Create: `reports/phase1211g-after/theme-hbm.png`
- Create: `reports/phase1211g-after/supply-chain-hbm.png`
- Create: `reports/phase1211g-after/scout.png`
- Create: `reports/phase1211g-after/browser-audit.json`

- [ ] **Step 1: Confirm canonical origin**

Open only:

```text
http://localhost:3000
```

Do not validate on ports `3001`, `3002`, or origin `127.0.0.1:3000`.

- [ ] **Step 2: Validate Rotation**

Confirm:

- state legend contains five visually distinct states;
- neutral tiles are dark and muted;
- strongest and weakest persisted sectors are visually distinguishable;
- tile area, fill, intensity, and momentum accents remain separate.

Capture `rotation.png`.

- [ ] **Step 3: Validate Theme for six themes**

For HBM, CoWoS, Glass Substrate, CPO, AI Infrastructure, and Data Center Cooling, record:

- eight stages in approved order;
- Bottleneck visual prominence;
- Controller, Beneficiary, Opportunity, and Validation visibility;
- no Supply Chain graph;
- no false unavailable block when persisted data exists;
- browser console errors.

Capture `theme-hbm.png` as the representative screenshot.

- [ ] **Step 4: Validate Supply Chain for six themes**

For each theme, record:

- graph node count;
- graph edge count;
- selected constraint anchor or truthful unavailable state;
- upstream and right-side node presence;
- no seven equal columns;
- no giant horizontal page scrollbar;
- every inspected line exposes a persisted relationship and evidence IDs;
- browser console errors.

Capture `supply-chain-hbm.png`.

- [ ] **Step 5: Validate Scout**

Confirm:

- Research Queue is the dominant surface;
- candidate selector is compact;
- Signals → Clusters → Constraint Watch → Queue → Validation → Approval is clear;
- metrics are metadata;
- novelty remains unavailable when unsupported;
- isolation statement is visible;
- no browser console errors.

Capture `scout.png`.

- [ ] **Step 6: Save browser audit**

Write `browser-audit.json` with:

```json
{
  "origin": "http://localhost:3000",
  "viewport": { "width": 1280, "height": 720 },
  "workspaces": {
    "rotation": {},
    "theme": {},
    "supply_chain": {},
    "scout": {}
  },
  "themes": {}
}
```

Populate the objects only with observed browser results. Do not fabricate unavailable measurements.

- [ ] **Step 7: Compare before and after**

Use Phase 12.11F screenshots as the baseline and report:

- Rotation contrast improvement;
- Theme above-fold stage visibility;
- Supply Chain scrollbar and edge-label reduction;
- Scout queue-area prominence;
- Chinese-first label hierarchy.

## Task 13: Final Acceptance Report

**Files:**
- No additional file required unless the user requests a persistent report.

- [ ] **Step 1: Re-read the approved specification**

Check every requirement against implementation, automated verification, and browser evidence.

- [ ] **Step 2: Report changed files**

List only files actually changed by Phase 12.11G.

- [ ] **Step 3: Report required audits**

Include:

- Rotation contrast report;
- Theme dossier report;
- Supply Chain map report;
- Scout workflow report;
- Chinese-first audit;
- AI-dashboard-removal audit;
- workspace-differentiation audit;
- automated test results;
- six-theme browser validation;
- screenshot paths;
- known limitations.

- [ ] **Step 4: Assign acceptance status**

Use `PASS` only when all blocking acceptance criteria and fresh verification commands pass. Otherwise report the actual failing status and evidence; do not claim completion.
