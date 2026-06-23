# Phase 10.15 Theme Research Operating System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the existing active Industrial Graph, Controller, Opportunity, and Decision Packet lineage inside the Theme Workspace without inventing data or changing Phase 12 engines.

**Architecture:** Add a read-only backend-owned `industrial_intelligence` projection to the existing theme aggregate. The projection resolves canonical Theme identity, admits bounded evidence-backed paths from one active snapshot lineage, filters controller/opportunity/packet records by retained theme-connected reasoning paths, and calculates deterministic observed coverage and gaps. The frontend strictly normalizes and renders this projection through focused dense terminal components.

**Tech Stack:** Python 3.12, FastAPI service layer, SQLite, NetworkX read projection, pytest, React 18, Next.js 14, TypeScript, CSS.

---

## Approved Invariants

- Existing aggregate fields remain compatible.
- Backend owns canonical identity and all Phase 12 projection logic.
- Only one aligned active Graph -> Controller -> Opportunity -> Packet lineage is read.
- Global nodes and metrics are never rendered without theme-path admission.
- Traversal is directional, bounded, relationship-filtered, deterministic, and stops at another Theme.
- Every returned dependency path consists only of active evidenced edges.
- Severity is nullable unless deterministically matched to persisted Phase 10 evidence.
- Legacy Phase 10 beneficiary controller labels do not populate Phase 12 controller panels.
- Research gaps are deterministic statuses, not generated explanations.
- Frontend does not score, infer, bridge, or classify industrial intelligence.

## Changed File Plan

Create:

- `backend/theme_intelligence/industrial_graph/theme_industrial_projection.py`
- `test_theme_industrial_projection.py`
- `test_theme_industrial_identity.py`
- `test_theme_industrial_aggregate.py`
- `frontend/src/components/theme-industrial/ThemeIndustrialOverview.tsx`
- `frontend/src/components/theme-industrial/IndustrialDependencyGraph.tsx`
- `frontend/src/components/theme-industrial/ConstraintIntelligencePanel.tsx`
- `frontend/src/components/theme-industrial/ControllerIntelligencePanel.tsx`
- `frontend/src/components/theme-industrial/OpportunityIntelligencePanel.tsx`
- `frontend/src/components/theme-industrial/DecisionPacketPanel.tsx`
- `frontend/src/components/theme-industrial/ThemeCoverageAudit.tsx`
- `frontend/src/components/theme-industrial/ThemeResearchGaps.tsx`
- `frontend/src/components/theme-industrial/IndustrialPathList.tsx`
- `frontend/src/components/theme-industrial/index.ts`
- `frontend/src/lib/themeIndustrialIntelligence.test.ts`

Modify:

- `backend/theme_intelligence/aggregate.py`
- `backend/theme_intelligence/industrial_graph/__init__.py`
- `frontend/src/types/stock.ts`
- `frontend/src/services/stockApi.ts`
- `frontend/src/components/ThemeResearchPage.tsx`
- `frontend/src/app/globals.css`
- `test_theme_intelligence_aggregate_api.py`
- `test_final_acceptance_frontend_contracts.py`

Do not modify:

- graph/controller/opportunity/packet builders, formulas, validators, activation, or persistence;
- Phase 10 overlap graph APIs;
- quote, portfolio, cache, or provider pipelines;
- frontend aggregate request ownership;
- public route paths;
- Investment Committee or Phase 12.11 code.

---

### Task 1: Lock Canonical Theme Identity

**Files:**
- Create: `test_theme_industrial_identity.py`
- Create: `backend/theme_intelligence/industrial_graph/theme_industrial_projection.py`

- [ ] **Step 1: Write failing identity tests**

Test exact inputs:

```python
@pytest.mark.parametrize(
    ("value", "canonical_key", "display_name"),
    [
        ("HBM", "hbm", "HBM"),
        ("CoWoS", "cowos", "CoWoS"),
        ("Glass Substrate", "glass_substrate", "Glass Substrate"),
        ("CPO", "cpo_photonics", "CPO Photonics"),
        ("CPO Photonics", "cpo_photonics", "CPO Photonics"),
        ("Co-Packaged Optics", "cpo_photonics", "CPO Photonics"),
        ("AI Infrastructure", "ai_infrastructure", "AI Infrastructure"),
        ("Data Center Cooling", "data_center_cooling", "Data Center Cooling"),
    ],
)
def test_resolver_returns_graph_canonical_theme(
    active_graph_repository, value, canonical_key, display_name
) -> None:
    identity = CanonicalThemeResolver(active_graph_repository).resolve(value)
    assert identity.canonical_theme_key == canonical_key
    assert identity.display_name == display_name
```

Also assert unknown input returns `resolution_state == "unresolved"` and does not alias by substring.

- [ ] **Step 2: Run the tests and verify import failure**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_industrial_identity.py -q
```

Expected: failure because the projection module does not exist.

- [ ] **Step 3: Implement immutable identity records and resolver**

Implement:

```python
@dataclass(frozen=True)
class CanonicalThemeIdentity:
    requested_theme_id: str
    canonical_theme_key: str
    display_name: str
    aliases: tuple[str, ...]
    resolution_state: str
```

Use exact normalized key, display-name, and alias matching against active graph Theme nodes plus the approved deterministic alias map:

```python
APPROVED_THEME_ALIASES = {
    "cpo": "cpo_photonics",
    "co_packaged_optics": "cpo_photonics",
    "cpo_photonics": "cpo_photonics",
}
```

- [ ] **Step 4: Run identity tests**

Expected: all identity tests pass.

---

### Task 2: Define The Industrial Intelligence Contract

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_industrial_projection.py`
- Create: `test_theme_industrial_projection.py`

- [ ] **Step 1: Write failing projection-shape tests**

Assert the service returns:

```python
{
    "identity": {...},
    "lineage": {...},
    "graph": {
        "nodes": [],
        "edges": [],
        "evidence_count": 0,
        "dependency_paths": [],
        "counts_by_type": {},
    },
    "constraints": [],
    "controllers": [],
    "opportunities": [],
    "decision_packets": {...},
    "coverage": {...},
    "research_gaps": [],
}
```

Assert ordering is stable across two calls.

- [ ] **Step 2: Run the tests and verify missing service failure**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest test_theme_industrial_projection.py -q
```

- [ ] **Step 3: Implement typed internal projection records**

Add focused dataclasses or typed serializer helpers for:

- lineage;
- projected node;
- projected edge;
- projected path;
- constraint;
- controller;
- opportunity;
- packet summary;
- coverage component;
- research gap.

Every serializer must return JSON-safe ordered structures and nullable values rather than numeric fallback zeros.

- [ ] **Step 4: Implement empty and unavailable states**

No active graph returns:

```python
{
    "lineage": {"lineage_state": "unavailable", ...},
    "graph": {"nodes": [], "edges": [], ...},
    "research_gaps": [
        {"code": "NO_GRAPH_PATH", "layer": "graph", "state": "missing", ...}
    ],
}
```

- [ ] **Step 5: Run projection-shape tests**

Expected: pass.

---

### Task 3: Implement Bounded Theme Graph Projection

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_industrial_projection.py`
- Modify: `test_theme_industrial_projection.py`

- [ ] **Step 1: Write failing path-boundary tests**

Fixtures must include:

- one root Theme;
- one Technology -> Process -> Material -> Company route;
- one Process -> Equipment -> Company route;
- one Constraint route;
- a shared Company connected to a second Theme;
- an edge without evidence;
- a cycle.

Assert:

```python
assert all(path["nodes"][0]["canonical_key"] == "hbm" for path in result["graph"]["dependency_paths"])
assert not any(node["canonical_key"] == "unrelated_theme" for node in result["graph"]["nodes"])
assert not any(edge["relationship_type"] == "UNSUPPORTED_TEST_EDGE" for edge in result["graph"]["edges"])
assert not any(path["path_id"] == "path-with-missing-evidence" for path in result["graph"]["dependency_paths"])
assert max(path["depth"] for path in result["graph"]["dependency_paths"]) <= 7
```

- [ ] **Step 2: Run and verify failures**

- [ ] **Step 3: Implement admitted relationship registry**

Use an explicit frozen set containing only the existing dependency relationships approved by the specification. Do not include Phase 10 overlap relationships or legacy `CONTROLS`.

- [ ] **Step 4: Implement deterministic path traversal**

Use the active graph export and:

- traverse outgoing edges;
- stop at another Theme;
- stop at Company;
- reject repeated nodes;
- reject edges without evidence;
- cap at seven edges;
- sort paths deterministically.

- [ ] **Step 5: Derive projected nodes and edges from retained paths**

Never call `get_nodes()` and expose its global result. Resolve only endpoint IDs present in retained active edges.

- [ ] **Step 6: Run path tests**

Expected: pass with no cross-theme leakage.

---

### Task 4: Project Constraints Truthfully

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_industrial_projection.py`
- Modify: `test_theme_industrial_projection.py`

- [ ] **Step 1: Write failing constraint tests**

Assert:

- canonical Constraint nodes appear from retained paths;
- evidence counts are distinct;
- explicit resolver edges produce `resolved_evidence`;
- absence of resolver produces `unresolved`;
- Company exposure does not imply resolution;
- unmatched Phase 10 bottleneck leaves severity `None`;
- exact canonical Phase 10 match admits persisted severity and source metadata.

- [ ] **Step 2: Run and verify failures**

- [ ] **Step 3: Implement constraint projection**

Resolve:

```text
Constraint node
-> evidence from admitted incident edges
-> explicit resolver endpoints
-> explicit exposed-company endpoints
-> optional exact persisted bottleneck match
```

- [ ] **Step 4: Run constraint tests**

Expected: pass.

---

### Task 5: Filter Controllers And Opportunities By Theme Paths

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_industrial_projection.py`
- Modify: `test_theme_industrial_projection.py`

- [ ] **Step 1: Write failing metric-filter tests**

Create global controller and opportunity records where:

- one reasoning path contains the root Theme;
- one belongs only to another Theme;
- one has an invalid graph edge;
- one contains a valid root path plus an unrelated path.

Assert only the valid root-connected records and valid retained paths appear.

- [ ] **Step 2: Run and verify failures**

- [ ] **Step 3: Implement lineage selection**

Select active snapshots and verify:

```text
controller.graph_snapshot_id == graph.id
opportunity.controller_snapshot_id == controller.id
opportunity.graph_snapshot_id == graph.id
```

Mismatches set `lineage_state = partial` and exclude mismatched downstream records.

- [ ] **Step 4: Implement reasoning-path validation**

A retained reasoning path must:

- contain `("Theme", canonical_theme_key)`;
- use nodes and directional edge pairs present in the active graph;
- remain bounded;
- stop before another Theme.

- [ ] **Step 5: Serialize controller and opportunity records**

Preserve persisted scores, types, contributions, coverage, evidence IDs, ranks, availability states, and filtered paths.

- [ ] **Step 6: Run metric-filter tests**

Expected: pass.

---

### Task 6: Filter Decision Packets And Preserve Lineage

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_industrial_projection.py`
- Modify: `test_theme_industrial_projection.py`

- [ ] **Step 1: Write failing packet tests**

Assert:

- only the active matching family is used;
- the canonical Theme packet is included;
- Company and Opportunity packets are included only for admitted companies;
- copied packet paths must contain the root Theme;
- family and packet counts come from persisted records;
- mismatched lineage yields a verified gap and no packet projection.

- [ ] **Step 2: Run and verify failures**

- [ ] **Step 3: Implement packet-family filtering**

Verify all family snapshot IDs against selected lineage before admitting packets.

- [ ] **Step 4: Serialize family and matching packet summaries**

Return structured counts and coverage only. Do not expose or create narrative fields.

- [ ] **Step 5: Run packet tests**

Expected: pass.

---

### Task 7: Calculate Coverage And Verified Research Gaps

**Files:**
- Modify: `backend/theme_intelligence/industrial_graph/theme_industrial_projection.py`
- Modify: `test_theme_industrial_projection.py`

- [ ] **Step 1: Write failing coverage tests**

For each node type assert:

```python
assert component["denominator"] == reachable_count
assert component["numerator"] == evidenced_reachable_count
assert component["coverage"] == pytest.approx(numerator / denominator * 100)
```

Assert zero denominators return `coverage is None` and `availability_state == "not_applicable"`.

Assert overall coverage excludes not-applicable components.

Build the denominator from the bounded theme-scoped active allowed-edge candidate traversal before evidence filtering. Build visible dependency paths only from the evidenced subset.

- [ ] **Step 2: Write failing research-gap tests**

Include the AI Infrastructure fixture state:

```python
codes = {gap["code"] for gap in result["research_gaps"]}
assert "NO_CONTROLLER_EVIDENCE" in codes
assert "NO_OPPORTUNITY_EVIDENCE" in codes
assert "NO_DECISION_PACKET_EVIDENCE" in codes
assert "NO_GRAPH_PATH" not in codes
```

- [ ] **Step 3: Run and verify failures**

- [ ] **Step 4: Implement coverage**

Calculate denominators from bounded candidate nodes and edges and numerators from the evidenced subset. Do not substitute configured target counts.

- [ ] **Step 5: Implement deterministic gaps**

Use fixed codes and fixed labels. Sort by graph-layer order.

- [ ] **Step 6: Run coverage and gap tests**

Expected: pass.

---

### Task 8: Extend The Existing Aggregate Additively

**Files:**
- Modify: `backend/theme_intelligence/aggregate.py`
- Modify: `backend/theme_intelligence/industrial_graph/__init__.py`
- Create: `test_theme_industrial_aggregate.py`
- Modify: `test_theme_intelligence_aggregate_api.py`

- [ ] **Step 1: Write failing aggregate contract tests**

Assert `/api/theme/intelligence/cpo` returns:

```python
assert payload["theme_id"] == "cpo_photonics"
assert payload["name"] == "CPO Photonics"
assert payload["industrial_intelligence"]["identity"]["canonical_theme_key"] == "cpo_photonics"
```

For all six themes assert the additive field exists and legacy aggregate keys remain unchanged.

- [ ] **Step 2: Run and verify failures**

- [ ] **Step 3: Resolve canonical identity before Phase 10 queries**

Use backend resolution to choose `canonical_name` and `canonical_theme_key`. Preserve existing Phase 10 matching behavior for non-graph themes.

- [ ] **Step 4: Delegate Phase 12 projection**

Add:

```python
"industrial_intelligence": self.industrial_projection.get_theme(canonical_theme_key)
```

Do not add a new route.

- [ ] **Step 5: Populate legacy dependency paths from the graph projection**

Map only validated graph paths into the existing `supply_chain.dependency_paths` compatibility field. Do not synthesize `strength`; use persisted edge dependency strength or `None`.

- [ ] **Step 6: Run aggregate tests**

Expected: pass.

---

### Task 9: Extend Strict Frontend Types And Normalization

**Files:**
- Modify: `frontend/src/types/stock.ts`
- Modify: `frontend/src/services/stockApi.ts`
- Create: `frontend/src/lib/themeIndustrialIntelligence.test.ts`

- [ ] **Step 1: Write failing normalization tests**

Test:

- complete HBM payload survives normalization;
- CPO remains `cpo_photonics`;
- null severity remains null;
- missing controller records remain empty;
- malformed paths are dropped;
- missing industrial field becomes an explicit unavailable projection;
- unknown numeric values do not become zero.

- [ ] **Step 2: Run the frontend test command configured by the repository**

Use the package script discovered in `frontend/package.json`; if no script exists, run the existing Vitest command directly.

- [ ] **Step 3: Add strict TypeScript interfaces**

Define all projection sections without `any`, `unknown as any`, or non-null assertions.

- [ ] **Step 4: Implement normalizers**

Use existing `isRecord`, `validNumber`, and string-array helpers. Preserve backend gap and availability states.

- [ ] **Step 5: Run normalization tests and TypeScript**

```powershell
cd frontend
npx tsc --noEmit
```

Expected: pass.

---

### Task 10: Build Focused Industrial Intelligence Components

**Files:**
- Create all files under `frontend/src/components/theme-industrial/`
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/lib/themeIndustrialIntelligence.test.ts`

- [ ] **Step 1: Add failing component contract tests**

Assert:

- graph counts render from payload;
- constraint severity renders `Not established` when null;
- controllers and opportunities render persisted values;
- packet lineage renders exact snapshot IDs;
- gaps render compact rows;
- no component contains generated fallback prose;
- empty tables use content-driven compact states.

- [ ] **Step 2: Run and verify failures**

- [ ] **Step 3: Implement shared path rendering**

`IndustrialPathList` renders ordered node labels and relationship labels exactly as returned.

- [ ] **Step 4: Implement command summary components**

Build:

- compact graph overview;
- constraint table;
- controller table;
- opportunity table;
- packet lineage;
- coverage strip;
- research-gap strip.

- [ ] **Step 5: Implement CSS**

Use terminal variables and:

- content-driven height;
- dense tables;
- no fixed-height empty state;
- compact bilingual headings;
- persistent selected state;
- responsive single-column fallback under the existing breakpoint.

- [ ] **Step 6: Run component tests and TypeScript**

Expected: pass.

---

### Task 11: Integrate The Command Workspace

**Files:**
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `test_final_acceptance_frontend_contracts.py`

- [ ] **Step 1: Write failing source/behavior contracts**

Assert:

- `ThemeResearchPage` imports focused industrial components;
- opportunity and packet evidence are no longer hard-coded to zero;
- Phase 12 controller display does not use `aggregateControllerLabels`;
- the aggregate fetch remains owned outside `ThemeResearchPage`;
- hover handlers do not fetch.

- [ ] **Step 2: Run and verify failures**

- [ ] **Step 3: Replace sparse command sections**

Keep the compact Phase 10 summary and compose `ThemeIndustrialOverview` below it. Remove repeated giant unavailable sections when the industrial projection supplies evidence.

- [ ] **Step 4: Retain Phase 10 evidence without duplication**

Catalysts, lifecycle, crowding, and persisted Phase 10 bottleneck severity remain visible once. Do not repeat the same record in multiple cards.

- [ ] **Step 5: Run focused tests and TypeScript**

Expected: pass.

---

### Task 12: Replace Supply Chain With Industrial Dependency Graph

**Files:**
- Modify: `frontend/src/components/ThemeResearchPage.tsx`
- Modify: `frontend/src/components/theme-industrial/IndustrialDependencyGraph.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Write failing expanded-graph tests**

Assert:

- title is `Industrial Dependency Graph`;
- graph paths come from `industrial_intelligence.graph.dependency_paths`;
- absent layers are omitted;
- no visual connector spans a missing layer;
- compact gap rows replace the old fixed-height placeholder.

- [ ] **Step 2: Run and verify failures**

- [ ] **Step 3: Compose expanded graph view**

Render:

- lineage strip;
- graph totals;
- node-type filters;
- path table;
- mini dependency visualization;
- constraints and terminal companies;
- path evidence counts;
- research gaps.

- [ ] **Step 4: Preserve interaction rules**

Single click opens ContextDock, double click uses an existing drilldown destination, hover previews only.

- [ ] **Step 5: Run focused tests and TypeScript**

Expected: pass.

---

### Task 13: Validate The Six Theme Contracts

**Files:**
- Modify: `test_theme_industrial_aggregate.py`
- Modify: `frontend/src/lib/themeIndustrialIntelligence.test.ts`

- [ ] **Step 1: Add six-theme backend assertions**

For HBM, CoWoS, Glass Substrate, CPO, AI Infrastructure, and Data Center Cooling assert:

- canonical identity;
- active graph lineage;
- graph nodes, edges, and evidence;
- constraint projection;
- deterministic response equality across repeated calls.

For five evidenced themes assert applicable downstream sections appear. For AI Infrastructure assert graph/constraints plus verified downstream gaps.

- [ ] **Step 2: Add frontend fixture assertions**

Normalize each backend-shaped fixture and assert no section disappears.

- [ ] **Step 3: Run all focused backend and frontend tests**

Expected: pass.

---

### Task 14: Full Verification And Browser Acceptance

**Files:**
- Create screenshots under `reports/phase1015-*.png` only if browser capture is available.

- [ ] **Step 1: Run full backend tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend TypeScript**

```powershell
cd frontend
npx tsc --noEmit
```

Expected: exit code 0.

- [ ] **Step 3: Run production build**

```powershell
cd frontend
npm run build
```

Expected: successful production build.

- [ ] **Step 4: Browser-validate every theme**

For each required theme:

1. search exact theme name or alias;
2. verify canonical selected identity;
3. verify compact Theme Summary;
4. verify graph counts and snapshot;
5. verify constraints;
6. verify controllers when present;
7. verify opportunities when present;
8. verify packet lineage when present;
9. open Industrial Dependency Graph;
10. verify path and evidence rendering;
11. verify compact gaps where evidence is absent.

- [ ] **Step 5: Verify integration safety**

Check:

- exactly one aggregate request per theme selection;
- no aggregate request on hover;
- no duplicate React key errors;
- no hydration errors;
- no mojibake;
- no `NaN`, `undefined`, or fabricated zero;
- no fixed-height blank evidence panel;
- no unrelated-theme path.

- [ ] **Step 6: Capture before and after screenshots**

Capture:

- existing sparse Theme Workspace before implementation, if an earlier report image is available;
- integrated HBM command workspace;
- integrated CPO command workspace;
- AI Infrastructure truthful research gaps;
- expanded Industrial Dependency Graph.

---

## Test Plan Summary

Backend:

- canonical identity;
- active lineage;
- bounded graph projection;
- cross-theme isolation;
- evidence admission;
- constraints and optional severity;
- controller and opportunity path filtering;
- packet lineage and filtering;
- coverage semantics;
- research gaps;
- additive aggregate compatibility;
- deterministic output.

Frontend:

- strict normalization;
- canonical identity preservation;
- graph/constraint/controller/opportunity/packet rendering;
- compact gaps;
- nullable values;
- no frontend inference;
- no duplicate fetch ownership;
- content-driven layout.

System:

- full pytest;
- TypeScript;
- production build;
- six-theme browser matrix;
- screenshots and console/network inspection.

## Browser Validation Checklist

| Check | HBM | CoWoS | Glass | CPO | AI Infra | Cooling |
|---|---|---|---|---|---|---|
| Canonical identity | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Graph rendered | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Constraint rows | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Controller rows/gap | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Opportunity rows/gap | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Packet lineage/gap | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Coverage audit | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Dependency paths | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| No unrelated path | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| One aggregate request | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Clean console/render | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

## Final Acceptance

Phase 10.15 is complete only when:

- the existing active Phase 12 stack is visibly accessible from Theme Workspace;
- available evidence never collapses into a generic unavailable block;
- genuine absence is shown as a compact verified research gap;
- Industrial Dependency Graph paths are real active evidenced paths;
- all six themes satisfy the browser matrix;
- automated verification passes.
