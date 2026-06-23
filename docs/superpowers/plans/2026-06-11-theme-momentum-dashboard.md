# Theme Momentum Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Theme Discovery `Market Rotation Trend` gauge panel with the approved aggregate-driven Dense Research Stack.

**Architecture:** Keep the existing Theme Discovery grid and sidebar dimensions. Add one presentation-only `ThemeMomentumDashboard` component inside `ThemeResearchPage.tsx`, feed it the already-fetched `ThemeAggregateResponse`, and style it through narrowly scoped CSS classes in `globals.css`.

**Tech Stack:** React, TypeScript, Next.js 14, existing Phase 10 aggregate contract, CSS.

---

### Task 1: Add the UI contract regression

**Files:**
- Modify: `frontend/src/lib/themeIntelligence.test.ts`
- Test: `frontend/src/lib/themeIntelligence.test.ts`

- [ ] **Step 1: Add failing source-contract assertions**

Extend `themeResearchSourceContract` to require:

```ts
hasThemeMomentumDashboard: source.includes("function ThemeMomentumDashboard"),
hasMomentumSections: [
  "Theme Momentum",
  "Why Now",
  "Primary Bottleneck",
  "Conviction Summary",
  "Theme Overlap",
].every((label) => source.includes(label)),
hasHonestEvidenceStates:
  source.includes("No catalyst evidence available.")
  && source.includes("No bottleneck evidence available."),
hasKnowledgeGraphPlaceholder:
  source.includes("Theme Overlap Intelligence will be available after Phase 10.12 Knowledge Graph Engine."),
removesGaugePanel:
  !source.includes("marketTrendItems")
  && !source.includes("ai-market-trend"),
```

- [ ] **Step 2: Run TypeScript to verify RED**

Run:

```powershell
npx tsc --noEmit
```

Expected: contract compilation succeeds, while direct contract evaluation shows the new booleans are false against the current source.

### Task 2: Implement the Dense Research Stack

**Files:**
- Modify: `frontend/src/components/ThemeResearchPage.tsx`

- [ ] **Step 1: Add aggregate-only helper functions**

Add helpers that:

- format nullable numeric metrics as `Unavailable`
- format nullable percentages with `%`
- extract persisted controller labels from `aggregate.bottlenecks.controllers`
- extract up to four persisted catalyst names

- [ ] **Step 2: Add `ThemeMomentumDashboard`**

The component accepts:

```ts
function ThemeMomentumDashboard({ aggregate }: { aggregate: ThemeAggregateResponse | null })
```

It renders:

- lifecycle stage, confidence, next stage, time window
- catalyst list or exact empty state
- primary bottleneck metrics and persisted controllers or exact empty state
- score-engine conviction metrics
- exact Phase 10.12 placeholder

- [ ] **Step 3: Replace only the old panel**

Delete:

```ts
const marketTrendItems = ...
```

Replace the `.ai-market-trend` section with:

```tsx
<ThemeMomentumDashboard aggregate={selectedAggregate} />
```

Keep `.ai-overview` and all surrounding layout unchanged.

### Task 3: Replace gauge styling with dense terminal styling

**Files:**
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Remove `.ai-market-trend` gauge rules**

Delete the half-gauge and heat-strip-specific selectors.

- [ ] **Step 2: Add scoped Dense Research Stack styles**

Add:

- `.theme-momentum-dashboard`
- `.theme-momentum-section`
- `.theme-momentum-section-head`
- `.theme-momentum-grid`
- `.theme-momentum-metric`
- `.theme-momentum-evidence`
- `.theme-momentum-bottleneck`
- `.theme-momentum-placeholder`

Keep the existing `.ai-side-stack` grid and sidebar width unchanged. Use compact typography,
ellipsis where needed, and no decorative charts or gauges.

### Task 4: Verify automated contracts

**Files:**
- No production changes expected

- [ ] **Step 1: Run TypeScript**

```powershell
npx tsc --noEmit
```

Expected: exit code 0.

- [ ] **Step 2: Run lint**

```powershell
npm run lint
```

Expected: exit code 0; existing unrelated warnings may remain.

- [ ] **Step 3: Run production build**

```powershell
npm run build
```

Expected: exit code 0.

### Task 5: Browser validation

**Files:**
- Evidence: `reports/phase1011-theme-momentum-*.png` when screenshot capture is available

- [ ] **Step 1: Start or reuse local frontend/backend**

Use the existing local API and Next.js development server.

- [ ] **Step 2: Validate HBM**

Confirm:

- Growth lifecycle and persisted confidence
- two persisted catalysts
- Advanced DRAM Capacity bottleneck
- persisted controllers
- score metrics and conviction
- Phase 10.12 placeholder

- [ ] **Step 3: Validate Glass Substrate**

Confirm the same five sections use its own aggregate evidence and render Early rather than a
fallback lifecycle.

- [ ] **Step 4: Validate AI Infrastructure**

Confirm the same five sections use its own aggregate evidence.

- [ ] **Step 5: Check browser quality**

Confirm:

- no console errors
- no hydration errors
- no horizontal overflow in the dashboard or page
- no mojibake
- no duplicate lifecycle gauge panel
- no synthetic values or fabricated catalyst/bottleneck rows

- [ ] **Step 6: Capture screenshots**

Capture one screenshot per validated theme if the in-app browser screenshot API succeeds.
