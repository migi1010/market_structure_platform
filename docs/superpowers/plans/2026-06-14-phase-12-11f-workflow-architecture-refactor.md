# Phase 12.11F Workflow Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build independent Theme, Supply Chain, and Scout research workflows and repair the Rotation treemap's five-state visual encoding without changing persisted business logic.

**Architecture:** Route-level components retain existing fetch and selection ownership. Three new workflow components consume existing contracts independently, while a dedicated SVG graph component renders only persisted industrial nodes and edges. Pure projection functions isolate deterministic workflow and color behavior for TDD.

**Tech Stack:** Next.js 14, React 18, TypeScript, CSS, SVG, Python pytest contract tests, in-app browser.

---

### Task 1: Workflow Architecture Contract Tests

**Files:**
- Modify: `test_final_acceptance_frontend_contracts.py`
- Create: `frontend/src/lib/workflowArchitecture.test.ts`
- Create: `frontend/src/lib/workflowArchitecture.ts`

- [ ] **Step 1: Add failing source-contract tests**

Assert that the four approved component files exist, Theme and Supply Chain import different workflow components, and Theme no longer imports the shared `ThemeIndustrialWorkspace`.

- [ ] **Step 2: Add failing projection tests**

Define expected ordered stage IDs:

```ts
THEME_WORKFLOW_STAGES === [
  "thesis", "why-now", "bottleneck", "controller",
  "beneficiary", "opportunity", "validation", "decision",
]

SUPPLY_WORKFLOW_STAGES === [
  "Theme", "Technology", "Process", "Material",
  "Equipment", "Constraint", "Company",
]

SCOUT_WORKFLOW_STAGES === [
  "signals", "clusters", "constraint-watch",
  "research-queue", "validation", "approval",
]
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_final_acceptance_frontend_contracts.py -q
cd frontend
npx tsc --noEmit
```

Expected: failures for missing workflow files and exports.

- [ ] **Step 4: Implement stage constants only**

Create `workflowArchitecture.ts` with readonly stage constants and Chinese-first labels. Do not create UI components in this step.

- [ ] **Step 5: Run tests and verify GREEN**

Run the same focused commands. Expected: projection tests pass; component source tests remain failing until Tasks 3-5.

### Task 2: Rotation Heatmap P0 Projection

**Files:**
- Modify: `frontend/src/lib/rotationWorkspace.test.ts`
- Modify: `frontend/src/lib/rotationWorkspace.ts`
- Modify: `frontend/src/components/terminal/MarketTreemap.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Add failing palette projection tests**

Add a `projectRotationVisual` contract returning:

```ts
{
  state: "neutral",
  fillFamily: "graphite",
  intensity: 0.42,
  momentumAccent: "positive",
}
```

Test all five states, verify neutral never returns yellow/olive, and verify Strong Leader differs from Improving while Laggard differs from Weakening.

- [ ] **Step 2: Add failing momentum tests**

Verify equal score/state inputs with positive and negative momentum return different `momentumAccent` and glow strength.

- [ ] **Step 3: Run TypeScript and verify RED**

Run `npx tsc --noEmit`.

Expected: missing `projectRotationVisual`.

- [ ] **Step 4: Implement deterministic projection**

Use the existing state projection. Clamp score intensity within the assigned state range and return CSS custom-property values for fill shade, border, and glow. Do not change score or state formulas.

- [ ] **Step 5: Render CSS variables**

Set `--rotation-fill`, `--rotation-border`, and `--rotation-glow` on each tile. Replace yellow/olive neutral styling with dark graphite/slate. Keep the explicit five-state legend.

- [ ] **Step 6: Verify GREEN**

Run `npx tsc --noEmit` and focused acceptance pytest.

### Task 3: Theme Investment Workflow

**Files:**
- Create: `frontend/src/components/theme-workspace/ThemeInvestmentWorkflow.tsx`
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] **Step 1: Add failing Theme workflow source tests**

Require eight ordered `data-workflow-stage` values and reject `IndustrialDependencyGraph`, node columns, and `IndustrialSupplyChainWorkspace` inside the Theme component.

- [ ] **Step 2: Run focused pytest and verify RED**

Expected: missing component and stage markers.

- [ ] **Step 3: Implement Thesis and Why Now**

Render one thesis strip from identity, lifecycle, conviction, rank, and time window. Render Why Now from persisted catalysts, discovery brief fields, and available evidence references. Missing sections render `不可用 / Unavailable`.

- [ ] **Step 4: Implement Bottleneck through Opportunity**

Render canonical constraints, persisted resolution data, controllers, direct beneficiaries, resolution enablers, indirect beneficiaries, and opportunity rows in workflow order. Do not render graph nodes or edges.

- [ ] **Step 5: Implement Validation and Decision**

Render coverage, research gaps, packet summary, and lineage as compact final stages.

- [ ] **Step 6: Switch Theme route composition**

Replace the current `ThemeIndustrialWorkspace` command rendering with:

```tsx
<ThemeInvestmentWorkflow
  aggregate={selectedAggregate}
  rank={institutionalRank}
  totalThemes={phase10ThemeRows.length}
  conviction={selectedScore?.conviction_level ?? null}
/>
```

- [ ] **Step 7: Verify GREEN**

Run focused pytest and `npx tsc --noEmit`.

### Task 4: Persisted SVG Industrial Dependency Graph

**Files:**
- Create: `frontend/src/components/theme-workspace/IndustrialDependencyGraph.tsx`
- Create: `frontend/src/lib/industrialGraphProjection.test.ts`
- Create: `frontend/src/lib/industrialGraphProjection.ts`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Add failing graph projection tests**

Use a fixture containing Theme, Technology, Process, Constraint, and Company nodes. Assert:

- deterministic x/y positions by node type and canonical key;
- one projected edge for each persisted graph edge;
- no projected edge for visual adjacency;
- persisted relationship label and evidence IDs are preserved.

- [ ] **Step 2: Run TypeScript and verify RED**

Expected: missing graph projection module.

- [ ] **Step 3: Implement pure graph projection**

Create `projectIndustrialGraph(graph)` returning positioned nodes, SVG edges, dimensions, and layer metadata. Build the edge set exclusively from `graph.edges`; dependency paths may admit otherwise missing referenced nodes but may not create edges.

- [ ] **Step 4: Implement SVG renderer**

Render `<svg>` paths with arrow markers and labels behind absolutely positioned compact nodes. Relationship-family styling:

- dependency: cyan;
- bottleneck/limit: amber;
- control: violet;
- resolution: green.

Unknown persisted relationship types use a neutral gray style and retain their exact label.

- [ ] **Step 5: Verify GREEN**

Run `npx tsc --noEmit`.

### Task 5: Industrial Dependency Workflow

**Files:**
- Create: `frontend/src/components/theme-workspace/IndustrialDependencyWorkflow.tsx`
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/components/theme-workspace/ThemeIndustrialWorkspace.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] **Step 1: Add failing Supply Chain workflow tests**

Require the SVG graph as primary content and secondary rails for constraints, controllers, evidence, dependency highlights, and coverage. Reject Theme Investment stages, Opportunity tables, and Decision Packet sections.

- [ ] **Step 2: Run focused pytest and verify RED**

- [ ] **Step 3: Implement workflow**

Compose:

```tsx
<IndustrialDependencyGraph graph={industrial.graph} />
<DependencyInspectionRails
  constraints={industrial.constraints}
  controllers={industrial.controllers}
  coverage={industrial.coverage}
  evidenceCount={industrial.graph.evidence_count}
  paths={industrial.graph.dependency_paths}
/>
```

- [ ] **Step 4: Switch Supply Chain route composition**

The `supply-chain` branch in `ThemeResearchPage.tsx` renders only `IndustrialDependencyWorkflow` when aggregate industrial intelligence exists.

- [ ] **Step 5: Retire shared workflow control**

Remove Theme/Supply workflow orchestration from `ThemeIndustrialWorkspace.tsx`. Keep or relocate only low-level shared rows that are still used.

- [ ] **Step 6: Verify GREEN**

Run focused pytest and TypeScript.

### Task 6: Scout Discovery Workflow

**Files:**
- Create: `frontend/src/components/scout-workspace/ScoutDiscoveryWorkflow.tsx`
- Modify: `frontend/src/components/ThemeScoutPage.tsx`
- Modify: `frontend/src/lib/themeScout.test.ts`
- Modify: `frontend/src/lib/themeScout.ts`
- Modify: `frontend/src/app/globals.css`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] **Step 1: Add failing Scout workflow tests**

Assert Signals and Clusters precede Constraint Watch and Research Queue. Require Validation and Approval stages. Reject gauges, radar, candidate-health panels, and a full-width score table.

- [ ] **Step 2: Run tests and verify RED**

- [ ] **Step 3: Add signal projection**

Extend the existing visual model with persisted signal records derived from admitted `signal_clusters` and their evidence IDs. Do not calculate signal quality.

- [ ] **Step 4: Implement discovery workflow**

Render provenance, narrow candidate selector, signals/clusters, constraint watch, research queue, validation evidence, and lifecycle approval pipeline.

- [ ] **Step 5: Simplify ThemeScoutPage**

Keep fetch, abort, error handling, candidate sorting, and selected key state. Delegate selected candidate rendering to `ScoutDiscoveryWorkflow`.

- [ ] **Step 6: Verify GREEN**

Run focused TypeScript and pytest.

### Task 7: Workspace Differentiation and Chinese-First Audit

**Files:**
- Modify: `frontend/src/app/globals.css`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] **Step 1: Add failing differentiation tests**

Require unique root classes:

- `theme-investment-workflow`;
- `industrial-dependency-workflow`;
- `scout-discovery-workflow`.

Require that no pair shares the same ordered primary stage IDs.

- [ ] **Step 2: Add failing Chinese-first tests**

Assert the approved Chinese labels appear before their English equivalents in component source.

- [ ] **Step 3: Implement visual identities**

- Theme: dossier rail and numbered research stages.
- Supply Chain: full-width graph canvas and inspection rails.
- Scout: queue/pipeline workspace with provenance header.

- [ ] **Step 4: Verify GREEN**

Run focused pytest and TypeScript.

### Task 8: Full Verification and Browser Acceptance

**Files:**
- Create: `reports/phase1211f-after/rotation.png`
- Create: `reports/phase1211f-after/theme.png`
- Create: `reports/phase1211f-after/supply-chain.png`
- Create: `reports/phase1211f-after/scout.png`

- [ ] **Step 1: Run frontend contract tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_final_acceptance_frontend_contracts.py -q
cd frontend
npx tsc --noEmit
```

- [ ] **Step 2: Run production build**

```powershell
cd frontend
npm run build
```

- [ ] **Step 3: Run backend regression**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest
```

- [ ] **Step 4: Restart the single frontend dev server**

Run one Next.js server on `localhost:3000` after the production build has completed.

- [ ] **Step 5: Validate Rotation**

Confirm five visible legend states, dark muted neutral tiles, distinct leader/improver and weakening/laggard fills, and momentum-specific borders.

- [ ] **Step 6: Validate six themes**

For HBM, CoWoS, Glass Substrate, CPO, AI Infrastructure, and Data Center Cooling:

- Theme shows the eight-stage Investment Workflow and no dependency graph.
- Supply Chain shows the SVG dependency graph and no Theme dossier duplication.
- persisted intelligence does not produce a false unavailable state.

- [ ] **Step 7: Validate Scout**

Confirm signals-first ordering, compact selector, visible Research Queue, lifecycle approval pipeline, and no gauges/radar.

- [ ] **Step 8: Capture screenshots and density metrics**

Capture before/after screenshots at `http://localhost:3000`, record viewport occupancy and primary-stage visibility, and check browser console errors.

